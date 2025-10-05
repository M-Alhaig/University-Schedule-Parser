import os
from io import BytesIO
import platform
from typing import Tuple, List
import fitz
import pdfplumber
from PIL import Image
from fastapi import HTTPException
from pdf2image import convert_from_bytes
import logging
from app.ParseImg import handle_img
from app.config import config

logger = logging.getLogger(__name__)

def process_pdf(doc: fitz.Document, browser: str = "CHROME") -> Tuple[Image.Image, str]:
    logger.info(f"Processing {doc.page_count}-page PDF with {browser} browser settings")

    if doc.page_count == 2:
        # Get crop points from config
        crop_config = config.PDF_CROP_POINTS[browser]
        page1_crop = crop_config["page1_crop"]
        page2_crop = crop_config["page2_crop"]
        logger.debug(f"Using crop points - page1: {page1_crop}, page2: {page2_crop}")

        page1 = doc.load_page(0)
        page2 = doc.load_page(1)

        rect0 = page1.rect
        rect1 = page2.rect

        text = page1.get_text()

        # If text not embedded in PDF (eg. Windows Chrome PDFs)
        if not text:
            logger.info("Text not embedded in PDF - treating as image-like PDF")
            rect = doc[0].rect
            width, height = rect.width, rect.height

            # Define clip rectangles using config
            clip1 = fitz.Rect(0, 0, width, height - config.CHROME_IMAGE_PDF_CROP["page1_bottom"])
            clip2 = fitz.Rect(0, config.CHROME_IMAGE_PDF_CROP["page2_top"], width, height)
            logger.debug(f"Clipping page 1: bottom={config.CHROME_IMAGE_PDF_CROP['page1_bottom']}, page 2: top={config.CHROME_IMAGE_PDF_CROP['page2_top']}")

            # Render cropped portions
            pix1 = doc[0].get_pixmap(clip=clip1, dpi=config.OCR_DPI)
            pix2 = doc[1].get_pixmap(clip=clip2, dpi=config.OCR_DPI)

            # Convert to PIL Images
            img1 = Image.open(BytesIO(pix1.tobytes("png")))
            img2 = Image.open(BytesIO(pix2.tobytes("png")))

            # Merge vertically
            merged = Image.new("RGB", (img1.width, img1.height + img2.height))
            merged.paste(img1, (0, 0))
            merged.paste(img2, (0, img1.height))

            logger.info(f"Merged pages into single image: {merged.width}x{merged.height}")
            return handle_img(merged, browser)


        logger.info("Text embedded in PDF - processing as standard PDF")
        new_rect0 = fitz.Rect(rect0.x0, rect0.y0, rect0.x1, rect0.y1 - page1_crop)
        new_rect1 = fitz.Rect(rect1.x0, rect1.y0 + page2_crop, rect1.x1, rect1.y1)

        page1.set_cropbox(new_rect0)
        page2.set_cropbox(new_rect1)

        # Get their sizes
        r1 = page1.rect
        r2 = page2.rect

        # Create new PDF with one page big enough to hold both vertically
        combined_height = r1.height + r2.height
        combined_width = max(r1.width, r2.width)
        logger.debug(f"Creating combined PDF: {combined_width}x{combined_height}")

        new_doc = fitz.open()
        new_page = new_doc.new_page(width=combined_width, height=combined_height)

        # Place first page at the top
        new_page.show_pdf_page(fitz.Rect(0, 0, r1.width, r1.height), doc, 0)

        # Place second page below the first
        new_page.show_pdf_page(fitz.Rect(0, r1.height, r2.width, r1.height + r2.height), doc, 1)
        doc = new_doc
        logger.info("Successfully merged PDF pages")

    pdf_bytes = doc.write()
    pdf_buffer = BytesIO(pdf_bytes)
    pdf_buffer = draw_pdf_line(pdf_buffer)

    # Convert to image for consistent return type
    images = pdf_to_images(pdf_buffer)
    return images[0], "PDF"

def draw_pdf_line(doc: BytesIO) -> BytesIO:
    logger.info("Drawing separator line in PDF")
    bbox = None
    target_keywords = ["THURSDAY", "JEUDI"]

    with pdfplumber.open(doc) as pdf:
        page = pdf.pages[0]

        for word in page.extract_words():
            if word["text"].upper() in target_keywords:
                bbox = word
                logger.debug(f"Found keyword '{word['text']}' at position x={word['x1']}, y={word['top']}")
                break

    if not bbox:
        logger.error(f"Required keyword not found in PDF. Expected one of: {target_keywords}")
        raise HTTPException(
            status_code=400,
            detail="PDF format not supported. Unable to detect schedule layout."
        )

    x_right = float(bbox["x1"]) + config.KEYWORD_PADDING
    top = float(bbox["top"]) - config.PDF_LINE_TOP_OFFSET
    bottom = float(bbox["bottom"])
    line_end = bottom + config.PDF_LINE_EXTENSION
    logger.debug(f"Drawing line from ({x_right}, {top}) to ({x_right}, {line_end})")

    doc = fitz.open(stream=doc, filetype="pdf")
    page = doc.load_page(0)
    page.draw_line(p1=(x_right, top), p2=(x_right, line_end), color=(0, 0, 0), width=1)
    pdf_bytes = doc.write()
    pdf_buffer = BytesIO(pdf_bytes)
    logger.info("Successfully drew separator line")
    return pdf_buffer

def pdf_to_images(pdf_data: BytesIO) -> List[Image.Image]:
    """
    Convert PDF bytes to images.

    Args:
        pdf_data: PDF file as BytesIO

    Returns:
        List of PIL Images
    """
    logger.info("Converting PDF to images")
    if platform.system() == "Windows":
        # Use your local Windows folders and executables
        poppler_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "poppler", "Library", "bin")
        logger.debug(f"Using Windows poppler_path: {poppler_path}")
    else:
        # Inside Linux container (or Linux machine)
        # Assume tesseract and poppler-utils installed system-wide
        poppler_path = "/usr/bin"  # typical path for poppler utils binaries
        logger.debug(f"Using Linux poppler_path: {poppler_path}")

    images = convert_from_bytes(pdf_data.getvalue(), dpi=config.OCR_DPI, poppler_path=poppler_path)
    logger.info(f"Converted PDF to {len(images)} image(s)")
    return images

def handle_pdf(pdf_stream: BytesIO, browser: str) -> Tuple[Image.Image, str]:
    logger.info(f"Handling PDF with {browser} browser settings")
    try:
        doc = fitz.open(stream=pdf_stream, filetype="pdf")
        image, file_type = process_pdf(doc, browser=browser)
        return image, file_type
    except HTTPException:
        # Re-raise HTTP exceptions with their original detail
        raise
    except ValueError as e:
        logger.error(f"Value error processing PDF: {e}", exc_info=True)
        raise HTTPException(status_code=400, detail="Unable to process PDF. Please ensure it's a valid schedule document.")
    except OSError as e:
        logger.error(f"File error processing PDF: {e}", exc_info=True)
        raise HTTPException(status_code=400, detail="Unable to process PDF. The file may be corrupted.")
    except Exception as e:
        logger.error(f"Unexpected error processing PDF - Type: {type(e).__name__}, Message: {e}", exc_info=True)
        raise HTTPException(
            status_code=400,
            detail="Unable to process PDF. Please ensure it's a valid schedule document."
        )