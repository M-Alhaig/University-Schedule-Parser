from fastapi import HTTPException
import fitz
import os
from pdf2image import convert_from_bytes
from io import BytesIO
import cv2
import numpy as np
import pdfplumber
import re
import pytesseract
from pydantic import BaseModel
from PIL import Image
import json
from IcsService import create_schedule_ics

class Course(BaseModel):
    name: str
    id: str = ""
    activity: str = ""
    section: str = ""
    campus: str = ""
    room: str = ""
    day: str = ""
    duration: str


tesseract_path = os.path.join(os.path.dirname(__file__), "Tesseract-OCR", "tesseract.exe")
pytesseract.pytesseract.tesseract_cmd = tesseract_path

def process_pdf(doc):
    if doc.page_count == 2:
        points_to_crop = 14.5

        page1 = doc.load_page(0)
        page2 = doc.load_page(1)


        rect0 = page1.rect
        rect1 = page2.rect

        new_rect0 = fitz.Rect(rect0.x0, rect0.y0, rect0.x1, rect0.y1 - points_to_crop)
        new_rect1 = fitz.Rect(rect1.x0, rect1.y0 + points_to_crop, rect1.x1, rect1.y1)

        page1.set_cropbox(new_rect0)
        page2.set_cropbox(new_rect1)


        # Get their sizes
        r1 = page2.rect
        r2 = page2.rect

        # Create new PDF with one page big enough to hold both vertically
        combined_height = r1.height + r2.height
        combined_width = max(r1.width, r2.width)

        new_doc = fitz.open()
        new_page = new_doc.new_page(width=combined_width, height=combined_height)

        # Place first page at the top
        new_page.show_pdf_page(fitz.Rect(0, 0, r1.width, r1.height), doc, 0)

        # Place second page below the first
        new_page.show_pdf_page(fitz.Rect(0, r1.height, r2.width, r1.height + r2.height), doc, 1)
        doc = new_doc


    pdf_bytes = doc.write()
    pdf_buffer = BytesIO(pdf_bytes)
    pdf_buffer = draw_pdf_line(pdf_buffer)

    return pdf_buffer

def draw_pdf_line(doc):
    bbox = None
    with pdfplumber.open(doc) as pdf:
        page = pdf.pages[0]
        target = ["THURSDAY", "JEUDI"]

        for word in page.extract_words():
            if word["text"].upper() in target:
                bbox = word
                break


    if not bbox:
        raise HTTPException(status_code=400, detail="PDF format not supported.")

    x_right = float(bbox["x1"]) + 20  # 10 points right
    top = float(bbox["top"]) - 10 # 10 points up
    bottom = float(bbox["bottom"])

    doc = fitz.open(stream=doc, filetype="pdf")
    page = doc.load_page(0)
    page.draw_line(p1=(x_right, top), p2=(x_right, bottom + 1300), color=(0, 0, 0), width=1)
    pdf_bytes = doc.write()
    pdf_buffer = BytesIO(pdf_bytes)
    return pdf_buffer



def pdf_to_images(pdf_data):
    poppler_path = os.path.join(os.path.dirname(__file__), "poppler", "Library", "bin")
    images = convert_from_bytes(pdf_data, dpi=300, poppler_path=poppler_path)  # Higher DPI = better quality
    return images


def extract_boxes_from_image(image):
    img = np.array(image)
    if len(img.shape) == 3:
        img = cv2.cvtColor(img, cv2.COLOR_RGB2GRAY)

    _, img_bin = cv2.threshold(img, 128, 255, cv2.THRESH_BINARY)
    img_bin = 255 - img_bin
    cv2.imwrite("Image_bin.jpg", img_bin)

    kernel_length = img.shape[1] // 80
    vertical_kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (1, kernel_length))
    hori_kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (kernel_length, 1))
    kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (3, 3))

    img_temp1 = cv2.erode(img_bin, vertical_kernel, iterations=1)
    vertical_lines_img = cv2.dilate(img_temp1, vertical_kernel, iterations=1)
    cv2.imwrite("vertical_lines.jpg", vertical_lines_img)

    img_temp2 = cv2.erode(img_bin, hori_kernel, iterations=1)
    horizontal_lines_img = cv2.dilate(img_temp2, hori_kernel, iterations=1)
    cv2.imwrite("horizontal_lines.jpg", horizontal_lines_img)

    img_final_bin = cv2.addWeighted(vertical_lines_img, 0.5, horizontal_lines_img, 0.5, 0.0)
    img_final_bin = cv2.erode(~img_final_bin, kernel, iterations=2)
    _, img_final_bin = cv2.threshold(img_final_bin, 128, 255, cv2.THRESH_BINARY)
    cv2.imwrite("img_final_bin.jpg", img_final_bin)

    contours, hierarchy = cv2.findContours(img_final_bin, cv2.RETR_TREE, cv2.CHAIN_APPROX_SIMPLE)

    boxes = []
    image_copy = np.array(image.copy())
    for cnt in contours:
        x, y, w, h = cv2.boundingRect(cnt)
        area = w * h
        aspect_ratio = w / float(h)

        if w < 50 or h < 20:
            continue
        if area < 20000 or area > 400000:
            continue
        if aspect_ratio < 0.2 or aspect_ratio > 10:
            continue

        boxes.append((x, y, w, h))
        cv2.rectangle(image_copy, (x, y), (x + w, y + h), (0, 255, 0), 2)

    cv2.imwrite("detected_boxes.png", image_copy)
    boxes = sorted(boxes, key=lambda b: (b[1], b[0]))
    return boxes


def get_bbox_days_times(boxes, image):
    DAYS = ["SUNDAY", "MONDAY", "TUESDAY", "WEDNESDAY", "THURSDAY"]
    day_boxes = []
    time_x = None
    time_w = None

    for box in boxes:

        if len(day_boxes) == 5 and time_x is not None:
            break

        x, y, w, h = box
        crop = image.crop((x, y, x + w, y + h))
        crop = cv2.cvtColor(np.array(crop), cv2.COLOR_RGB2GRAY)
        text = pytesseract.image_to_string(crop).strip()

        if text.upper() in DAYS:
            day_boxes.append((box, text))
        elif re.match(r"\d{2}:\d{2}", text) and time_x is None:
            time_x = x
            time_w = w

    return day_boxes, time_x, time_w


def get_subjects_data(boxes, image):
    day_boxes, time_x, time_w = get_bbox_days_times(boxes, image)
    subjects = []

    for box in boxes:
        x, y, w, h = box

        if any(day_box[0] == box for day_box in day_boxes):
            continue

        day = None
        for day_box in day_boxes:
            if abs(day_box[0][0] - x) < 2:
                day = day_box[1]
                break

        crop = image.crop((x, y, x + w, y + h))
        crop = cv2.cvtColor(np.array(crop), cv2.COLOR_RGB2GRAY)
        subject_details = pytesseract.image_to_string(crop).strip()

        # Skip time boxes and empty boxes
        if re.match(r"\d{2}:\d{2}", subject_details) or not subject_details:
            continue

        # Extract time for this row
        time_box = (time_x, y, time_x + time_w, y + h)
        time_crop = image.crop(time_box)
        time = pytesseract.image_to_string(time_crop).strip()
        subjects.append({
            "details": " ".join(subject_details.split()),
            "day": day if day else "",
            "time": time.split()
        })
    return subjects

def create_courses(subjects):
    regex = r"(.+?)(?:\s+ID:\s*(.+?))?(?:\s+Activity:\s*(.+?))?(?:\s+Section:\s*(.+?))?(?:\s+Campus:\s*(.+?))?(?:\s+Room:\s*(.+?))?$"
    subject_objects = []
    for subject in subjects:
        match = re.search(regex, subject["details"])
        if match:
            subject_object = Course(
                name=match.group(1),
                id=match.group(2) if match.group(2) else "",
                activity=match.group(3) if match.group(3) else "",
                section=match.group(4) if match.group(4) else "",
                campus=match.group(5) if match.group(5) else "",
                room=match.group(6) if match.group(6) else "",
                day=subject["day"],
                duration=subject["time"][0] + subject["time"][-1]
            )
            subject_objects.append(subject_object)

    return subject_objects

def handle_pdf(pdf_stream):
    doc = fitz.open(stream=pdf_stream, filetype="pdf")
    pdf_stream = process_pdf(doc)
    return pdf_to_images(pdf_stream.getvalue())[0]

async def parse(file):
    pdf_bytes = await file.read()
    pdf_stream = BytesIO(pdf_bytes)

    if file.filename.endswith(".pdf"):
        image = handle_pdf(pdf_stream)
    else:
        image = Image.open(pdf_stream)

    boxes = extract_boxes_from_image(image)
    subjects = get_subjects_data(boxes, image)
    courses = create_courses(subjects)

    create_schedule_ics(courses)

    image.save("output.png")
    return courses