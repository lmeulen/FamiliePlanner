"""Tests for timezone utility functions."""

from datetime import datetime, timezone
from zoneinfo import ZoneInfo

from app.utils.timezone import from_naive_utc, from_utc, to_naive_utc, to_utc


def test_to_utc_from_naive_utc():
    """Test converting naive UTC datetime to aware UTC."""
    naive_dt = datetime(2024, 1, 15, 14, 30)
    result = to_utc(naive_dt, "UTC")

    assert result.tzinfo == timezone.utc
    assert result.year == 2024
    assert result.month == 1
    assert result.day == 15
    assert result.hour == 14
    assert result.minute == 30


def test_to_utc_from_naive_amsterdam():
    """Test converting naive Amsterdam time to UTC."""
    # January 15 14:30 in Amsterdam (CET, UTC+1)
    naive_dt = datetime(2024, 1, 15, 14, 30)
    result = to_utc(naive_dt, "Europe/Amsterdam")

    assert result.tzinfo == timezone.utc
    # 14:30 CET = 13:30 UTC
    assert result.hour == 13
    assert result.minute == 30


def test_to_utc_from_aware_datetime():
    """Test converting timezone-aware datetime to UTC."""
    amsterdam_tz = ZoneInfo("Europe/Amsterdam")
    aware_dt = datetime(2024, 1, 15, 14, 30, tzinfo=amsterdam_tz)
    result = to_utc(aware_dt)

    assert result.tzinfo == timezone.utc
    # 14:30 CET = 13:30 UTC
    assert result.hour == 13
    assert result.minute == 30


def test_from_utc_to_amsterdam():
    """Test converting UTC to Amsterdam timezone."""
    utc_dt = datetime(2024, 1, 15, 13, 30, tzinfo=timezone.utc)
    result = from_utc(utc_dt, "Europe/Amsterdam")

    amsterdam_tz = ZoneInfo("Europe/Amsterdam")
    assert result.tzinfo == amsterdam_tz
    # 13:30 UTC = 14:30 CET
    assert result.hour == 14
    assert result.minute == 30


def test_from_utc_to_new_york():
    """Test converting UTC to New York timezone."""
    utc_dt = datetime(2024, 1, 15, 13, 30, tzinfo=timezone.utc)
    result = from_utc(utc_dt, "America/New_York")

    ny_tz = ZoneInfo("America/New_York")
    assert result.tzinfo == ny_tz
    # 13:30 UTC = 08:30 EST (UTC-5 in January)
    assert result.hour == 8
    assert result.minute == 30


def test_to_naive_utc():
    """Test converting datetime to naive UTC."""
    # From aware datetime
    amsterdam_tz = ZoneInfo("Europe/Amsterdam")
    aware_dt = datetime(2024, 1, 15, 14, 30, tzinfo=amsterdam_tz)
    result = to_naive_utc(aware_dt)

    assert result.tzinfo is None
    # 14:30 CET = 13:30 UTC
    assert result.hour == 13
    assert result.minute == 30


def test_to_naive_utc_from_naive_amsterdam():
    """Test converting naive Amsterdam time to naive UTC."""
    naive_dt = datetime(2024, 1, 15, 14, 30)
    result = to_naive_utc(naive_dt, "Europe/Amsterdam")

    assert result.tzinfo is None
    # 14:30 CET = 13:30 UTC
    assert result.hour == 13
    assert result.minute == 30


def test_from_naive_utc():
    """Test converting naive UTC to aware UTC."""
    naive_dt = datetime(2024, 1, 15, 13, 30)
    result = from_naive_utc(naive_dt)

    assert result.tzinfo == timezone.utc
    assert result.hour == 13
    assert result.minute == 30


def test_from_naive_utc_already_aware():
    """Test from_naive_utc with already aware datetime."""
    aware_dt = datetime(2024, 1, 15, 13, 30, tzinfo=timezone.utc)
    result = from_naive_utc(aware_dt)

    # Should return as-is
    assert result.tzinfo == timezone.utc
    assert result == aware_dt


def test_dst_transition():
    """Test handling of daylight saving time transitions."""
    # March 31, 2024 - DST starts in Amsterdam (CET -> CEST, UTC+1 -> UTC+2)
    # 2:00 AM becomes 3:00 AM

    # Before DST (March 30, 14:00 CET = 13:00 UTC)
    before_dst = datetime(2024, 3, 30, 14, 0)
    result_before = to_utc(before_dst, "Europe/Amsterdam")
    assert result_before.hour == 13  # UTC+1

    # After DST (April 1, 14:00 CEST = 12:00 UTC)
    after_dst = datetime(2024, 4, 1, 14, 0)
    result_after = to_utc(after_dst, "Europe/Amsterdam")
    assert result_after.hour == 12  # UTC+2


def test_roundtrip_conversion():
    """Test that converting to UTC and back preserves the original time."""
    original_tz = "Europe/Amsterdam"
    original_dt = datetime(2024, 1, 15, 14, 30)

    # Convert to UTC and back
    utc_dt = to_utc(original_dt, original_tz)
    back_dt = from_utc(utc_dt, original_tz)

    amsterdam_tz = ZoneInfo(original_tz)
    expected = datetime(2024, 1, 15, 14, 30, tzinfo=amsterdam_tz)

    assert back_dt.replace(tzinfo=None) == expected.replace(tzinfo=None)
    assert back_dt.hour == expected.hour
    assert back_dt.minute == expected.minute
