"""Shared recurrence utilities used by both agenda and task routers."""

import calendar as cal_mod
from datetime import date, timedelta

from app.enums import RecurrenceType


def generate_occurrence_dates(
    recurrence_type: RecurrenceType,
    series_start: date,
    series_end: date,
) -> list[date]:
    """Return every occurrence date for a recurrence series (max 365 items)."""
    results: list[date] = []
    current: date = series_start
    MAX = 365

    while current <= series_end and len(results) < MAX:
        if recurrence_type == RecurrenceType.weekdays:
            if current.weekday() < 5:  # Mon=0 … Fri=4
                results.append(current)
            current += timedelta(days=1)
        elif recurrence_type == RecurrenceType.monthly:
            results.append(current)
            mo = current.month + 1
            yr = current.year
            if mo > 12:
                mo, yr = 1, yr + 1
            day = min(series_start.day, cal_mod.monthrange(yr, mo)[1])
            current = date(yr, mo, day)
        else:
            results.append(current)
            delta = {
                RecurrenceType.daily: timedelta(days=1),
                RecurrenceType.every_other_day: timedelta(days=2),
                RecurrenceType.weekly: timedelta(weeks=1),
                RecurrenceType.biweekly: timedelta(weeks=2),
            }[recurrence_type]
            current += delta

    return results
