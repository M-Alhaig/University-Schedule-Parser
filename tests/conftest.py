"""
Pytest configuration and fixtures
"""

from io import BytesIO
from unittest.mock import MagicMock, Mock

import numpy as np
import pytest
from PIL import Image

from app.Parse import Course


@pytest.fixture
def sample_course():
    """Create a sample course for testing"""
    return Course(
        name="Introduction to Computer Science",
        id="CS101",
        activity="Lecture",
        section="A",
        campus="Main Campus",
        room="Building 1, Room 201",
        day="MONDAY",
        duration="08:00-09:30",
    )


@pytest.fixture
def sample_courses():
    """Create multiple sample courses for testing"""
    return [
        Course(name="Math 101", id="MTH101", day="MONDAY", duration="08:00-09:00"),
        Course(name="Physics 201", id="PHY201", day="TUESDAY", duration="10:00-11:30"),
        Course(name="Chemistry 101", id="CHM101", day="WEDNESDAY", duration="14:00-15:30"),
    ]


@pytest.fixture
def sample_image():
    """Create a simple test image"""
    # Create a white 800x600 image
    img_array = np.ones((600, 800, 3), dtype=np.uint8) * 255
    return Image.fromarray(img_array, "RGB")


@pytest.fixture
def sample_image_bytes():
    """Create test image as BytesIO"""
    img_array = np.ones((600, 800, 3), dtype=np.uint8) * 255
    img = Image.fromarray(img_array, "RGB")
    buffer = BytesIO()
    img.save(buffer, format="PNG")
    buffer.seek(0)
    return buffer


@pytest.fixture
def mock_tesseract(monkeypatch):
    """Mock pytesseract calls to avoid dependency on actual Tesseract"""
    mock_image_to_string = Mock(return_value="MONDAY")
    mock_image_to_data = Mock(
        return_value={
            "text": ["", "MONDAY", "", "TUESDAY", "08:00"],
            "left": [0, 50, 0, 250, 450],
            "top": [0, 10, 0, 10, 10],
            "width": [0, 100, 0, 100, 50],
            "height": [0, 30, 0, 30, 20],
        }
    )

    monkeypatch.setattr("pytesseract.image_to_string", mock_image_to_string)
    monkeypatch.setattr("pytesseract.image_to_data", mock_image_to_data)

    return {"image_to_string": mock_image_to_string, "image_to_data": mock_image_to_data}


@pytest.fixture
def mock_pdf_document(monkeypatch):
    """Mock PyMuPDF (fitz) Document"""
    mock_doc = MagicMock()
    mock_doc.page_count = 2

    mock_page1 = MagicMock()
    mock_page1.rect = MagicMock(x0=0, y0=0, x1=600, y1=800)
    mock_page1.get_text.return_value = "Schedule text"

    mock_page2 = MagicMock()
    mock_page2.rect = MagicMock(x0=0, y0=0, x1=600, y1=800)

    mock_doc.load_page.side_effect = [mock_page1, mock_page2]

    return mock_doc


@pytest.fixture
def sample_boxes():
    """Sample bounding boxes for testing"""
    return [
        (50, 10, 100, 30),  # Day box 1
        (250, 10, 100, 30),  # Day box 2
        (450, 10, 50, 20),  # Time box
        (50, 100, 100, 40),  # Subject box 1
        (250, 100, 100, 40),  # Subject box 2
    ]


@pytest.fixture
def sample_subjects():
    """Sample subject data for testing"""
    return [
        {
            "details": "MATH 101 ID: MTH101 Activity: Lecture Section: A Campus: Main Room: 201",
            "day": "MONDAY",
            "time": ["08:00", "09:30"],
        },
        {
            "details": "PHYS 201 ID: PHY201 Activity: Lab Section: B Campus: North Room: 305",
            "day": "TUESDAY",
            "time": ["10:00", "11:30"],
        },
    ]
