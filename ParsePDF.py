import os
from io import BytesIO

import fitz
import pdfplumber
from fastapi import HTTPException
from pdf2image import convert_from_bytes


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

def handle_pdf(pdf_stream):
    doc = fitz.open(stream=pdf_stream, filetype="pdf")
    pdf_stream = process_pdf(doc)
    return pdf_to_images(pdf_stream.getvalue())[0]