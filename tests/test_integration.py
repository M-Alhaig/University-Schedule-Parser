"""
Integration tests for the schedule parser
These tests require sample PDF files
"""
import pytest
import os
from pathlib import Path
from io import BytesIO
from PIL import Image
import numpy as np


# Check if test schedules exist
SCHEDULES_DIR = Path(__file__).parent.parent / "examples" / "schedules"
HAS_TEST_FILES = SCHEDULES_DIR.exists()

pytestmark = pytest.mark.skipif(
    not HAS_TEST_FILES,
    reason="Test schedule files not found. Add sample PDFs to examples/schedules/"
)


@pytest.mark.integration
class TestIntegrationWithRealPDFs:
    """Integration tests with actual PDF files"""

    def get_test_files(self):
        """Get list of test PDF files"""
        if not SCHEDULES_DIR.exists():
            return []
        return list(SCHEDULES_DIR.glob("*.pdf"))

    def test_chrome_portrait_schedule(self):
        """Test parsing Chrome portrait schedule"""
        test_file = SCHEDULES_DIR / "chrome_portrait.pdf"
        if not test_file.exists():
            pytest.skip("chrome_portrait.pdf not found")

        from app.ParsePDF import handle_pdf

        with open(test_file, 'rb') as f:
            pdf_bytes = BytesIO(f.read())
            image, file_type = handle_pdf(pdf_bytes, "CHROME")

            assert isinstance(image, Image.Image)
            assert file_type == "PDF"
            assert image.size[0] > 0 and image.size[1] > 0

    def test_chrome_landscape_schedule(self):
        """Test parsing Chrome landscape schedule"""
        test_file = SCHEDULES_DIR / "chrome_landscape.pdf"
        if not test_file.exists():
            pytest.skip("chrome_landscape.pdf not found")

        from app.ParsePDF import handle_pdf

        with open(test_file, 'rb') as f:
            pdf_bytes = BytesIO(f.read())
            image, file_type = handle_pdf(pdf_bytes, "CHROME")

            assert isinstance(image, Image.Image)
            assert file_type == "PDF"

    def test_firefox_portrait_schedule(self):
        """Test parsing Firefox portrait schedule"""
        test_file = SCHEDULES_DIR / "firefox_portrait.pdf"
        if not test_file.exists():
            pytest.skip("firefox_portrait.pdf not found")

        from app.ParsePDF import handle_pdf

        with open(test_file, 'rb') as f:
            pdf_bytes = BytesIO(f.read())
            image, file_type = handle_pdf(pdf_bytes, "FIREFOX")

            assert isinstance(image, Image.Image)
            assert file_type == "PDF"

    def test_firefox_landscape_schedule(self):
        """Test parsing Firefox landscape schedule"""
        test_file = SCHEDULES_DIR / "firefox_landscape.pdf"
        if not test_file.exists():
            pytest.skip("firefox_landscape.pdf not found")

        from app.ParsePDF import handle_pdf

        with open(test_file, 'rb') as f:
            pdf_bytes = BytesIO(f.read())
            image, file_type = handle_pdf(pdf_bytes, "FIREFOX")

            assert isinstance(image, Image.Image)
            assert file_type == "PDF"

    @pytest.mark.asyncio
    async def test_end_to_end_parsing(self):
        """Test complete parsing workflow"""
        test_files = self.get_test_files()
        if not test_files:
            pytest.skip("No test PDF files found")

        from app.Parse import parse
        from unittest.mock import Mock

        # Test with first available PDF
        test_file = test_files[0]
        browser = "CHROME" if "chrome" in test_file.name.lower() else "FIREFOX"

        with open(test_file, 'rb') as f:
            mock_file = Mock()
            mock_file.read = Mock(return_value=f.read())
            mock_file.content_type = "application/pdf"

            try:
                result = await parse(mock_file, browser)
                assert result is not None
                assert isinstance(result, bytes)
                assert b'BEGIN:VCALENDAR' in result
                assert b'END:VCALENDAR' in result
            except ValueError as e:
                # Expected if PDF format is not supported
                assert "No schedule table detected" in str(e) or "No course information" in str(e)


@pytest.mark.integration
class TestIntegrationWithMockData:
    """Integration tests with synthetic data (no real PDFs needed)"""

    @pytest.mark.asyncio
    async def test_parse_workflow_with_mock_pdf(self):
        """Test parsing workflow with minimal mocking"""
        from app.Parse import parse
        from unittest.mock import Mock, patch
        from PIL import Image

        # Create a simple test image
        img_array = np.ones((600, 800, 3), dtype=np.uint8) * 255
        test_image = Image.fromarray(img_array, 'RGB')

        mock_file = Mock()
        mock_file.read = Mock(return_value=b"fake pdf content")
        mock_file.content_type = "application/pdf"

        with patch('app.Parse.handle_pdf', return_value=(test_image, "PDF")), \
             patch('app.Parse.extract_boxes_from_image', return_value=[(10, 10, 100, 100)]), \
             patch('app.Parse.get_subjects_data') as mock_subjects, \
             patch('app.Parse.create_courses') as mock_courses:

            # Setup realistic mock data
            mock_subjects.return_value = [{
                "details": "CS 101 ID: CS101 Activity: Lecture Section: A Campus: Main Room: 201",
                "day": "MONDAY",
                "time": ["08:00", "09:30"]
            }]

            from app.Parse import Course
            mock_courses.return_value = [
                Course(name="CS 101", id="CS101", day="MONDAY", duration="08:00-09:30")
            ]

            result = await parse(mock_file, "CHROME")

            assert b'BEGIN:VCALENDAR' in result
            assert b'CS 101' in result
            assert b'RRULE:FREQ=WEEKLY' in result
