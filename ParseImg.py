import numpy as np
from PIL import Image
import pytesseract
from pytesseract import Output
import cv2


def handle_img(img):
    try:
        image = Image.open(img)
    except Exception:
        image = img
    width, height = image.size
    cropped = image.crop((0, 0, width, height // 4))

    data = pytesseract.image_to_data(cropped, output_type=Output.DICT)

    keyword = "THURSDAY"
    padding = 63
    img_np = np.array(image)
    for i, word in enumerate(data['text']):
        if word.strip().lower() == keyword.lower():
            x = data['left'][i]
            y = data['top'][i]
            w = data['width'][i]
            h = data['height'][i]

            # Calculate x position just after the keyword
            line_x = x + w + padding

            # Draw line on the full image
            line_start = (line_x, 0)
            line_end = (line_x, height)
            cv2.line(img_np, line_start, line_end, color=(0, 0, 0), thickness=1)
            cv2.imwrite("line.png", img_np)
            break

    return Image.fromarray(img_np), "IMAGE"