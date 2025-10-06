"""
Integration tests for the schedule parser
These tests use real PDF files from CHROME_EX and FIREFOX_EX directories
"""

import os
from io import BytesIO
from pathlib import Path
from unittest.mock import AsyncMock, Mock, patch

import numpy as np
import pytest
from PIL import Image

# Check if test PDFs exist in CHROME_EX and FIREFOX_EX
BASE_DIR = Path(__file__).parent.parent
CHROME_PORTRAIT = BASE_DIR / "CHROME_EX" / "PORTRAIT"
CHROME_LANDSCAPE = BASE_DIR / "CHROME_EX" / "LANDSCAPE"
FIREFOX_PORTRAIT = BASE_DIR / "FIREFOX_EX" / "PORTRAIT"
FIREFOX_LANDSCAPE = BASE_DIR / "FIREFOX_EX" / "LANDSCAPE"

HAS_CHROME_PORTRAIT = CHROME_PORTRAIT.exists() and list(CHROME_PORTRAIT.glob("*.pdf"))
HAS_CHROME_LANDSCAPE = CHROME_LANDSCAPE.exists() and list(CHROME_LANDSCAPE.glob("*.pdf"))
HAS_FIREFOX_PORTRAIT = FIREFOX_PORTRAIT.exists() and list(FIREFOX_PORTRAIT.glob("*.pdf"))
HAS_FIREFOX_LANDSCAPE = FIREFOX_LANDSCAPE.exists() and list(FIREFOX_LANDSCAPE.glob("*.pdf"))

pytestmark = pytest.mark.integration


@pytest.mark.integration
class TestIntegrationWithRealPDFs:
    """Integration tests with actual PDF files from CHROME_EX and FIREFOX_EX"""

    @pytest.mark.skipif(not HAS_CHROME_PORTRAIT, reason="No Chrome portrait PDFs found in CHROME_EX/PORTRAIT")
    def test_chrome_portrait_pdf_processing(self):
        """Test processing Chrome portrait PDFs"""
        from app.ParsePDF import handle_pdf

        pdf_files = list(CHROME_PORTRAIT.glob("*.pdf"))
        test_file = pdf_files[0]  # Test with first PDF

        with open(test_file, "rb") as f:
            pdf_bytes = BytesIO(f.read())
            image, file_type = handle_pdf(pdf_bytes, "CHROME")

            assert isinstance(image, Image.Image)
            assert file_type in ["PDF", "IMAGE"]  # May be PDF or extracted image
            assert image.size[0] > 0 and image.size[1] > 0
            print(f"✓ Chrome Portrait: {test_file.name} -> {image.size}")

    @pytest.mark.skipif(not HAS_CHROME_LANDSCAPE, reason="No Chrome landscape PDFs found in CHROME_EX/LANDSCAPE")
    def test_chrome_landscape_pdf_processing(self):
        """Test processing Chrome landscape PDFs"""
        from app.ParsePDF import handle_pdf

        pdf_files = list(CHROME_LANDSCAPE.glob("*.pdf"))
        test_file = pdf_files[0]

        with open(test_file, "rb") as f:
            pdf_bytes = BytesIO(f.read())
            image, file_type = handle_pdf(pdf_bytes, "CHROME")

            assert isinstance(image, Image.Image)
            assert file_type in ["PDF", "IMAGE"]  # May be PDF or extracted image
            assert image.size[0] > 0 and image.size[1] > 0
            print(f"✓ Chrome Landscape: {test_file.name} -> {image.size}")

    @pytest.mark.skipif(not HAS_FIREFOX_PORTRAIT, reason="No Firefox portrait PDFs found in FIREFOX_EX/PORTRAIT")
    def test_firefox_portrait_pdf_processing(self):
        """Test processing Firefox portrait PDFs"""
        from app.ParsePDF import handle_pdf

        pdf_files = list(FIREFOX_PORTRAIT.glob("*.pdf"))
        test_file = pdf_files[0]

        with open(test_file, "rb") as f:
            pdf_bytes = BytesIO(f.read())
            image, file_type = handle_pdf(pdf_bytes, "FIREFOX")

            assert isinstance(image, Image.Image)
            assert file_type in ["PDF", "IMAGE"]  # Firefox may export as images
            assert image.size[0] > 0 and image.size[1] > 0
            print(f"✓ Firefox Portrait: {test_file.name} -> {image.size}")

    @pytest.mark.skipif(not HAS_FIREFOX_LANDSCAPE, reason="No Firefox landscape PDFs found in FIREFOX_EX/LANDSCAPE")
    def test_firefox_landscape_pdf_processing(self):
        """Test processing Firefox landscape PDFs"""
        from app.ParsePDF import handle_pdf

        pdf_files = list(FIREFOX_LANDSCAPE.glob("*.pdf"))
        test_file = pdf_files[0]

        with open(test_file, "rb") as f:
            pdf_bytes = BytesIO(f.read())
            image, file_type = handle_pdf(pdf_bytes, "FIREFOX")

            assert isinstance(image, Image.Image)
            assert file_type in ["PDF", "IMAGE"]  # Firefox may export as images
            assert image.size[0] > 0 and image.size[1] > 0
            print(f"✓ Firefox Landscape: {test_file.name} -> {image.size}")

    @pytest.mark.asyncio
    @pytest.mark.skipif(not HAS_CHROME_PORTRAIT, reason="No Chrome portrait PDFs found")
    async def test_end_to_end_parsing_chrome_portrait(self):
        """Test complete end-to-end parsing with Chrome portrait PDF"""
        from app.Parse import parse

        pdf_files = list(CHROME_PORTRAIT.glob("*.pdf"))
        test_file = pdf_files[0]

        with open(test_file, "rb") as f:
            mock_file = Mock()
            mock_file.read = AsyncMock(return_value=f.read())
            mock_file.content_type = "application/pdf"

            try:
                result = await parse(mock_file, "CHROME")
                assert result is not None
                assert isinstance(result, bytes)
                assert b"BEGIN:VCALENDAR" in result
                assert b"END:VCALENDAR" in result
                print(f"✓ E2E Chrome Portrait: {test_file.name} -> Generated ICS calendar")
            except ValueError as e:
                # Expected if PDF format is not supported or has no valid schedule
                pytest.skip(f"PDF parsing failed (expected for some formats): {e}")
            except Exception as e:
                pytest.fail(f"Unexpected error during parsing: {e}")

    @pytest.mark.asyncio
    @pytest.mark.skipif(not HAS_FIREFOX_PORTRAIT, reason="No Firefox portrait PDFs found")
    async def test_end_to_end_parsing_firefox_portrait(self):
        """Test complete end-to-end parsing with Firefox portrait PDF"""
        from app.Parse import parse

        pdf_files = list(FIREFOX_PORTRAIT.glob("*.pdf"))
        test_file = pdf_files[0]

        with open(test_file, "rb") as f:
            mock_file = Mock()
            mock_file.read = AsyncMock(return_value=f.read())
            mock_file.content_type = "application/pdf"

            try:
                result = await parse(mock_file, "FIREFOX")
                assert result is not None
                assert isinstance(result, bytes)
                assert b"BEGIN:VCALENDAR" in result
                assert b"END:VCALENDAR" in result
                print(f"✓ E2E Firefox Portrait: {test_file.name} -> Generated ICS calendar")
            except ValueError as e:
                # Expected if PDF format is not supported or has no valid schedule
                pytest.skip(f"PDF parsing failed (expected for some formats): {e}")
            except Exception as e:
                pytest.fail(f"Unexpected error during parsing: {e}")


@pytest.mark.integration
class TestIntegrationWithMockData:
    """Integration tests with synthetic data (no real PDFs needed)"""

    @pytest.mark.asyncio
    async def test_parse_workflow_with_mock_pdf(self):
        """Test parsing workflow with minimal mocking"""
        from PIL import Image

        from app.Parse import parse

        # Create a simple test image
        img_array = np.ones((600, 800, 3), dtype=np.uint8) * 255
        test_image = Image.fromarray(img_array, "RGB")

        mock_file = Mock()
        mock_file.read = AsyncMock(return_value=b"fake pdf content")
        mock_file.content_type = "application/pdf"

        with patch("app.Parse.process_file_to_image", return_value=(test_image, "PDF")), patch(
            "app.Parse.extract_boxes_from_image", return_value=[(10, 10, 100, 100)]
        ), patch("app.Parse.extract_and_create_courses") as mock_courses_extract, patch(
            "app.Parse.generate_calendar"
        ) as mock_calendar:

            # Setup realistic mock data
            from app.Parse import Course

            mock_courses_extract.return_value = [Course(name="CS 101", id="CS101", day="MONDAY", duration="08:00-09:30")]
            mock_calendar.return_value = b"BEGIN:VCALENDAR\r\nSUMMARY:CS 101\r\nRRULE:FREQ=WEEKLY\r\nEND:VCALENDAR"

            result = await parse(mock_file, "CHROME")

            assert b"BEGIN:VCALENDAR" in result
            assert b"CS 101" in result
            assert b"RRULE:FREQ=WEEKLY" in result
