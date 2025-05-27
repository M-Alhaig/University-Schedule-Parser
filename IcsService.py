from icalendar import Calendar, Event
from datetime import datetime, time, timedelta
import pytz



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
    start, finish = duration.split('-')
    target_day = days_map[day.upper()]
    today = datetime.today().weekday()

    days_ahead = target_day - today
    if days_ahead < 0:
        days_ahead += 7


    start_hour, start_minute = map(int,start.split(':'))
    finish_hour, finish_minute = map(int, finish.split(':'))

    date = datetime.today() + timedelta(days=days_ahead)

    timezone = pytz.timezone('Asia/Riyadh')
    if time_zone == "ALG":
        timezone = pytz.timezone('Africa/Algiers')

    start_time = datetime.combine(date, time(start_hour, start_minute))
    start_time = timezone.localize(start_time)

    end_time = datetime.combine(date, time(finish_hour, finish_minute))
    end_time = timezone.localize(end_time)

    return start_time, end_time, timezone

def create_schedule_ics(courses):
    cal = Calendar()
    cal.add('prodid', '-//University Schedule//Student Portal//')
    cal.add('version', '2.0')

    for course in courses:
        event = Event()
        start_time, end_time, timezone = parse_duration(course.duration, course.day)
        until = (start_time + timedelta(weeks=13)).replace(tzinfo=timezone)

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

    with open("calendar.ics", 'wb') as f:
        f.write(cal.to_ical())