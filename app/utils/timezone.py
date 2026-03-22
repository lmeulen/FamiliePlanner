"""Timezone utilities for consistent datetime handling."""

from datetime import datetime, timezone
from zoneinfo import ZoneInfo

# Default timezone for the application (UTC)
UTC = timezone.utc


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
    Convert datetime to naive UTC datetime (for SQLite storage).

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
    Convert naive UTC datetime (from SQLite) to timezone-aware UTC datetime.

    Args:
        dt: Naive datetime assumed to be in UTC

    Returns:
        Timezone-aware UTC datetime
    """
    if dt.tzinfo is not None:
        return dt  # Already aware

    return dt.replace(tzinfo=UTC)


async def get_user_timezone(db) -> str:
    """
    Get user's preferred timezone from settings.

    Args:
        db: AsyncSession database connection

    Returns:
        Timezone name (e.g., "Europe/Amsterdam", "America/New_York")
    """
    from app.models.settings import AppSetting

    setting = await db.get(AppSetting, "timezone")
    return setting.value if setting else "UTC"
