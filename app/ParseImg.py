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
        logger.debug("Opened image from file-like object")
    except Exception as e:
        logger.warning(f"Could not open as file-like object (Error: {type(e).__name__}: {e}), attempting to use as PIL Image")
        if isinstance(img, Image.Image):
            image = img
            logger.debug("Using image object directly")
        else:
            logger.error(f"Invalid image input - Type: {type(img).__name__}")
            raise ValueError("Invalid image input. Expected BytesIO or PIL Image.")

    width, height = image.size
    logger.info(f"Image dimensions: {width}x{height}")

    # Crop to top quarter for keyword detection
    cropped = image.crop((0, 0, width, height // 4))
    logger.debug("Cropped top quarter for keyword detection")

    data = pytesseract.image_to_data(cropped, output_type=Output.DICT)

    keyword = config.DETECTION_KEYWORD
    padding = config.KEYWORD_PADDING
    img_np = np.array(image)

    line_drawn = False
    for i, word in enumerate(data['text']):
        if word.strip().lower() == keyword.lower():
            x = data['left'][i]
            y = data['top'][i]
            w = data['width'][i]
            h = data['height'][i]

            # Calculate x position just after the keyword
            line_x = x + w + padding
            logger.info(f"Found keyword '{keyword}' at position ({x}, {y}), drawing line at x={line_x}")

            # Draw line on the full image
            line_start = (line_x, 0)
            line_end = (line_x, height)
            cv2.line(img_np, line_start, line_end, color=(0, 0, 0), thickness=1)
            line_drawn = True
            break

    if not line_drawn:
        logger.warning(f"Keyword '{keyword}' not found in image - no separator line drawn")

    return Image.fromarray(img_np), "IMAGE"