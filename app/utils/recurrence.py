"""Shared recurrence utilities using RFC 5545 RRULE standard."""

import re
from datetime import date, datetime, timedelta

from dateutil.rrule import (  # type: ignore[import-untyped]
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
from loguru import logger

from app.enums import RecurrenceType
from app.utils.timezone import today_local

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

    Infinite Series Rolling Window:
        When both ``series_end`` and ``count`` are ``None``, the series is treated as
        infinite and generated through a rolling window from ``series_start`` through
        ``today + 365 days`` (computed fresh on every call). This means older series
        can contain more than ~52 weekly items if ``series_start`` is in the past,
        because the window is anchored on "today" for its upper bound.

        Ongoing maintenance is handled by ``app/recurrence_scheduler.py`` which
        regenerates future non-exception occurrences daily when fewer than 30 days
        remain, while preserving ``is_exception=True`` items.
    """
    # Handle infinite series with rolling window
    if series_end is None and count is None:
        today = today_local()
        # Generate 1 year ahead from today (not from series_start!)
        effective_end = today + timedelta(days=365)
        series_end = effective_end
        logger.debug("recurrence.rolling_window window_end={}", effective_end)

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


# ── RFC 5545 RRULE strings (for external calendars) ─────────────────────────

_RRULE_BYDAY = {
    "monday": "MO",
    "tuesday": "TU",
    "wednesday": "WE",
    "thursday": "TH",
    "friday": "FR",
    "saturday": "SA",
    "sunday": "SU",
}

_RRULE_POSITION = {"first": "1", "second": "2", "third": "3", "fourth": "4", "last": "-1"}


def build_rrule_string(
    recurrence_type: RecurrenceType,
    interval: int = 1,
    monthly_pattern: str | None = None,
    count: int | None = None,
    until_utc: datetime | None = None,
) -> str:
    """Build an RFC 5545 RRULE line for external calendars (Google, CalDAV).

    ``until_utc`` must already be UTC: RFC 5545 requires a UTC UNTIL whenever
    DTSTART carries a TZID. Omitting both ``count`` and ``until_utc`` yields a
    genuinely infinite rule, which is what an infinite series maps to.
    """
    parts: list[str] = []

    if recurrence_type == RecurrenceType.daily:
        parts.append("FREQ=DAILY")
        if interval > 1:
            parts.append(f"INTERVAL={interval}")
    elif recurrence_type == RecurrenceType.every_other_day:
        parts.extend(["FREQ=DAILY", "INTERVAL=2"])
    elif recurrence_type == RecurrenceType.weekly:
        parts.append("FREQ=WEEKLY")
        if interval > 1:
            parts.append(f"INTERVAL={interval}")
    elif recurrence_type == RecurrenceType.biweekly:
        parts.extend(["FREQ=WEEKLY", "INTERVAL=2"])
    elif recurrence_type == RecurrenceType.weekdays:
        parts.extend(["FREQ=WEEKLY", "BYDAY=MO,TU,WE,TH,FR"])
    elif recurrence_type == RecurrenceType.monthly:
        parts.append("FREQ=MONTHLY")
        if interval > 1:
            parts.append(f"INTERVAL={interval}")
        byday = _monthly_pattern_to_byday(monthly_pattern)
        if byday:
            parts.append(f"BYDAY={byday}")
    elif recurrence_type == RecurrenceType.yearly:
        parts.append("FREQ=YEARLY")
        if interval > 1:
            parts.append(f"INTERVAL={interval}")
    else:
        parts.append("FREQ=DAILY")

    if count:
        parts.append(f"COUNT={count}")
    elif until_utc is not None:
        parts.append(f"UNTIL={until_utc.strftime('%Y%m%dT%H%M%SZ')}")

    return "RRULE:" + ";".join(parts)


def _monthly_pattern_to_byday(monthly_pattern: str | None) -> str | None:
    if not monthly_pattern or monthly_pattern == "day_of_month":
        return None

    match = re.match(
        r"^(first|second|third|fourth|last)_(monday|tuesday|wednesday|thursday|friday|saturday|sunday)$",
        monthly_pattern,
    )
    if not match:
        return None

    position_str, weekday_str = match.groups()
    return f"{_RRULE_POSITION[position_str]}{_RRULE_BYDAY[weekday_str]}"
