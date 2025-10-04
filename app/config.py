"""
Configuration settings for FastAPI Schedule Parser
"""
from typing import Dict, Literal


class Config:
    """Application configuration"""

    # File validation
    MAX_FILE_SIZE = 10 * 1024 * 1024  # 10MB
    VALID_BROWSERS = ["CHROME", "FIREFOX"]
    ALLOWED_CONTENT_TYPES = ["application/pdf"]

    # PDF Processing - Crop points for multi-page PDFs
    PDF_CROP_POINTS: Dict[str, Dict[str, float]] = {
        "CHROME": {
            "page1_crop": 14.5,
            "page2_crop": 40.0,
        },
        "FIREFOX": {
            "page1_crop": 14.5,
            "page2_crop": 14.5,
        }
    }

    # PDF Processing - Chrome Windows PDF (image-like PDFs)
    CHROME_IMAGE_PDF_CROP = {
        "page1_bottom": 24.0,
        "page2_top": 42.0,
    }

    # Image Processing - Box extraction thresholds
    BOX_EXTRACTION = {
        "min_width": 50,
        "min_height": 20,
        "area_threshold_pdf": 20000,
        "area_threshold_image": 2000,
        "max_area": 800000,
        "min_aspect_ratio": 0.2,
        "max_aspect_ratio": 10.0,
        "iou_threshold": 0.1,
        "kernel_divisor": 80,  # image.shape[1] // kernel_divisor
    }

    # Image Processing - OCR settings
    OCR_DPI = 300

    # Image Processing - Day/keyword detection
    DAYS_ENGLISH = ["SUNDAY", "MONDAY", "TUESDAY", "WEDNESDAY", "THURSDAY", "FRIDAY", "SATURDAY"]
    DAYS_FRENCH = ["DIMANCHE", "LUNDI", "MARDI", "MERCREDI", "JEUDI", "VENDREDI", "SAMEDI"]
    DETECTION_KEYWORD = "THURSDAY"  # Keyword to find for drawing separator line
    KEYWORD_PADDING = 100  # Padding after keyword for line placement (in pixels)

    # Threading
    MAX_WORKERS = 8

    # Calendar settings
    SCHEDULE_DURATION_WEEKS = 19
    DEFAULT_TIMEZONE: Literal["KSA", "ALG"] = "KSA"
    TIMEZONES = {
        "KSA": "Asia/Riyadh",
        "ALG": "Africa/Algiers",
    }

    # API Settings
    CALENDAR_FILENAME = "calendar.ics"


# Singleton instance
config = Config()
