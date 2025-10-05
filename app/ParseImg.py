import numpy as np
from PIL import Image
import pytesseract
from pytesseract import Output
import cv2
import logging
from typing import Tuple, Union
from io import BytesIO
from app.config import config

logger = logging.getLogger(__name__)


def handle_img(img: Union[BytesIO, Image.Image], browser: str = "CHROME") -> Tuple[Image.Image, str]:
    logger.info(f"Handling image with {browser} browser settings")
    try:
        image = Image.open(img)
    except Exception as e:
        logger.warning(f"Could not open as file-like object (Error: {type(e).__name__}: {e}), attempting to use as PIL Image")
        if isinstance(img, Image.Image):
            image = img
        else:
            logger.error(f"Invalid image input - Type: {type(img).__name__}")
            raise ValueError("Invalid image input. Expected BytesIO or PIL Image.")

    width, height = image.size
    logger.info(f"Image dimensions: {width}x{height}")

    # Crop to top quarter for keyword detection
    cropped = image.crop((0, 0, width, height // 4))
    data = pytesseract.image_to_data(cropped, output_type=Output.DICT)

    keyword = config.DETECTION_KEYWORD
    img_np = np.array(image)

    # Find THURSDAY keyword position
    thursday_y = None
    thursday_x = None
    for i, word in enumerate(data['text']):
        if word.strip().lower() == keyword.lower():
            thursday_x = data['left'][i] + data['width'][i]
            thursday_y = data['top'][i] + data['height'][i]
            logger.info(f"Found keyword '{keyword}' at position ({data['left'][i]}, {data['top'][i]})")
            break

    if thursday_y is None:
        logger.warning(f"Keyword '{keyword}' not found - using fallback line position")
        return Image.fromarray(img_np), "IMAGE"

    # Detect horizontal lines below THURSDAY using morphological operations
    gray = cv2.cvtColor(img_np, cv2.COLOR_RGB2GRAY)
    _, binary = cv2.threshold(gray, 128, 255, cv2.THRESH_BINARY_INV)

    # Create horizontal kernel
    horizontal_kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (50, 1))
    detect_horizontal = cv2.morphologyEx(binary, cv2.MORPH_OPEN, horizontal_kernel, iterations=1)

    # Find contours of horizontal lines
    contours, _ = cv2.findContours(detect_horizontal, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

    # Find horizontal line just below THURSDAY (header separator)
    header_line_x_right = None
    search_range_start = thursday_y + 5
    search_range_end = thursday_y + 100

    for contour in contours:
        x, y, w, h = cv2.boundingRect(contour)
        # Check if this is a horizontal line in the search range
        if search_range_start <= y <= search_range_end and w > 100:  # Significant width
            line_x_right = x + w
            if header_line_x_right is None or line_x_right > header_line_x_right:
                header_line_x_right = line_x_right

    # Draw vertical line at the rightmost edge
    if header_line_x_right:
        line_x = header_line_x_right
        logger.info(f"Found table right edge at x={line_x} (detected from horizontal line)")
    else:
        # Fallback: use keyword position + padding
        line_x = thursday_x + config.KEYWORD_RIGHT_PADDING
        logger.warning(f"No horizontal line detected, using fallback at x={line_x}")

    # Draw the vertical line
    cv2.line(img_np, (line_x, 0), (line_x, height), color=(0, 0, 0), thickness=1)
    logger.info(f"Drew vertical line at x={line_x}")

    return Image.fromarray(img_np), "IMAGE"