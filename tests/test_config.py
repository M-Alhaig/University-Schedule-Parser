"""
Unit tests for Configuration module
"""

import os

import pytest

from app.config import Config


class TestConfig:
    """Tests for configuration settings"""

    def test_default_values(self):
        """Test default configuration values"""
        config = Config()
        assert config.MAX_FILE_SIZE > 0
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

    def test_vertical_line_detection_config(self):
        """Test vertical line detection configuration"""
        config = Config()
        assert config.VERTICAL_LINE_MIN_LENGTH > 0
        assert config.VERTICAL_KERNEL_HEIGHT > 0
        assert config.VERTICAL_KERNEL_WIDTH > 0
        assert config.EDGE_CLUSTER_THRESHOLD > 0
        assert config.MIN_VERTICAL_LINES_COUNT > 0
