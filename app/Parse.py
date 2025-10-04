import logging
import os
from concurrent.futures import ThreadPoolExecutor
from io import BytesIO
import cv2
import numpy as np
import re
import pytesseract
from pydantic import BaseModel
import platform

from app.IcsService import create_schedule_ics
from app.ParseImg import handle_img
from app.ParsePDF import handle_pdf
from app.config import config

logger = logging.getLogger(__name__)

class Course(BaseModel):
    name: str
    id: str = ""
    activity: str = ""
    section: str = ""
    campus: str = ""
    room: str = ""
    day: str = ""
    duration: str



if platform.system() == "Windows":
    # Use your local Windows folders and executables
    tesseract_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "Tesseract-OCR", "tesseract.exe")
else:
    # Inside Linux container (or Linux machine)
    # Assume tesseract and poppler-utils installed system-wide
    tesseract_path = "tesseract"  # system command in PATH

pytesseract.pytesseract.tesseract_cmd = tesseract_path


def calculate_iou(box, filtered_box):
    x1, y1, w1, h1 = box
    x2, y2, w2, h2 = filtered_box

    # Coords of intersection rectangle
    x_left = max(x1, x2)
    y_top = max(y1, y2)
    x_right = min(x1 + w1, x2 + w2)
    y_bottom = min(y1 + h1, y2 + h2)

    # Check for no intersection
    if x_left > x_right or y_top > y_bottom:
        return 0.0

    area_intersection = (x_right - x_left) * (y_bottom - y_top)

    box1_area = w1 * h1
    box2_area = w2 * h2

    iou = area_intersection / (box1_area + box2_area - area_intersection)
    return iou


def filter_duplicate_boxes(boxes, iou_threshold=0.8):

    boxes = sorted(boxes, key=lambda box: box[2] * box[3])

    filtered_boxes = []

    for box in boxes:
        duplicate = False

        for filtered_box in filtered_boxes:
            iou = calculate_iou(box, filtered_box)
            if iou > iou_threshold:
                duplicate = True
                break

        if not duplicate:
            filtered_boxes.append(box)

    return filtered_boxes


def extract_boxes_from_image(image, file_type="PDF"):
    logger.info(f"Extracting boxes from {file_type} image")
    img = np.array(image)
    if len(img.shape) == 3:
        img = cv2.cvtColor(img, cv2.COLOR_RGB2GRAY)
        logger.debug("Converted image from RGB to grayscale")

    _, img_bin = cv2.threshold(img, 128, 255, cv2.THRESH_BINARY)
    img_bin = 255 - img_bin

    kernel_length = img.shape[1] // config.BOX_EXTRACTION["kernel_divisor"]
    logger.debug(f"Using kernel length: {kernel_length}")
    vertical_kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (1, kernel_length))
    hori_kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (kernel_length, 1))
    kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (3, 3))

    img_temp1 = cv2.erode(img_bin, vertical_kernel, iterations=1)
    vertical_lines_img = cv2.dilate(img_temp1, vertical_kernel, iterations=1)

    img_temp2 = cv2.erode(img_bin, hori_kernel, iterations=1)
    horizontal_lines_img = cv2.dilate(img_temp2, hori_kernel, iterations=1)

    img_final_bin = cv2.addWeighted(vertical_lines_img, 0.5, horizontal_lines_img, 0.5, 0.0)
    img_final_bin = cv2.erode(~img_final_bin, kernel, iterations=2)
    _, img_final_bin = cv2.threshold(img_final_bin, 128, 255, cv2.THRESH_BINARY)

    contours, _ = cv2.findContours(img_final_bin, cv2.RETR_TREE, cv2.CHAIN_APPROX_SIMPLE)
    logger.debug(f"Found {len(contours)} contours")

    boxes = []
    image_copy = np.array(image.copy())
    area_threshold = config.BOX_EXTRACTION["area_threshold_pdf"] if file_type == "PDF" else config.BOX_EXTRACTION["area_threshold_image"]

    for cnt in contours:
        x, y, w, h = cv2.boundingRect(cnt)
        area = w * h
        aspect_ratio = w / float(h)

        if w < config.BOX_EXTRACTION["min_width"] or h < config.BOX_EXTRACTION["min_height"]:
            continue
        if area < area_threshold or area > config.BOX_EXTRACTION["max_area"]:
            continue
        if aspect_ratio < config.BOX_EXTRACTION["min_aspect_ratio"] or aspect_ratio > config.BOX_EXTRACTION["max_aspect_ratio"]:
            continue

        boxes.append((x, y, w, h))

    logger.info(f"Extracted {len(boxes)} boxes before filtering")
    boxes = filter_duplicate_boxes(boxes, iou_threshold=config.BOX_EXTRACTION["iou_threshold"])
    logger.info(f"Filtered to {len(boxes)} unique boxes")

    for box in boxes:
        x, y, w, h = box
        cv2.rectangle(image_copy, (x, y), (x + w, y + h), (0, 0, 255), 2)

    boxes = sorted(boxes, key=lambda b: (b[1], b[0]))
    return boxes


def get_bbox_days_times(boxes, image):
    DAYS = config.DAYS_ENGLISH + config.DAYS_FRENCH
    logger.info("Detecting day and time boxes")
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
            logger.debug(f"Found day box: {text}")
        elif re.match(r"\d{2}:\d{2}", text) and time_x is None:
            time_x = x
            time_w = w
            logger.debug(f"Found time box at x={time_x}")

    logger.info(f"Detected {len(day_boxes)} day boxes and time reference: {time_x is not None}")
    return day_boxes, time_x, time_w


def extract_single_box(args):
    box, image, time_x, time_w, day = args
    x, y, w, h = box
    w = w + 2

    # Crop image and prepare it
    crop = image.crop((x, y, x + w, y + h))
    subject_details = pytesseract.image_to_string(crop).strip()

    # Skip duration boxes
    if re.match(r"\d{2}:\d{2}", subject_details) or not subject_details:
        return None

    # Extract time for this subject
    time_box = (time_x, y, time_x + time_w, y + h)
    time_crop = image.crop(time_box)
    time = pytesseract.image_to_string(time_crop).strip()
    subject = {
        "details": " ".join(subject_details.split()),
        "day": day if day else "",
        "time": time.split()
    }
    return subject


def get_subjects_data(boxes, image):
    logger.info("Extracting subjects data")
    day_boxes, time_x, time_w = get_bbox_days_times(boxes, image)

    if time_x is None:
        logger.warning("No time reference box found - schedule parsing may fail")

    # Prepare tasks for threading
    tasks = []
    for box in boxes:
        x, y, w, h = box

        # Skip day boxes
        if any(day_box[0] == box for day_box in day_boxes):
            continue

        # Find the day for this box
        day = None
        for day_box in day_boxes:
            if abs(day_box[0][0] - x) < 10:
                day = day_box[1]
                break

        tasks.append((box, image, time_x, time_w, day))

    logger.info(f"Processing {len(tasks)} subject boxes with {config.MAX_WORKERS} workers")
    # Process all tasks in parallel
    with ThreadPoolExecutor(max_workers=config.MAX_WORKERS) as executor:
        results = list(executor.map(extract_single_box, tasks))

    # Filter out None results
    subjects = [subject for subject in results if subject is not None]
    logger.info(f"Successfully extracted {len(subjects)} subjects")
    return subjects

def create_courses(subjects):
    logger.info(f"Creating course objects from {len(subjects)} subjects")
    regex = r"(.+?)(?:\s+ID:\s*(.+?))?(?:\s+Activity:\s*(.+?))?(?:\s+Section:\s*(.+?))?(?:\s+Campus:\s*(.+?))?(?:\s+Room:\s*(.+?))?$"
    subject_objects = []
    for i, subject in enumerate(subjects):
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
            logger.debug(f"Created course: {subject_object.name} on {subject_object.day}")
        else:
            logger.warning(f"Failed to parse subject {i+1}: {subject['details']}")

    logger.info(f"Successfully created {len(subject_objects)} course objects")
    return subject_objects


async def parse(file, browser):
    logger.info(f"Starting parse workflow for {browser} browser")

    file_bytes = await file.read()
    file_buffer = BytesIO(file_bytes)
    logger.info(f"Read {len(file_bytes)} bytes from uploaded file")

    if file.content_type == "application/pdf":
        logger.info("Processing PDF file")
        image, file_type = handle_pdf(file_buffer, browser)
    else:
        logger.info("Processing image file")
        image, file_type = handle_img(file_buffer, browser)

    boxes = extract_boxes_from_image(image, file_type=file_type)
    subjects = get_subjects_data(boxes, image)
    courses = create_courses(subjects)

    logger.info("Generating ICS calendar")
    calendar = create_schedule_ics(courses)

    logger.info("Parse workflow completed successfully")
    return calendar