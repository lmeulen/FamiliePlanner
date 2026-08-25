"""Timezone utilities.

Storage policy: naive ``datetime`` columns hold **wall-clock time in the app
timezone**, not UTC. Conversion happens only at external boundaries (ICS
import/export, third-party calendar sync). Use :func:`now_local` /
:func:`today_local` instead of ``datetime.now()`` / ``date.today()`` so the
server's own timezone (often UTC inside Docker) never leaks into stored data.

The UTC helpers lower down are boundary utilities and are not used for storage.
"""

from datetime import date, datetime, timezone
from typing import Any
from zoneinfo import ZoneInfo, available_timezones

from app.config import APP_TIMEZONE

# Default timezone for the application (UTC)
UTC = timezone.utc

_app_tz_name: str = APP_TIMEZONE
_app_tz: ZoneInfo = ZoneInfo(APP_TIMEZONE)


# ── App timezone ────────────────────────────────────────────────────────────


def app_timezone_name() -> str:
    """Return the configured IANA timezone name (e.g. ``Europe/Amsterdam``)."""
    return _app_tz_name


def app_tz() -> ZoneInfo:
    """Return the configured application timezone."""
    return _app_tz


def set_app_timezone(name: str) -> None:
    """Set the process-wide application timezone. Raises ValueError if invalid."""
    global _app_tz_name, _app_tz

    if name not in available_timezones():
        raise ValueError(f"Onbekende timezone: {name}")

    _app_tz_name = name
    _app_tz = ZoneInfo(name)


async def load_app_timezone(db: Any) -> str:
    """Load the timezone from settings at startup, seeding it when absent.

    A stored ``UTC`` is treated as the un-migrated legacy default rather than a
    deliberate choice, because it silently mislabels every exported timestamp.
    """
    from app.models.settings import AppSetting

    row = await db.get(AppSetting, "timezone")
    if row is None:
        db.add(AppSetting(key="timezone", value=APP_TIMEZONE))
        await db.commit()
        set_app_timezone(APP_TIMEZONE)
        return APP_TIMEZONE

    if row.value == "UTC" and APP_TIMEZONE != "UTC":
        row.value = APP_TIMEZONE
        await db.commit()
        set_app_timezone(APP_TIMEZONE)
        return APP_TIMEZONE

    try:
        set_app_timezone(row.value)
    except ValueError:
        set_app_timezone(APP_TIMEZONE)
        return APP_TIMEZONE

    return str(row.value)


# ── Wall-clock helpers (use these for stored values) ────────────────────────


def now_local() -> datetime:
    """Current wall-clock time in the app timezone, as a naive datetime."""
    return datetime.now(_app_tz).replace(tzinfo=None)


def today_local() -> date:
    """Current date in the app timezone."""
    return datetime.now(_app_tz).date()


def to_local_naive(dt: datetime) -> datetime:
    """Normalise an incoming datetime to naive app-local wall-clock time.

    Naive input is treated as already local (a floating iCalendar time).
    """
    if dt.tzinfo is None:
        return dt
    return dt.astimezone(_app_tz).replace(tzinfo=None)


def to_aware(dt: datetime) -> datetime:
    """Attach the app timezone to a naive stored datetime."""
    if dt.tzinfo is not None:
        return dt
    return dt.replace(tzinfo=_app_tz)


def now_utc_aware() -> datetime:
    """Timezone-aware UTC now, for protocol fields such as iCalendar DTSTAMP."""
    return datetime.now(UTC)


# ── UTC boundary helpers ────────────────────────────────────────────────────


def now_utc() -> datetime:
    """Get current time in UTC with timezone awareness."""
    return datetime.now(UTC)


def to_utc(dt: datetime, from_tz: str = "UTC") -> datetime:
    """
    Convert datetime to UTC.

    Args:
        dt: Datetime to convert (can be naive or aware)
        from_tz: Source timezone name (e.g., "Europe/Amsterdam", "America/New_York")
                 Only used if dt is naive. Defaults to UTC.

    Returns:
        Timezone-aware datetime in UTC
    """
    if dt.tzinfo is None:
        # Naive datetime - assume it's in from_tz
        if from_tz == "UTC":
            dt = dt.replace(tzinfo=UTC)
        else:
            tz = ZoneInfo(from_tz)
            dt = dt.replace(tzinfo=tz)

    # Convert to UTC
    return dt.astimezone(UTC)


def from_utc(dt: datetime, to_tz: str = "UTC") -> datetime:
    """
    Convert UTC datetime to target timezone.

    Args:
        dt: UTC datetime (should be timezone-aware)
        to_tz: Target timezone name (e.g., "Europe/Amsterdam", "America/New_York")

    Returns:
        Timezone-aware datetime in target timezone
    """
    if dt.tzinfo is None:
        # Assume naive datetime is UTC
        dt = dt.replace(tzinfo=UTC)

    if to_tz == "UTC":
        return dt.astimezone(UTC)

    tz = ZoneInfo(to_tz)
    return dt.astimezone(tz)


def to_naive_utc(dt: datetime, from_tz: str = "UTC") -> datetime:
    """
    Convert datetime to naive UTC datetime.

    Args:
        dt: Datetime to convert
        from_tz: Source timezone if dt is naive

    Returns:
        Naive datetime in UTC (no timezone info)
    """
    utc_dt = to_utc(dt, from_tz)
    return utc_dt.replace(tzinfo=None)


def from_naive_utc(dt: datetime) -> datetime:
    """
    Convert naive UTC datetime to timezone-aware UTC datetime.

    Args:
        dt: Naive datetime assumed to be in UTC

    Returns:
        Timezone-aware UTC datetime
    """
    if dt.tzinfo is not None:
        return dt  # Already aware

    return dt.replace(tzinfo=UTC)


async def get_user_timezone(db: Any) -> str:
    """
    Get user's preferred timezone from settings.

    Args:
        db: AsyncSession database connection

    Returns:
        Timezone name (e.g., "Europe/Amsterdam", "America/New_York")
    """
    from app.models.settings import AppSetting

    setting = await db.get(AppSetting, "timezone")
    return setting.value if setting else app_timezone_name()
