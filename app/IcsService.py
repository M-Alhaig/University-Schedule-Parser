from icalendar import Calendar, Event
from datetime import datetime, time, timedelta
import pytz
import logging
from app.config import config

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


def parse_duration(duration, day, time_zone="KSA"):
    days_map = {
        "MONDAY":0,
        "TUESDAY":1,
        "WEDNESDAY":2,
        "THURSDAY":3,
        "FRIDAY":4,
        "SATURDAY":5,
        "SUNDAY":6,
    }
    logger.debug(f"Parsing duration '{duration}' for {day} in {time_zone} timezone")

    start, finish = duration.split('-')
    target_day = days_map[day.upper()]
    today = datetime.today().weekday()

    days_ahead = target_day - today
    if days_ahead < 0:
        days_ahead += 7

    start_hour, start_minute = map(int,start.split(':'))
    finish_hour, finish_minute = map(int, finish.split(':'))

    date = datetime.today() + timedelta(days=days_ahead)

    timezone_str = config.TIMEZONES.get(time_zone, config.TIMEZONES[config.DEFAULT_TIMEZONE])
    timezone = pytz.timezone(timezone_str)
    logger.debug(f"Using timezone: {timezone_str}")

    start_time = datetime.combine(date, time(start_hour, start_minute))
    start_time = timezone.localize(start_time)

    end_time = datetime.combine(date, time(finish_hour, finish_minute))
    end_time = timezone.localize(end_time)

    return start_time, end_time, timezone

def create_schedule_ics(courses):
    logger.info(f"Creating ICS calendar for {len(courses)} courses")
    cal = Calendar()
    cal.add('prodid', '-//University Schedule//')
    cal.add('version', '2.0')

    for i, course in enumerate(courses):
        event = Event()
        start_time, end_time, timezone = parse_duration(course.duration, course.day)
        until = (start_time + timedelta(weeks=config.SCHEDULE_DURATION_WEEKS)).replace(tzinfo=timezone)

        event.add('summary', course.name)

        event.add('description',
                  f"Course ID: {course.id}\n"
                  f"Activity: {course.activity}\n"
                  f"Section: {course.section}")

        event.add('dtstart', start_time)
        event.add('dtend', end_time)

        event.add('rrule', {'freq': 'weekly', 'until': until})

        event.add('uid',
                  f"{course.id}-{course.section}-{course.duration}@university.edu")

        event.add('dtstamp', datetime.now(timezone))

        event.add('location', f"{course.campus}, Room {course.room}")

        cal.add_component(event)
        logger.debug(f"Added event {i+1}/{len(courses)}: {course.name} ({course.day} {course.duration})")

    logger.info(f"Successfully created calendar with {len(courses)} events spanning {config.SCHEDULE_DURATION_WEEKS} weeks")
    return cal.to_ical()