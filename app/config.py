"""
Configuration settings for FastAPI Schedule Parser
Supports environment variable overrides
"""
import os
from typing import Dict, Literal


class Config:
    """Application configuration with environment variable support"""

    # File validation
    MAX_FILE_SIZE = int(os.getenv("MAX_FILE_SIZE", 10 * 1024 * 1024))  # 10MB default
    MAX_PDF_PAGES = int(os.getenv("MAX_PDF_PAGES", 10))  # Maximum pages in PDF
    ALLOWED_CONTENT_TYPES = os.getenv("ALLOWED_CONTENT_TYPES", "application/pdf").split(",")

    # PDF Processing - Dynamic Table Boundary Detection
    # Vertical line detection parameters for finding table boundaries
    VERTICAL_LINE_MIN_LENGTH = int(os.getenv("VERTICAL_LINE_MIN_LENGTH", 30))
    VERTICAL_KERNEL_HEIGHT = int(os.getenv("VERTICAL_KERNEL_HEIGHT", 50))
    VERTICAL_KERNEL_WIDTH = int(os.getenv("VERTICAL_KERNEL_WIDTH", 1))

    # Edge detection thresholds
    EDGE_CLUSTER_THRESHOLD = int(os.getenv("EDGE_CLUSTER_THRESHOLD", 20))  # Pixels to group edges
    MIN_VERTICAL_LINES_COUNT = int(os.getenv("MIN_VERTICAL_LINES_COUNT", 3))  # Min lines to confirm table

    # Image Processing - Box extraction thresholds
    BOX_EXTRACTION = {
        "min_width": int(os.getenv("BOX_MIN_WIDTH", 50)),
        "min_height": int(os.getenv("BOX_MIN_HEIGHT", 20)),
        "area_threshold_pdf": int(os.getenv("BOX_AREA_THRESHOLD_PDF", 20000)),
        "area_threshold_image": int(os.getenv("BOX_AREA_THRESHOLD_IMAGE", 2000)),
        "max_area": int(os.getenv("BOX_MAX_AREA", 800000)),
        "min_aspect_ratio": float(os.getenv("BOX_MIN_ASPECT_RATIO", 0.2)),
        "max_aspect_ratio": float(os.getenv("BOX_MAX_ASPECT_RATIO", 10.0)),
        "iou_threshold": float(os.getenv("BOX_IOU_THRESHOLD", 0.1)),
        "kernel_divisor": int(os.getenv("BOX_KERNEL_DIVISOR", 80)),
    }

    # Image Processing - OCR settings
    OCR_DPI = int(os.getenv("OCR_DPI", 300))

    # Image Processing - Day/keyword detection
    DAYS_ENGLISH = ["SUNDAY", "MONDAY", "TUESDAY", "WEDNESDAY", "THURSDAY", "FRIDAY", "SATURDAY"]
    DAYS_FRENCH = ["DIMANCHE", "LUNDI", "MARDI", "MERCREDI", "JEUDI", "VENDREDI", "SAMEDI"]
    DETECTION_KEYWORD = os.getenv("DETECTION_KEYWORD", "THURSDAY")
    KEYWORD_RIGHT_PADDING = int(os.getenv("KEYWORD_RIGHT_PADDING", 100))  # Fallback padding to right of keyword

    # Box matching tolerance (previously hardcoded in Parse.py)
    DAY_BOX_TOLERANCE = int(os.getenv("DAY_BOX_TOLERANCE", 10))  # Pixel tolerance for matching day columns
    MAX_DAYS_TO_DETECT = int(os.getenv("MAX_DAYS_TO_DETECT", 5))  # Max number of day columns to find
    BOX_WIDTH_ADJUSTMENT = int(os.getenv("BOX_WIDTH_ADJUSTMENT", 2))  # Width adjustment for OCR boxes

    # Threading
    MAX_WORKERS = int(os.getenv("MAX_WORKERS", 8))

    # Debug settings
    DEBUG_SAVE_BOXES = os.getenv("DEBUG_SAVE_BOXES", "true").lower() == "true"

    # Logging settings
    ENVIRONMENT = os.getenv("ENVIRONMENT", "dev")  # dev or prod
    LOG_FORMAT = os.getenv("LOG_FORMAT", "text")  # text or json
    # Auto-detect Lambda environment
    if os.getenv("AWS_LAMBDA_FUNCTION_NAME"):
        ENVIRONMENT = "prod"
        LOG_FORMAT = "json"

    # Calendar settings
    SCHEDULE_DURATION_WEEKS = int(os.getenv("SCHEDULE_DURATION_WEEKS", 19))
    DEFAULT_TIMEZONE: Literal["KSA", "ALG"] = os.getenv("DEFAULT_TIMEZONE", "KSA")  # type: ignore
    TIMEZONES = {
        "KSA": "Asia/Riyadh",
        "ALG": "Africa/Algiers",
    }

    # API Settings
    CALENDAR_FILENAME = os.getenv("CALENDAR_FILENAME", "calendar.ics")

    # CORS Settings
    ALLOWED_ORIGINS = os.getenv(
        "ALLOWED_ORIGINS",
        "https://zocq7dcly5.execute-api.me-central-1.amazonaws.com,https://schedule-parser.malhaig.online"
    ).split(",")


# Singleton instance
config = Config()
