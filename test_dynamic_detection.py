"""
Test script for dynamic PDF boundary detection
Tests all sample PDFs with the new vertical line detection approach
"""
import os
from pathlib import Path
from io import BytesIO
from app.ParsePDF import handle_pdf
import logging

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def test_pdf(pdf_path: Path, browser: str):
    """Test a single PDF file"""
    try:
        logger.info(f"\n{'='*80}")
        logger.info(f"Testing: {pdf_path.name} (Browser: {browser})")
        logger.info(f"{'='*80}")

        with open(pdf_path, 'rb') as f:
            pdf_bytes = BytesIO(f.read())
            image, file_type = handle_pdf(pdf_bytes, browser)

            logger.info(f"✓ Success: {pdf_path.name}")
            logger.info(f"  Image size: {image.width}x{image.height}")
            logger.info(f"  File type: {file_type}")

            # Save output for manual inspection
            output_dir = Path("test_output")
            output_dir.mkdir(exist_ok=True)
            output_path = output_dir / f"{pdf_path.stem}_processed.png"
            image.save(output_path)
            logger.info(f"  Saved to: {output_path}")

            return True

    except Exception as e:
        logger.error(f"✗ Failed: {pdf_path.name}")
        logger.error(f"  Error: {type(e).__name__}: {e}")
        return False

def main():
    """Test all PDFs"""
    base_dir = Path(__file__).parent

    test_dirs = [
        (base_dir / "CHROME_EX" / "PORTRAIT", "CHROME"),
        (base_dir / "CHROME_EX" / "LANDSCAPE", "CHROME"),
        (base_dir / "FIREFOX_EX" / "PORTRAIT", "FIREFOX"),
        (base_dir / "FIREFOX_EX" / "LANDSCAPE", "FIREFOX"),
    ]

    total = 0
    passed = 0
    failed = 0

    for test_dir, browser in test_dirs:
        if not test_dir.exists():
            logger.warning(f"Directory not found: {test_dir}")
            continue

        pdf_files = sorted(test_dir.glob("*.pdf"))

        for pdf_path in pdf_files:
            total += 1
            if test_pdf(pdf_path, browser):
                passed += 1
            else:
                failed += 1

    # Summary
    logger.info(f"\n{'='*80}")
    logger.info(f"TEST SUMMARY")
    logger.info(f"{'='*80}")
    logger.info(f"Total: {total}")
    logger.info(f"Passed: {passed}")
    logger.info(f"Failed: {failed}")
    logger.info(f"Success Rate: {(passed/total*100) if total > 0 else 0:.1f}%")

if __name__ == "__main__":
    main()
