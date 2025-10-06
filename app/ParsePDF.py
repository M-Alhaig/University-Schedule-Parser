import logging
import os
import platform
from io import BytesIO
from typing import List, Optional, Tuple

import cv2
import fitz
import numpy as np
import pdfplumber
from fastapi import HTTPException
from pdf2image import convert_from_bytes
from PIL import Image

from app.config import config
from app.ParseImg import handle_img

logger = logging.getLogger(__name__)

# PDF magic number signature
PDF_MAGIC_NUMBERS = [b"%PDF-1.", b"%PDF-2."]


def validate_pdf_file(pdf_stream: BytesIO) -> None:
    """
    Validate PDF file structure and constraints.

    Args:
        pdf_stream: PDF file as BytesIO

    Raises:
        HTTPException: If validation fails
    """
    # Check for PDF magic number
    pdf_stream.seek(0)
    header = pdf_stream.read(8)
    pdf_stream.seek(0)  # Reset position

    is_valid_pdf = any(header.startswith(magic) for magic in PDF_MAGIC_NUMBERS)
    if not is_valid_pdf:
        logger.warning(f"Invalid PDF header: {header[:20]}")
        raise HTTPException(status_code=400, detail="Invalid PDF file. The file does not appear to be a valid PDF document.")

    # Validate page count
    try:
        doc = fitz.open(stream=pdf_stream, filetype="pdf")
        page_count = doc.page_count
        doc.close()
        pdf_stream.seek(0)  # Reset position

        if page_count > config.MAX_PDF_PAGES:
            logger.warning(f"PDF has {page_count} pages, exceeds limit of {config.MAX_PDF_PAGES}")
            raise HTTPException(
                status_code=400,
                detail=f"PDF has too many pages ({page_count}). Maximum allowed is {config.MAX_PDF_PAGES} pages.",
            )

        if page_count == 0:
            logger.warning("PDF has 0 pages")
            raise HTTPException(status_code=400, detail="PDF file appears to be empty or corrupted.")

        logger.info(f"PDF validation passed: {page_count} page(s)")

    except fitz.FileDataError as e:
        logger.error(f"PDF structure error: {e}")
        raise HTTPException(status_code=400, detail="PDF file is corrupted or has an invalid structure.")


def detect_vertical_lines(image: Image.Image) -> List[Tuple[int, int, int, int]]:
    """
    Detect vertical lines in an image using morphological operations.

    Args:
        image: PIL Image to analyze

    Returns:
        List of (x, y_start, y_end, x_end) tuples representing vertical line segments
    """
    # Convert PIL image to OpenCV format
    img_array = np.array(image)
    gray = cv2.cvtColor(img_array, cv2.COLOR_RGB2GRAY)

    # Apply binary threshold
    _, binary = cv2.threshold(gray, 128, 255, cv2.THRESH_BINARY_INV)

    # Create vertical kernel for morphological operation
    kernel_height = config.VERTICAL_KERNEL_HEIGHT
    kernel_width = config.VERTICAL_KERNEL_WIDTH
    vertical_kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (kernel_width, kernel_height))

    # Detect vertical lines
    detected_lines = cv2.morphologyEx(binary, cv2.MORPH_OPEN, vertical_kernel, iterations=1)

    # Find contours
    contours, _ = cv2.findContours(detected_lines, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

    # Extract line segments
    lines = []
    for contour in contours:
        x, y, w, h = cv2.boundingRect(contour)
        # Filter by minimum length
        if h >= config.VERTICAL_LINE_MIN_LENGTH:
            lines.append((x, y, y + h, x + w))  # (x, y_start, y_end, x_end)

    logger.debug(f"Detected {len(lines)} vertical lines")
    return lines


def find_table_bottom(page_image: Image.Image) -> Optional[int]:
    """
    Find the bottom boundary of the table by detecting where vertical lines end.

    Args:
        page_image: PIL Image of the page

    Returns:
        Y-coordinate of table bottom, or None if not found
    """
    lines = detect_vertical_lines(page_image)

    if len(lines) < config.MIN_VERTICAL_LINES_COUNT:
        logger.warning(f"Insufficient vertical lines detected ({len(lines)}), cannot determine table bottom")
        return None

    # Find the maximum y_end (lowest point where vertical lines terminate)
    max_y_end = max(line[2] for line in lines)
    logger.info(f"Table bottom detected at y={max_y_end}")
    return max_y_end


def detect_horizontal_lines_simple(image: Image.Image, y_start: int, y_end: int) -> List[int]:
    """
    Detect horizontal lines using row-based analysis (simpler, more robust).

    Args:
        image: PIL Image to analyze
        y_start: Start Y coordinate of region
        y_end: End Y coordinate of region

    Returns:
        List of Y coordinates where horizontal lines are found
    """
    # Convert PIL image to OpenCV format
    img_array = np.array(image)
    gray = cv2.cvtColor(img_array, cv2.COLOR_RGB2GRAY)

    # Crop to region of interest
    roi = gray[y_start:y_end, :]
    height, width = roi.shape

    # For each row, count the number of dark pixels
    dark_pixel_counts = []
    for y in range(height):
        row = roi[y, :]
        # Count pixels darker than threshold (lines are dark)
        dark_pixels = np.sum(row < 200)
        dark_pixel_counts.append(dark_pixels)

    # Find rows with high dark pixel density (likely horizontal lines)
    # A horizontal line will have many dark pixels across the width
    threshold = width * 0.3  # At least 30% of width must be dark

    line_positions = []
    i = 0
    while i < len(dark_pixel_counts):
        if dark_pixel_counts[i] >= threshold:
            # Found start of a line, find its end
            line_start = i
            while i < len(dark_pixel_counts) and dark_pixel_counts[i] >= threshold * 0.5:
                i += 1
            line_end = i

            # Record the middle of the line
            line_y = y_start + (line_start + line_end) // 2
            line_positions.append(line_y)
        else:
            i += 1

    logger.debug(f"Detected {len(line_positions)} horizontal lines in region {y_start}-{y_end}")
    return line_positions


def find_duplicate_days_row(page_image: Image.Image) -> Optional[int]:
    """
    Find and locate the duplicate days row at the top of page 2.
    Returns the Y coordinate just below the bottom horizontal line of the days row.

    Args:
        page_image: PIL Image of the page

    Returns:
        Y-coordinate just below the duplicate days row, or None if not found
    """
    import pytesseract
    from pytesseract import Output

    # Search in top 30% of page for duplicate days
    search_height = int(page_image.height * 0.3)
    top_region = page_image.crop((0, 0, page_image.width, search_height))

    # Use OCR to find day names
    data = pytesseract.image_to_data(top_region, output_type=Output.DICT)

    DAYS = config.DAYS_ENGLISH + config.DAYS_FRENCH

    # Find any day name and get its bounding box
    day_found = False
    min_y = float("inf")
    max_y = 0

    for i, word in enumerate(data["text"]):
        if word.strip().upper() in DAYS:
            day_found = True
            word_top = data["top"][i]
            word_bottom = data["top"][i] + data["height"][i]
            min_y = min(min_y, word_top)
            max_y = max(max_y, word_bottom)
            logger.debug(f"Found day '{word}' at y={word_top}-{word_bottom}")

    if not day_found:
        logger.info("No duplicate days row found - no day names detected")
        return None

    # Now find horizontal lines around this region
    # Expand search significantly - look well above and below the days
    search_start = max(0, int(min_y) - 50)
    search_end = min(search_height, int(max_y) + 100)

    logger.debug(f"Searching for horizontal lines in region {search_start}-{search_end} (days found at {min_y}-{max_y})")

    horizontal_lines = detect_horizontal_lines_simple(page_image, search_start, search_end)

    logger.info(f"Found {len(horizontal_lines)} horizontal lines around duplicate days row")

    if len(horizontal_lines) < 2:
        logger.warning(f"Found days but only {len(horizontal_lines)} horizontal lines - expected 2")
        # Fallback: return position below the days text with some padding
        crop_position = int(max_y) + 10
        logger.info(f"Using fallback crop position at y={crop_position}")
        return crop_position

    # We expect 2 lines: one above days, one below
    # Find the line that's below the days (closest line after max_y)
    lines_below_days = [line for line in horizontal_lines if line > max_y]

    if lines_below_days:
        # Use the first line below the days
        bottom_line_y = lines_below_days[0]
        crop_position = bottom_line_y + 5  # Crop a bit below the line
        logger.info(f"Duplicate days row found - cropping at y={crop_position} (line at {bottom_line_y} + 5px offset)")
    else:
        # No line below days, use fallback
        crop_position = int(max_y) + 10
        logger.info(f"No line found below days, using fallback at y={crop_position}")

    return crop_position


def find_table_top(page_image: Image.Image) -> Optional[int]:
    """
    Find the top boundary of the table by detecting duplicate days row.
    If duplicate days found, crop below its bottom line.
    Otherwise, use vertical line detection as fallback.

    Args:
        page_image: PIL Image of the page

    Returns:
        Y-coordinate of table top, or None if not found
    """
    # First, try to find duplicate days row
    duplicate_row_bottom = find_duplicate_days_row(page_image)

    if duplicate_row_bottom is not None:
        return duplicate_row_bottom

    # Fallback: use vertical line detection
    logger.info("Falling back to vertical line detection")
    vert_lines = detect_vertical_lines(page_image)

    if len(vert_lines) < config.MIN_VERTICAL_LINES_COUNT:
        logger.warning(f"Insufficient vertical lines detected ({len(vert_lines)}), cannot determine table top")
        return None

    # Use the minimum starting position of vertical lines
    line_starts = sorted([line[1] for line in vert_lines])
    table_top = line_starts[0]
    logger.info(f"Table top detected at y={table_top} (using vertical line start)")
    return table_top


def detect_orientation(page: fitz.Page) -> str:
    """
    Detect page orientation based on aspect ratio.

    Args:
        page: PyMuPDF page object

    Returns:
        "portrait" or "landscape"
    """
    rect = page.rect
    aspect_ratio = rect.width / rect.height
    orientation = "portrait" if aspect_ratio < 1.0 else "landscape"
    logger.info(f"Detected orientation: {orientation} (aspect_ratio={aspect_ratio:.2f})")
    return orientation


def process_pdf(doc: fitz.Document, browser: str = "CHROME") -> Tuple[Image.Image, str]:
    """
    Process PDF by dynamically detecting table boundaries and merging pages.
    Browser parameter kept for backward compatibility but not used in processing.
    """
    logger.info(f"Processing {doc.page_count}-page PDF (browser parameter: {browser})")

    if doc.page_count == 2:
        page1 = doc.load_page(0)
        page2 = doc.load_page(1)

        # Detect orientation
        orientation = detect_orientation(page1)

        # Convert pages to images for boundary detection
        pix1 = page1.get_pixmap(dpi=config.OCR_DPI)
        pix2 = page2.get_pixmap(dpi=config.OCR_DPI)

        img1_full = Image.open(BytesIO(pix1.tobytes("png")))
        img2_full = Image.open(BytesIO(pix2.tobytes("png")))

        # Detect table boundaries
        page1_bottom = find_table_bottom(img1_full)
        page2_top = find_table_top(img2_full)

        # Fallback to full page if detection fails
        if page1_bottom is None:
            logger.warning("Could not detect page 1 bottom, using full page height")
            page1_bottom = img1_full.height

        if page2_top is None:
            logger.warning("Could not detect page 2 top, using 0")
            page2_top = 0
        else:
            # page2_top already points to just below the bottom line of duplicate days row
            # No offset needed - use the detected position directly for seamless merge
            logger.debug(f"Using page 2 top at y={page2_top} (just below duplicate days row)")

        # Crop images based on detected boundaries
        img1_cropped = img1_full.crop((0, 0, img1_full.width, page1_bottom))
        img2_cropped = img2_full.crop((0, page2_top, img2_full.width, img2_full.height))

        # Merge vertically
        merged_width = max(img1_cropped.width, img2_cropped.width)
        merged_height = img1_cropped.height + img2_cropped.height
        merged = Image.new("RGB", (merged_width, merged_height))
        merged.paste(img1_cropped, (0, 0))
        merged.paste(img2_cropped, (0, img1_cropped.height))

        logger.info(f"Merged pages dynamically: {merged.width}x{merged.height} (orientation: {orientation})")

        # Close temporary images
        img1_full.close()
        img2_full.close()

        return handle_img(merged, browser)

    # Single page PDF - convert to image and process
    logger.info("Processing single-page PDF")
    pdf_bytes = doc.write()
    pdf_buffer = BytesIO(pdf_bytes)

    # Convert to image
    images = pdf_to_images(pdf_buffer)

    # Process through image handler (draws line on image)
    return handle_img(images[0], browser)


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

    # Validate PDF before processing
    validate_pdf_file(pdf_stream)

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
        raise HTTPException(status_code=400, detail="Unable to process PDF. Please ensure it's a valid schedule document.")
