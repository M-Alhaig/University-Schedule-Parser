"""
Unit tests for ICS Service module
"""
import pytest
from datetime import datetime, timedelta
from app.IcsService import parse_duration, create_schedule_ics
from app.Parse import Course


class TestParseDuration:
    """Tests for duration parsing"""

    def test_parse_valid_duration(self):
        """Test parsing valid duration string"""
        start_time, end_time, timezone = parse_duration("08:00-09:30", "MONDAY", "KSA")

        # Check that times are parsed correctly
        assert start_time.hour == 8
        assert start_time.minute == 0
        assert end_time.hour == 9
        assert end_time.minute == 30

        # Check timezone
        assert str(timezone) == "Asia/Riyadh"

    def test_parse_duration_algeria_timezone(self):
        """Test parsing with Algeria timezone"""
        start_time, end_time, timezone = parse_duration("14:00-15:30", "TUESDAY", "ALG")
        assert str(timezone) == "Africa/Algiers"

    def test_parse_duration_different_days(self):
        """Test parsing for different days of week"""
        days = ["MONDAY", "TUESDAY", "WEDNESDAY", "THURSDAY", "FRIDAY", "SATURDAY", "SUNDAY"]
        for day in days:
            start_time, end_time, timezone = parse_duration("10:00-11:00", day, "KSA")
            assert start_time is not None
            assert end_time is not None

    def test_duration_difference(self):
        """Test that start and end times have correct duration"""
        start_time, end_time, timezone = parse_duration("10:00-12:30", "WEDNESDAY", "KSA")
        duration = end_time - start_time
        assert duration == timedelta(hours=2, minutes=30)


class TestCreateScheduleICS:
    """Tests for ICS calendar creation"""

    def test_create_empty_calendar(self):
        """Test creating calendar with no courses"""
        courses = []
        ics_bytes = create_schedule_ics(courses)
        assert ics_bytes is not None
        assert b'BEGIN:VCALENDAR' in ics_bytes
        assert b'END:VCALENDAR' in ics_bytes

    def test_create_single_course_calendar(self):
        """Test creating calendar with single course"""
        courses = [
            Course(
                name="Test Course",
                id="TC101",
                activity="Lecture",
                section="A",
                campus="Main",
                room="201",
                day="MONDAY",
                duration="08:00-09:30"
            )
        ]
        ics_bytes = create_schedule_ics(courses)

        assert b'BEGIN:VCALENDAR' in ics_bytes
        assert b'BEGIN:VEVENT' in ics_bytes
        assert b'Test Course' in ics_bytes
        assert b'TC101' in ics_bytes
        assert b'RRULE:FREQ=WEEKLY' in ics_bytes

    def test_create_multiple_courses_calendar(self):
        """Test creating calendar with multiple courses"""
        courses = [
            Course(name="Math", day="MONDAY", duration="08:00-09:00"),
            Course(name="Physics", day="TUESDAY", duration="10:00-11:00"),
            Course(name="Chemistry", day="WEDNESDAY", duration="14:00-15:00"),
        ]
        ics_bytes = create_schedule_ics(courses)

        # Should have 3 events
        assert ics_bytes.count(b'BEGIN:VEVENT') == 3
        assert ics_bytes.count(b'END:VEVENT') == 3

        assert b'Math' in ics_bytes
        assert b'Physics' in ics_bytes
        assert b'Chemistry' in ics_bytes

    def test_calendar_structure(self):
        """Test ICS calendar has proper structure"""
        courses = [
            Course(name="Test", day="FRIDAY", duration="13:00-14:00")
        ]
        ics_bytes = create_schedule_ics(courses)
        ics_string = ics_bytes.decode('utf-8')

        # Check required ICS components
        assert 'BEGIN:VCALENDAR' in ics_string
        assert 'VERSION:2.0' in ics_string
        assert 'PRODID:-//University Schedule//' in ics_string
        assert 'BEGIN:VEVENT' in ics_string
        assert 'SUMMARY:Test' in ics_string
        assert 'DTSTART' in ics_string
        assert 'DTEND' in ics_string
        assert 'RRULE:FREQ=WEEKLY' in ics_string
        assert 'END:VEVENT' in ics_string
        assert 'END:VCALENDAR' in ics_string
