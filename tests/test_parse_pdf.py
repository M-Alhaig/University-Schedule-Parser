"""
Tests for PDF processing and line detection algorithms
"""

from unittest.mock import MagicMock, Mock, patch

import cv2
import numpy as np
import pytest
from PIL import Image

from app.ParsePDF import (
    detect_horizontal_lines_simple,
    detect_orientation,
    detect_vertical_lines,
    find_duplicate_days_row,
    find_table_bottom,
    find_table_top,
)


class TestDetectVerticalLines:
    """Tests for vertical line detection"""

    def test_detect_vertical_lines_with_clear_lines(self):
        """Test detection of clear vertical lines"""
        # Create synthetic image with vertical lines
        img_array = np.ones((500, 800, 3), dtype=np.uint8) * 255  # White background

        # Draw 5 clear vertical lines
        for x in [100, 200, 300, 400, 500]:
            cv2.line(img_array, (x, 50), (x, 450), (0, 0, 0), 2)  # Black lines

        image = Image.fromarray(img_array, "RGB")
        lines = detect_vertical_lines(image)

        # Should detect at least 5 lines
        assert len(lines) >= 5
        # Lines should have format (x, y_start, y_end, x_end)
        assert all(len(line) == 4 for line in lines)
        # Lines should be vertical (y_end > y_start)
        assert all(line[2] > line[1] for line in lines)

    def test_detect_vertical_lines_with_no_lines(self):
        """Test with image containing no vertical lines"""
        # Create blank white image
        img_array = np.ones((500, 800, 3), dtype=np.uint8) * 255
        image = Image.fromarray(img_array, "RGB")

        lines = detect_vertical_lines(image)

        # Should detect no lines or very few
        assert len(lines) < 3

    def test_detect_vertical_lines_filters_short_lines(self):
        """Test that short vertical lines are filtered out"""
        # Create image with short and long lines
        img_array = np.ones((500, 800, 3), dtype=np.uint8) * 255

        # Short line (should be filtered)
        cv2.line(img_array, (100, 100), (100, 120), (0, 0, 0), 2)
        # Long lines (should be detected)
        cv2.line(img_array, (200, 50), (200, 450), (0, 0, 0), 2)
        cv2.line(img_array, (300, 50), (300, 450), (0, 0, 0), 2)

        image = Image.fromarray(img_array, "RGB")
        lines = detect_vertical_lines(image)

        # Should detect long lines but not short ones
        assert len(lines) >= 2
        # All detected lines should meet minimum length requirement
        for line in lines:
            line_length = line[2] - line[1]  # y_end - y_start
            assert line_length >= 30  # config.VERTICAL_LINE_MIN_LENGTH


class TestDetectHorizontalLines:
    """Tests for horizontal line detection"""

    def test_detect_horizontal_lines_with_clear_lines(self):
        """Test detection of horizontal lines in a region"""
        # Create image with horizontal lines
        img_array = np.ones((500, 800, 3), dtype=np.uint8) * 255

        # Draw 3 horizontal lines in test region
        for y in [100, 150, 200]:
            cv2.line(img_array, (50, y), (750, y), (0, 0, 0), 2)

        image = Image.fromarray(img_array, "RGB")

        # Search in region containing the lines
        lines = detect_horizontal_lines_simple(image, y_start=80, y_end=220)

        # Should detect approximately 3 lines
        assert len(lines) >= 2
        assert len(lines) <= 4  # Allow some tolerance

    def test_detect_horizontal_lines_empty_region(self):
        """Test with region containing no lines"""
        img_array = np.ones((500, 800, 3), dtype=np.uint8) * 255
        image = Image.fromarray(img_array, "RGB")

        lines = detect_horizontal_lines_simple(image, y_start=100, y_end=200)

        # Should detect no lines
        assert len(lines) == 0

    def test_detect_horizontal_lines_returns_y_coordinates(self):
        """Test that returned values are Y coordinates"""
        img_array = np.ones((500, 800, 3), dtype=np.uint8) * 255
        cv2.line(img_array, (50, 150), (750, 150), (0, 0, 0), 3)

        image = Image.fromarray(img_array, "RGB")
        lines = detect_horizontal_lines_simple(image, y_start=100, y_end=200)

        assert len(lines) > 0
        # Y coordinates should be within search region
        for y in lines:
            assert 100 <= y <= 200


class TestFindTableBottom:
    """Tests for table bottom detection"""

    def test_find_table_bottom_with_sufficient_lines(self):
        """Test finding table bottom when enough vertical lines exist"""
        # Create image with table-like structure
        img_array = np.ones((600, 800, 3), dtype=np.uint8) * 255

        # Draw table with vertical lines ending at y=500
        for x in [100, 200, 300, 400, 500]:
            cv2.line(img_array, (x, 50), (x, 500), (0, 0, 0), 2)

        image = Image.fromarray(img_array, "RGB")
        table_bottom = find_table_bottom(image)

        # Should detect table bottom near y=500
        assert table_bottom is not None
        assert 480 <= table_bottom <= 520  # Allow some tolerance

    def test_find_table_bottom_insufficient_lines(self):
        """Test when not enough vertical lines are present"""
        # Create image with only 1-2 lines (below threshold)
        img_array = np.ones((600, 800, 3), dtype=np.uint8) * 255
        cv2.line(img_array, (200, 50), (200, 500), (0, 0, 0), 2)

        image = Image.fromarray(img_array, "RGB")
        table_bottom = find_table_bottom(image)

        # Should return None due to insufficient lines
        assert table_bottom is None


class TestFindDuplicateDaysRow:
    """Tests for duplicate days row detection"""

    @patch("pytesseract.image_to_data")
    @patch("app.ParsePDF.detect_horizontal_lines_simple")
    def test_find_duplicate_days_with_clear_detection(self, mock_detect_lines, mock_image_to_data):
        """Test finding duplicate days row with clear day names"""
        # Mock OCR to return day names
        mock_image_to_data.return_value = {
            "text": ["", "MONDAY", "TUESDAY", "WEDNESDAY", ""],
            "left": [0, 100, 200, 300, 400],
            "top": [0, 100, 100, 100, 150],
            "width": [50, 80, 80, 100, 50],
            "height": [20, 20, 20, 20, 20],
        }

        # Mock horizontal line detection to return lines above and below days
        mock_detect_lines.return_value = [95, 125]  # Top and bottom lines

        # Create image
        img_array = np.ones((800, 1000, 3), dtype=np.uint8) * 255
        image = Image.fromarray(img_array, "RGB")

        crop_position = find_duplicate_days_row(image)

        # Should find a crop position just below the bottom line
        assert crop_position is not None
        assert 120 <= crop_position <= 135  # Should be near bottom line (125) + offset (5)

    @patch("pytesseract.image_to_data")
    def test_find_duplicate_days_no_days_found(self, mock_image_to_data):
        """Test when no day names are detected"""
        # Mock OCR to return no day names
        mock_image_to_data.return_value = {
            "text": ["Some", "Random", "Text"],
            "left": [0, 100, 200],
            "top": [0, 100, 100],
            "width": [50, 80, 80],
            "height": [20, 20, 20],
        }

        img_array = np.ones((800, 1000, 3), dtype=np.uint8) * 255
        image = Image.fromarray(img_array, "RGB")

        crop_position = find_duplicate_days_row(image)

        # Should return None when no days found
        assert crop_position is None

    @patch("pytesseract.image_to_data")
    @patch("app.ParsePDF.detect_horizontal_lines_simple")
    def test_find_duplicate_days_fallback_mode(self, mock_detect_lines, mock_image_to_data):
        """Test fallback when days found but not enough lines"""
        # Mock OCR to return day names
        mock_image_to_data.return_value = {
            "text": ["THURSDAY", "FRIDAY"],
            "left": [100, 200],
            "top": [100, 100],
            "width": [80, 80],
            "height": [20, 20],
        }

        # Mock only 1 horizontal line detected (insufficient)
        mock_detect_lines.return_value = [95]

        img_array = np.ones((800, 1000, 3), dtype=np.uint8) * 255
        image = Image.fromarray(img_array, "RGB")

        crop_position = find_duplicate_days_row(image)

        # Should use fallback position (days bottom + padding)
        assert crop_position is not None
        assert crop_position >= 120  # Should be below day text (100+20+10)


class TestFindTableTop:
    """Tests for table top detection"""

    @patch("app.ParsePDF.find_duplicate_days_row")
    def test_find_table_top_with_duplicate_days(self, mock_find_days):
        """Test finding table top when duplicate days are detected"""
        mock_find_days.return_value = 150  # Mock crop position

        img_array = np.ones((800, 1000, 3), dtype=np.uint8) * 255
        image = Image.fromarray(img_array, "RGB")

        table_top = find_table_top(image)

        # Should return the duplicate days crop position
        assert table_top == 150
        mock_find_days.assert_called_once()

    @patch("app.ParsePDF.find_duplicate_days_row")
    def test_find_table_top_fallback_to_vertical_lines(self, mock_find_days):
        """Test fallback to vertical line detection when no duplicate days"""
        mock_find_days.return_value = None  # No duplicate days found

        # Create image with vertical lines starting at y=100
        img_array = np.ones((800, 1000, 3), dtype=np.uint8) * 255
        for x in [100, 200, 300, 400]:
            cv2.line(img_array, (x, 100), (x, 700), (0, 0, 0), 2)

        image = Image.fromarray(img_array, "RGB")
        table_top = find_table_top(image)

        # Should detect table top from vertical lines
        assert table_top is not None
        assert 80 <= table_top <= 120  # Near where lines start


class TestDetectOrientation:
    """Tests for page orientation detection"""

    def test_detect_orientation_portrait(self):
        """Test detection of portrait orientation"""
        mock_page = Mock()
        mock_page.rect = Mock(width=612, height=792)  # Standard portrait (8.5" x 11")

        orientation = detect_orientation(mock_page)

        assert orientation == "portrait"

    def test_detect_orientation_landscape(self):
        """Test detection of landscape orientation"""
        mock_page = Mock()
        mock_page.rect = Mock(width=792, height=612)  # Standard landscape (11" x 8.5")

        orientation = detect_orientation(mock_page)

        assert orientation == "landscape"

    def test_detect_orientation_square(self):
        """Test detection with square page (edge case)"""
        mock_page = Mock()
        mock_page.rect = Mock(width=500, height=500)  # Square

        orientation = detect_orientation(mock_page)

        # Square should be detected as landscape (aspect_ratio = 1.0 >= 1.0)
        assert orientation == "landscape"
