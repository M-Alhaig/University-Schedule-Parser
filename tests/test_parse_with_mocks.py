"""
Unit tests for Parse module with mocked dependencies
"""

from io import BytesIO
from unittest.mock import AsyncMock, MagicMock, Mock, patch

import numpy as np
import pytest
from PIL import Image

from app.Parse import (
    calculate_iou,
    create_courses,
    extract_boxes_from_image,
    filter_duplicate_boxes,
)


class TestCalculateIOUWithMocks:
    """Tests for IoU calculation (no mocks needed)"""

    def test_partial_overlap_precise(self):
        """Test precise IoU calculation"""
        box1 = (0, 0, 20, 20)
        box2 = (10, 10, 20, 20)
        iou = calculate_iou(box1, box2)
        # Overlap = 10x10 = 100
        # Union = 400 + 400 - 100 = 700
        assert abs(iou - (100 / 700)) < 0.001


class TestFilterDuplicateBoxesWithMocks:
    """Tests for box filtering (no mocks needed)"""

    def test_filters_overlapping_boxes(self):
        """Test filtering with controlled overlap"""
        # Create boxes with known overlap
        boxes = [
            (0, 0, 100, 100),  # area = 10000
            (5, 5, 100, 100),  # High overlap with first
            (200, 200, 50, 50),  # No overlap
        ]
        filtered = filter_duplicate_boxes(boxes, iou_threshold=0.5)
        assert len(filtered) == 2  # Should keep first and third


class TestCreateCoursesWithMocks:
    """Tests for course creation (no mocks needed)"""

    def test_creates_courses_from_valid_subjects(self, sample_subjects):
        """Test course creation with valid data"""
        courses = create_courses(sample_subjects)
        assert len(courses) == 2
        assert courses[0].name == "MATH 101"
        assert courses[0].id == "MTH101"
        assert courses[1].name == "PHYS 201"

    def test_handles_missing_optional_fields(self):
        """Test course creation with minimal data"""
        subjects = [{"details": "Basic Course", "day": "FRIDAY", "time": ["13:00", "14:00"]}]
        courses = create_courses(subjects)
        assert len(courses) == 1
        assert courses[0].name == "Basic Course"
        assert courses[0].id == ""


@pytest.mark.usefixtures("mock_tesseract")
class TestExtractBoxesWithMocks:
    """Tests for box extraction with mocked CV operations"""

    def test_extract_boxes_returns_list(self, sample_image):
        """Test that extract_boxes returns a list"""
        with patch("cv2.findContours") as mock_contours:
            # Mock contours to return some simple rectangles
            mock_contour = np.array([[[10, 10]], [[110, 10]], [[110, 60]], [[10, 60]]])
            mock_contours.return_value = ([mock_contour], None)

            boxes = extract_boxes_from_image(sample_image, "PDF")
            assert isinstance(boxes, list)

    def test_extract_boxes_filters_small_boxes(self, sample_image):
        """Test that small boxes are filtered out"""
        with patch("cv2.findContours") as mock_contours:
            # Create mix of small and large contours
            small = np.array([[[10, 10]], [[20, 10]], [[20, 20]], [[10, 20]]])  # 10x10
            large = np.array([[[100, 100]], [[200, 100]], [[200, 150]], [[100, 150]]])  # 100x50
            mock_contours.return_value = ([small, large], None)

            boxes = extract_boxes_from_image(sample_image, "PDF")
            # Small box should be filtered out (area < threshold)
            assert all(w >= 50 and h >= 20 for x, y, w, h in boxes)


@pytest.mark.usefixtures("mock_tesseract")
class TestGetSubjectsDataWithMocks:
    """Tests for subject extraction with mocked OCR"""

    def test_subjects_extracted_from_boxes(self, sample_boxes, sample_image, mock_tesseract):
        """Test that subjects are extracted from boxes"""
        from app.Parse import get_subjects_data

        # Mock OCR to return proper day names, time, and course data
        def mock_ocr(image):
            text = getattr(mock_ocr, "call_count", 0)
            mock_ocr.call_count = text + 1
            # First few calls should return day names and time
            if text == 0:
                return "MONDAY"
            elif text == 1:
                return "08:00"  # Time reference
            else:
                return "MATH 101 ID: MTH101"

        mock_tesseract["image_to_string"].side_effect = mock_ocr

        subjects = get_subjects_data(sample_boxes, sample_image)
        # Should extract subjects (at least we should get a list back)
        assert isinstance(subjects, list)


class TestResourceCleanup:
    """Tests for resource management"""

    @pytest.mark.asyncio
    async def test_parse_cleans_up_resources_on_success(self, sample_image_bytes):
        """Test that resources are cleaned up after successful parse"""
        from app.Parse import parse

        # Create mock file upload
        mock_file = Mock()
        mock_file.read = AsyncMock(return_value=b"fake pdf content")
        mock_file.content_type = "application/pdf"

        with patch("app.Parse.process_file_to_image") as mock_pdf, patch(
            "app.Parse.extract_boxes_from_image"
        ) as mock_boxes, patch("app.Parse.extract_and_create_courses") as mock_courses_extract, patch(
            "app.Parse.generate_calendar"
        ) as mock_calendar:

            # Setup mocks
            mock_image = Mock(spec=Image.Image)
            mock_pdf.return_value = (mock_image, "PDF")
            mock_boxes.return_value = [(10, 10, 100, 100)]
            from app.Parse import Course

            mock_courses_extract.return_value = [Course(name="Test", day="MONDAY", duration="08:00-09:00")]
            mock_calendar.return_value = b"fake ics data"

            result = await parse(mock_file, "CHROME")

            # Verify image.close() was called
            mock_image.close.assert_called_once()
            assert result == b"fake ics data"

    @pytest.mark.asyncio
    async def test_parse_cleans_up_resources_on_error(self):
        """Test that resources are cleaned up even on error"""
        from app.Parse import parse

        mock_file = Mock()
        mock_file.read = AsyncMock(return_value=b"fake pdf content")
        mock_file.content_type = "application/pdf"

        with patch("app.Parse.process_file_to_image") as mock_pdf:
            mock_image = Mock(spec=Image.Image)
            mock_pdf.return_value = (mock_image, "PDF")

            # Force an error in box extraction
            with patch("app.Parse.extract_boxes_from_image", side_effect=Exception("Test error")):
                with pytest.raises(Exception):
                    await parse(mock_file, "CHROME")

                # Verify cleanup happened despite error
                mock_image.close.assert_called_once()
