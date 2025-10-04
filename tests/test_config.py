"""
Unit tests for Configuration module
"""
import pytest
import os
from app.config import Config


class TestConfig:
    """Tests for configuration settings"""

    def test_default_values(self):
        """Test default configuration values"""
        config = Config()
        assert config.MAX_FILE_SIZE > 0
        assert len(config.VALID_BROWSERS) > 0
        assert "CHROME" in config.VALID_BROWSERS
        assert config.OCR_DPI == 300
        assert config.SCHEDULE_DURATION_WEEKS == 19

    def test_box_extraction_config(self):
        """Test box extraction configuration"""
        config = Config()
        assert config.BOX_EXTRACTION["min_width"] > 0
        assert config.BOX_EXTRACTION["min_height"] > 0
        assert config.BOX_EXTRACTION["area_threshold_pdf"] > 0
        assert 0 < config.BOX_EXTRACTION["iou_threshold"] < 1

    def test_timezone_config(self):
        """Test timezone configuration"""
        config = Config()
        assert "KSA" in config.TIMEZONES
        assert "ALG" in config.TIMEZONES
        assert config.TIMEZONES["KSA"] == "Asia/Riyadh"
        assert config.TIMEZONES["ALG"] == "Africa/Algiers"

    def test_days_config(self):
        """Test day name configuration"""
        config = Config()
        assert "MONDAY" in config.DAYS_ENGLISH
        assert "LUNDI" in config.DAYS_FRENCH
        assert len(config.DAYS_ENGLISH) == 7
        assert len(config.DAYS_FRENCH) == 7

    def test_pdf_crop_points(self):
        """Test PDF crop point configuration"""
        config = Config()
        assert "CHROME" in config.PDF_CROP_POINTS
        assert "FIREFOX" in config.PDF_CROP_POINTS
        assert "page1_crop" in config.PDF_CROP_POINTS["CHROME"]
        assert "page2_crop" in config.PDF_CROP_POINTS["CHROME"]
