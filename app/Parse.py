import logging
import os
import platform
import re
from concurrent.futures import ThreadPoolExecutor
from io import BytesIO
from typing import Any, Dict, List, Optional, Tuple

import cv2
import numpy as np
import pytesseract
from fastapi import UploadFile
from numpy.typing import NDArray
from PIL import Image
from pydantic import BaseModel

from app.config import config
from app.IcsService import create_schedule_ics
from app.metrics import track_time
from app.ParseImg import handle_img
from app.ParsePDF import handle_pdf

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


def calculate_iou(box: Tuple[int, int, int, int], filtered_box: Tuple[int, int, int, int]) -> float:
    """
    Calculate Intersection over Union (IoU) between two bounding boxes.

    Args:
        box: First bounding box as (x, y, width, height)
        filtered_box: Second bounding box as (x, y, width, height)

    Returns:
        IoU score between 0.0 and 1.0
    """
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


def filter_duplicate_boxes(
    boxes: List[Tuple[int, int, int, int]], iou_threshold: float = 0.8
) -> List[Tuple[int, int, int, int]]:
    """
    Filter out duplicate bounding boxes using IoU threshold.

    Args:
        boxes: List of bounding boxes as (x, y, width, height)
        iou_threshold: IoU threshold for considering boxes as duplicates

    Returns:
        Filtered list of unique bounding boxes
    """
    boxes = sorted(boxes, key=lambda box: box[2] * box[3])

    filtered_boxes: List[Tuple[int, int, int, int]] = []

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


@track_time("box_extraction_times")
def extract_boxes_from_image(image: Image.Image, file_type: str = "PDF") -> List[Tuple[int, int, int, int]]:
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
    area_threshold = (
        config.BOX_EXTRACTION["area_threshold_pdf"] if file_type == "PDF" else config.BOX_EXTRACTION["area_threshold_image"]
    )

    for cnt in contours:
        x, y, w, h = cv2.boundingRect(cnt)
        area = w * h
        aspect_ratio = w / float(h)

        if w < config.BOX_EXTRACTION["min_width"] or h < config.BOX_EXTRACTION["min_height"]:
            continue
        if area < area_threshold or area > config.BOX_EXTRACTION["max_area"]:
            continue
        if (
            aspect_ratio < config.BOX_EXTRACTION["min_aspect_ratio"]
            or aspect_ratio > config.BOX_EXTRACTION["max_aspect_ratio"]
        ):
            continue

        boxes.append((x, y, w, h))

    logger.info(f"Extracted {len(boxes)} boxes before filtering")
    boxes = filter_duplicate_boxes(boxes, iou_threshold=config.BOX_EXTRACTION["iou_threshold"])
    logger.info(f"Filtered to {len(boxes)} unique boxes")

    # Save debug image if enabled
    if config.DEBUG_SAVE_BOXES:
        for box in boxes:
            x, y, w, h = box
            cv2.rectangle(image_copy, (x, y), (x + w, y + h), (0, 255, 0), 2)

        debug_image = Image.fromarray(image_copy)
        debug_path = "debug_boxes.png"
        debug_image.save(debug_path)
        logger.info(f"Saved debug image with detected boxes to {debug_path}")

    boxes = sorted(boxes, key=lambda b: (b[1], b[0]))
    return boxes


def get_bbox_days_times(
    boxes: List[Tuple[int, int, int, int]], image: Image.Image
) -> Tuple[List[Tuple[Tuple[int, int, int, int], str]], Optional[int], Optional[int]]:
    DAYS = config.DAYS_ENGLISH + config.DAYS_FRENCH
    logger.info("Detecting day and time boxes")
    day_boxes = []
    time_x = None
    time_w = None

    for box in boxes:

        if len(day_boxes) == config.MAX_DAYS_TO_DETECT and time_x is not None:
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


def extract_single_box(
    args: Tuple[Tuple[int, int, int, int], Image.Image, Optional[int], Optional[int], Optional[str]],
) -> Optional[Dict[str, Any]]:
    box, image, time_x, time_w, day = args
    x, y, w, h = box
    w = w + config.BOX_WIDTH_ADJUSTMENT

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

    # Parse time into components, handling various OCR formats
    # Examples: "08:00 - 09:00", "08:00-09:00", "08:00 09:00", "08:00- -09:50"
    time_parts = time.split()
    # Remove dashes that might be standalone tokens
    time_parts = [t for t in time_parts if t != "-"]
    # Strip leading/trailing dashes from each part (OCR artifacts)
    time_parts = [t.strip("-") for t in time_parts]
    # Remove empty strings after stripping
    time_parts = [t for t in time_parts if t]
    # If we have a single token, try splitting by dash
    if len(time_parts) == 1 and "-" in time_parts[0]:
        time_parts = time_parts[0].split("-")
        time_parts = [t.strip() for t in time_parts if t.strip()]

    subject = {"details": " ".join(subject_details.split()), "day": day if day else "", "time": time_parts}
    return subject


def get_subjects_data(boxes: List[Tuple[int, int, int, int]], image: Image.Image) -> List[Dict[str, Any]]:
    logger.info("Extracting subjects data")
    day_boxes, time_x, time_w = get_bbox_days_times(boxes, image)

    if time_x is None:
        logger.warning("No time reference box found - schedule parsing may fail")

    # Prepare tasks for threading
    tasks = []

    # Sort day_boxes by x position for column range detection
    day_boxes_sorted = sorted(day_boxes, key=lambda d: d[0][0])

    for box in boxes:
        x, y, w, h = box

        # Skip day boxes
        if any(day_box[0] == box for day_box in day_boxes):
            continue

        # Find the day for this box by checking which day column it falls in
        day = None
        for i, day_box in enumerate(day_boxes_sorted):
            day_x = day_box[0][0]
            day_w = day_box[0][2]

            # Determine column boundaries
            col_start = day_x - config.DAY_BOX_TOLERANCE
            if i + 1 < len(day_boxes_sorted):
                # Use midpoint between this day and next day as boundary
                next_day_x = day_boxes_sorted[i + 1][0][0]
                col_end = (day_x + next_day_x) // 2
            else:
                # Last column extends to a reasonable width
                col_end = day_x + day_w + 200

            # Check if box falls within this column
            box_center_x = x + w // 2
            if col_start <= box_center_x <= col_end:
                day = day_box[1]
                break

        if day is None and config.DEBUG_SAVE_BOXES:
            logger.warning(f"No day assigned to box at x={x}, y={y}")

        tasks.append((box, image, time_x, time_w, day))

    logger.info(f"Processing {len(tasks)} subject boxes with {config.MAX_WORKERS} workers")
    # Process all tasks in parallel
    with ThreadPoolExecutor(max_workers=config.MAX_WORKERS) as executor:
        results = list(executor.map(extract_single_box, tasks))

    # Filter out None results
    subjects = [subject for subject in results if subject is not None]
    logger.info(f"Successfully extracted {len(subjects)} subjects")
    return subjects


def create_courses(subjects: List[Dict[str, Any]]) -> List[Course]:
    """
    Create Course objects from extracted subject data.

    Args:
        subjects: List of dictionaries containing subject information

    Returns:
        List of Course objects
    """
    logger.info(f"Creating course objects from {len(subjects)} subjects")
    regex = r"(.+?)(?:\s+ID:\s*(.+?))?(?:\s+Activity:\s*(.+?))?(?:\s+Section:\s*(.+?))?(?:\s+Campus:\s*(.+?))?(?:\s+Room:\s*(.+?))?$"
    subject_objects = []
    for i, subject in enumerate(subjects):
        # Validate subject has required time data
        time_parts = subject.get("time", [])
        if not time_parts or len(time_parts) < 1:
            logger.warning(f"Skipping subject {i+1} - missing or invalid time data: {subject.get('details', 'N/A')}")
            continue

        # Construct duration string
        # If we have 2+ parts, use first and last (start and end times)
        # If we have only 1 part and it contains a dash, use it as-is
        if len(time_parts) >= 2:
            duration = f"{time_parts[0]}-{time_parts[-1]}"
        elif len(time_parts) == 1 and "-" in time_parts[0]:
            duration = time_parts[0]
        else:
            logger.warning(f"Skipping subject {i+1} - invalid time format: {time_parts}")
            continue

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
                duration=duration,
            )
            subject_objects.append(subject_object)
        else:
            logger.warning(f"Failed to parse subject {i+1}: {subject['details']}")

    logger.info(f"Successfully created {len(subject_objects)} course objects")
    return subject_objects


# Wrapper functions with timing decorators


@track_time("pdf_processing_times")
def process_file_to_image(file_buffer: BytesIO, browser: str, content_type: str) -> Tuple[Image.Image, str]:
    """
    Process uploaded file (PDF or image) and return PIL Image.

    Args:
        file_buffer: File content as BytesIO
        browser: Browser type (for backward compatibility)
        content_type: MIME type of the file

    Returns:
        Tuple of (PIL Image, file type string)
    """
    if content_type == "application/pdf":
        logger.info("Processing PDF file")
        return handle_pdf(file_buffer, browser)
    else:
        logger.info("Processing image file")
        return handle_img(file_buffer, browser)


@track_time("ocr_processing_times")
def extract_and_create_courses(boxes: List[Tuple[int, int, int, int]], image: Image.Image) -> List[Course]:
    """
    Extract subjects from boxes using OCR and create Course objects.

    Args:
        boxes: List of detected bounding boxes
        image: PIL Image to extract text from

    Returns:
        List of Course objects
    """
    subjects = get_subjects_data(boxes, image)

    # Validate subjects were extracted
    if not subjects:
        logger.error(f"No subjects extracted from {len(boxes)} boxes")
        raise ValueError("No course information could be extracted. The schedule format may not be supported.")

    courses = create_courses(subjects)

    # Validate courses were created
    if not courses:
        logger.error(f"No courses created from {len(subjects)} subjects")
        raise ValueError("Failed to parse course information. The schedule format may be invalid.")

    return courses


@track_time("calendar_generation_times")
def generate_calendar(courses: List[Course]) -> bytes:
    """
    Generate ICS calendar from Course objects.

    Args:
        courses: List of Course objects

    Returns:
        ICS calendar as bytes
    """
    logger.info("Generating ICS calendar")
    logger.info(courses)
    return create_schedule_ics(courses)


async def parse(file: UploadFile, browser: str) -> bytes:
    """
    Main parse workflow that processes uploaded schedule files and generates ICS calendar.

    Stages (with automatic timing via decorators):
    1. PDF/Image Processing - Convert file to PIL Image
    2. Box Extraction - Detect table cells using morphological operations
    3. OCR Processing - Extract text and create Course objects
    4. Calendar Generation - Generate ICS file from courses

    Args:
        file: Uploaded file (PDF or image)
        browser: Browser type (for backward compatibility)

    Returns:
        ICS calendar as bytes
    """
    logger.info(f"Starting parse workflow for {browser} browser")

    file_bytes = await file.read()
    file_buffer = BytesIO(file_bytes)
    logger.info(f"Read {len(file_bytes)} bytes from uploaded file")

    image = None
    try:
        # Stage 1: PDF/Image Processing (timed by decorator)
        image, file_type = process_file_to_image(file_buffer, browser, file.content_type)

        # Stage 2: Box Extraction (timed by decorator)
        boxes = extract_boxes_from_image(image, file_type=file_type)

        # Validate boxes were extracted
        if not boxes:
            logger.error("No boxes detected in the schedule image")
            raise ValueError("No schedule table detected. Please ensure the PDF contains a valid weekly schedule table.")

        # Save debug image if enabled
        if config.DEBUG_SAVE_BOXES:
            image.save("test.png")
            logger.debug("Saved test image to test.png")

        # Stage 3: OCR Processing (timed by decorator)
        courses = extract_and_create_courses(boxes, image)

        # Stage 4: Calendar Generation (timed by decorator)
        calendar = generate_calendar(courses)

        logger.info(f"Parse workflow completed successfully: {len(courses)} courses")
        return calendar
    finally:
        # Clean up resources
        if image is not None:
            try:
                image.close()
                logger.debug("Closed PIL Image resource")
            except Exception as e:
                logger.warning(f"Error closing image: {e}")

        if file_buffer is not None:
            try:
                file_buffer.close()
                logger.debug("Closed BytesIO buffer")
            except Exception as e:
                logger.warning(f"Error closing buffer: {e}")
