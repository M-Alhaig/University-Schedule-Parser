"""
Unit tests for Parse module
"""
import pytest
from PIL import Image
import numpy as np
from app.Parse import (
    calculate_iou,
    filter_duplicate_boxes,
    Course,
    create_courses
)


class TestCalculateIOU:
    """Tests for IoU calculation"""

    def test_no_overlap(self):
        """Test boxes with no overlap"""
        box1 = (0, 0, 10, 10)
        box2 = (20, 20, 10, 10)
        assert calculate_iou(box1, box2) == 0.0

    def test_complete_overlap(self):
        """Test identical boxes"""
        box1 = (10, 10, 20, 20)
        box2 = (10, 10, 20, 20)
        assert calculate_iou(box1, box2) == 1.0

    def test_partial_overlap(self):
        """Test boxes with partial overlap"""
        box1 = (0, 0, 20, 20)  # area = 400
        box2 = (10, 10, 20, 20)  # area = 400
        # Overlap area = 10x10 = 100
        # Union = 400 + 400 - 100 = 700
        # IoU = 100/700 ≈ 0.143
        iou = calculate_iou(box1, box2)
        assert 0.14 < iou < 0.15


class TestFilterDuplicateBoxes:
    """Tests for duplicate box filtering"""

    def test_no_duplicates(self):
        """Test filtering when no duplicates exist"""
        boxes = [(0, 0, 10, 10), (50, 50, 10, 10), (100, 100, 10, 10)]
        filtered = filter_duplicate_boxes(boxes, iou_threshold=0.5)
        assert len(filtered) == 3

    def test_exact_duplicates(self):
        """Test filtering exact duplicate boxes"""
        boxes = [(10, 10, 20, 20), (10, 10, 20, 20), (10, 10, 20, 20)]
        filtered = filter_duplicate_boxes(boxes, iou_threshold=0.8)
        assert len(filtered) == 1

    def test_high_overlap_duplicates(self):
        """Test filtering boxes with high overlap"""
        boxes = [(10, 10, 20, 20), (11, 11, 20, 20), (50, 50, 10, 10)]
        filtered = filter_duplicate_boxes(boxes, iou_threshold=0.7)
        # First two should be considered duplicates
        assert len(filtered) == 2


class TestCreateCourses:
    """Tests for course creation from subjects"""

    def test_full_course_details(self):
        """Test creating course with all details"""
        subjects = [{
            "details": "MATH 101 ID: MTH101 Activity: Lecture Section: A Campus: Main Room: 201",
            "day": "MONDAY",
            "time": ["08:00", "09:30"]
        }]
        courses = create_courses(subjects)
        assert len(courses) == 1
        assert courses[0].name == "MATH 101"
        assert courses[0].id == "MTH101"
        assert courses[0].activity == "Lecture"
        assert courses[0].section == "A"
        assert courses[0].campus == "Main"
        assert courses[0].room == "201"
        assert courses[0].day == "MONDAY"
        assert courses[0].duration == "08:0009:30"

    def test_minimal_course_details(self):
        """Test creating course with minimal details"""
        subjects = [{
            "details": "Introduction to Physics",
            "day": "TUESDAY",
            "time": ["10:00", "11:30"]
        }]
        courses = create_courses(subjects)
        assert len(courses) == 1
        assert courses[0].name == "Introduction to Physics"
        assert courses[0].id == ""
        assert courses[0].day == "TUESDAY"

    def test_invalid_format(self):
        """Test handling of invalid subject format"""
        subjects = [{
            "details": "",
            "day": "WEDNESDAY",
            "time": ["14:00", "15:30"]
        }]
        courses = create_courses(subjects)
        # Should skip invalid entries
        assert len(courses) == 0


class TestCourseModel:
    """Tests for Course Pydantic model"""

    def test_course_creation(self):
        """Test creating a Course instance"""
        course = Course(
            name="Test Course",
            id="TC101",
            activity="Lab",
            section="B",
            campus="North",
            room="305",
            day="FRIDAY",
            duration="13:00-14:30"
        )
        assert course.name == "Test Course"
        assert course.id == "TC101"

    def test_course_defaults(self):
        """Test Course with default values"""
        course = Course(
            name="Minimal Course",
            day="THURSDAY",
            duration="09:00-10:00"
        )
        assert course.id == ""
        assert course.activity == ""
        assert course.section == ""
