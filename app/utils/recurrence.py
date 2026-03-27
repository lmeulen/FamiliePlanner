"""Shared recurrence utilities using RFC 5545 RRULE standard."""

import re
from datetime import date, datetime

from dateutil.rrule import (
    DAILY,
    FR,
    MO,
    MONTHLY,
    SA,
    SU,
    TH,
    TU,
    WE,
    WEEKLY,
    YEARLY,
    rrule,
    rrulestr,
)

from app.enums import RecurrenceType

MAX_OCCURRENCES = 365


def generate_occurrence_dates(
    recurrence_type: RecurrenceType,
    series_start: date,
    series_end: date | None = None,
    interval: int = 1,
    count: int | None = None,
    monthly_pattern: str | None = None,
    rrule_string: str | None = None,
) -> list[date]:
    """
    Generate occurrence dates for a recurrence series using RRULE standard.

    Args:
        recurrence_type: Basic recurrence pattern (daily, weekly, monthly, etc.)
        series_start: First occurrence date
        series_end: Last possible occurrence date (mutually exclusive with count)
        interval: Interval between occurrences (e.g., 2 = every 2 days/weeks)
        count: Number of occurrences (mutually exclusive with series_end)
        monthly_pattern: Pattern for monthly recurrence (e.g., "first_monday", "last_friday")
        rrule_string: Custom RFC 5545 RRULE string for advanced patterns

    Returns:
        List of occurrence dates (max MAX_OCCURRENCES)
    """
    # Use custom RRULE string if provided (advanced patterns)
    if rrule_string:
        try:
            rule = rrulestr(rrule_string, dtstart=datetime.combine(series_start, datetime.min.time()))
            dates = [dt.date() for dt in rule[:MAX_OCCURRENCES]]
            return dates
        except Exception:
            # Fallback to enum-based generation if RRULE parsing fails
            pass

    # Build RRULE from parameters
    rule = _build_rrule_from_params(
        recurrence_type=recurrence_type,
        series_start=series_start,
        series_end=series_end,
        interval=interval,
        count=count,
        monthly_pattern=monthly_pattern,
    )

    # Generate dates from rule
    dates = [dt.date() for dt in rule]
    return dates[:MAX_OCCURRENCES]


def _build_rrule_from_params(
    recurrence_type: RecurrenceType,
    series_start: date,
    series_end: date | None = None,
    interval: int = 1,
    count: int | None = None,
    monthly_pattern: str | None = None,
) -> rrule:
    """Build python-dateutil rrule from parameters."""
    dtstart = datetime.combine(series_start, datetime.min.time())

    # Determine end condition (use either count OR until, never both)
    if count:
        occurrence_count = min(count, MAX_OCCURRENCES)
        until = None
    else:
        occurrence_count = None
        until = datetime.combine(series_end or series_start, datetime.max.time())

    # Map RecurrenceType to RRULE parameters
    if recurrence_type == RecurrenceType.daily:
        return rrule(DAILY, dtstart=dtstart, interval=interval, count=occurrence_count, until=until)

    elif recurrence_type == RecurrenceType.every_other_day:
        # Legacy pattern: every_other_day = daily with interval=2
        return rrule(DAILY, dtstart=dtstart, interval=2, count=occurrence_count, until=until)

    elif recurrence_type == RecurrenceType.weekly:
        return rrule(WEEKLY, dtstart=dtstart, interval=interval, count=occurrence_count, until=until)

    elif recurrence_type == RecurrenceType.biweekly:
        # Legacy pattern: biweekly = weekly with interval=2
        return rrule(WEEKLY, dtstart=dtstart, interval=2, count=occurrence_count, until=until)

    elif recurrence_type == RecurrenceType.weekdays:
        # Legacy pattern: weekdays = weekly on Mon-Fri
        return rrule(WEEKLY, dtstart=dtstart, byweekday=(MO, TU, WE, TH, FR), count=occurrence_count, until=until)

    elif recurrence_type == RecurrenceType.monthly:
        # Handle monthly patterns
        if monthly_pattern and monthly_pattern != "day_of_month":
            # Parse patterns like "first_monday", "last_friday"
            byweekday_param = _parse_monthly_pattern(monthly_pattern)
            if byweekday_param:
                return rrule(
                    MONTHLY,
                    dtstart=dtstart,
                    interval=interval,
                    byweekday=byweekday_param,
                    count=occurrence_count,
                    until=until,
                )

        # Default: same day of month
        return rrule(MONTHLY, dtstart=dtstart, interval=interval, count=occurrence_count, until=until)

    elif recurrence_type == RecurrenceType.yearly:
        return rrule(YEARLY, dtstart=dtstart, interval=interval, count=occurrence_count, until=until)

    # Fallback: daily
    return rrule(DAILY, dtstart=dtstart, interval=interval, count=occurrence_count, until=until)


def _parse_monthly_pattern(monthly_pattern: str) -> tuple | None:
    """
    Convert monthly patterns to python-dateutil byweekday parameter.

    Examples:
        "first_monday" -> MO(+1)
        "last_friday" -> FR(-1)
        "second_tuesday" -> TU(+2)
    """
    weekday_map = {
        "monday": MO,
        "tuesday": TU,
        "wednesday": WE,
        "thursday": TH,
        "friday": FR,
        "saturday": SA,
        "sunday": SU,
    }

    position_map = {
        "first": 1,
        "second": 2,
        "third": 3,
        "fourth": 4,
        "last": -1,
    }

    # Parse pattern like "first_monday"
    match = re.match(
        r"^(first|second|third|fourth|last)_(monday|tuesday|wednesday|thursday|friday|saturday|sunday)$",
        monthly_pattern,
    )
    if not match:
        return None

    position_str, weekday_str = match.groups()
    position = position_map.get(position_str)
    weekday = weekday_map.get(weekday_str)

    if position and weekday:
        return (weekday(position),)

    return None
