"""Boundary tests for the wall-clock storage policy.

Storage policy: naive datetimes in the database are wall-clock time in the app
timezone. Conversion happens only at ICS import/export boundaries.
"""

from datetime import date, datetime

import pytest
from icalendar import Calendar

from app.utils.timezone import (
    app_timezone_name,
    now_local,
    set_app_timezone,
    to_aware,
    to_local_naive,
    today_local,
)
from tools.cozi_import_advisor import _detect_meal_candidate, _extract_start_end
from tools.cozi_importer import _to_naive


@pytest.fixture(autouse=True)
def amsterdam_tz():
    original = app_timezone_name()
    set_app_timezone("Europe/Amsterdam")
    yield
    set_app_timezone(original)


def _vevent(ics_body: str):
    ics = (
        "BEGIN:VCALENDAR\nVERSION:2.0\nPRODID:-//Test//EN\n"
        f"BEGIN:VEVENT\nUID:tz-test@example\n{ics_body}\nEND:VEVENT\nEND:VCALENDAR\n"
    )
    cal = Calendar.from_ical(ics)
    return next(c for c in cal.walk() if c.name == "VEVENT")


# ── Wall-clock helpers ──────────────────────────────────────────────────────


def test_to_local_naive_leaves_naive_input_untouched():
    """Floating iCalendar times are already wall-clock local."""
    dt = datetime(2026, 8, 25, 18, 30)
    assert to_local_naive(dt) == dt


def test_to_local_naive_converts_utc_to_local():
    aware = datetime(2026, 8, 25, 16, 30, tzinfo=__import__("zoneinfo").ZoneInfo("UTC"))
    assert to_local_naive(aware) == datetime(2026, 8, 25, 18, 30)


def test_to_aware_attaches_app_timezone():
    result = to_aware(datetime(2026, 8, 25, 18, 30))
    assert result.tzinfo is not None
    assert result.utcoffset().total_seconds() == 2 * 3600  # CEST


def test_now_local_and_today_local_agree():
    assert now_local().date() == today_local()


# ── Cozi import ─────────────────────────────────────────────────────────────


def test_cozi_utc_event_is_converted_to_local():
    """The core bug: 16:30Z is an 18:30 Amsterdam appointment, not 16:30."""
    event = _vevent("DTSTART:20260825T163000Z\nDTEND:20260825T173000Z\nSUMMARY:Voetbal")
    start, end, all_day = _extract_start_end(event)

    assert all_day is False
    assert _to_naive(start) == datetime(2026, 8, 25, 18, 30)
    assert _to_naive(end) == datetime(2026, 8, 25, 19, 30)


def test_cozi_floating_event_is_unchanged():
    """Guarantees the existing Cozi test suite keeps passing."""
    event = _vevent("DTSTART:20260825T183000\nDTEND:20260825T193000\nSUMMARY:Voetbal")
    start, end, _ = _extract_start_end(event)

    assert _to_naive(start) == datetime(2026, 8, 25, 18, 30)
    assert _to_naive(end) == datetime(2026, 8, 25, 19, 30)


def test_cozi_foreign_tzid_is_converted():
    event = _vevent("DTSTART;TZID=America/New_York:20260825T120000\nDTEND;TZID=America/New_York:20260825T130000")
    start, _, _ = _extract_start_end(event)

    # 12:00 EDT = 16:00 UTC = 18:00 CEST
    assert _to_naive(start) == datetime(2026, 8, 25, 18, 0)


def test_cozi_all_day_date_is_not_shifted():
    """VALUE=DATE has no timezone; converting it would move the event a day."""
    event = _vevent("DTSTART;VALUE=DATE:20260825\nDTEND;VALUE=DATE:20260826\nSUMMARY:Vrije dag")
    start, _, all_day = _extract_start_end(event)

    assert all_day is True
    assert _to_naive(start) == datetime(2026, 8, 25, 0, 0)


def test_cozi_winter_event_uses_cet_offset():
    """January is CET (+1), not CEST (+2)."""
    event = _vevent("DTSTART:20260115T173000Z\nDTEND:20260115T183000Z")
    start, _, _ = _extract_start_end(event)

    assert _to_naive(start) == datetime(2026, 1, 15, 18, 30)


def test_meal_detection_survives_utc_feed():
    """An 18:00-20:00 local dinner arrives as 16:00-18:00Z and must still match."""
    event = _vevent("DTSTART:20260825T160000Z\nDTEND:20260825T180000Z\nSUMMARY:Pasta")
    is_meal, reason, start, _ = _detect_meal_candidate(event, "Pasta")

    assert is_meal is True, reason
    assert start == datetime(2026, 8, 25, 18, 0)


def test_meal_detection_rejects_non_dinner_slot():
    event = _vevent("DTSTART:20260825T080000Z\nDTEND:20260825T090000Z\nSUMMARY:Ontbijt")
    is_meal, _, _, _ = _detect_meal_candidate(event, "Ontbijt")

    assert is_meal is False


# ── ICS export ──────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_export_uses_tzid_and_vtimezone(client):
    payload = {
        "title": "Voetbaltraining",
        "start_time": "2026-08-25T18:30:00",
        "end_time": "2026-08-25T20:00:00",
        "all_day": False,
        "member_ids": [],
    }
    created = (await client.post("/api/agenda/", json=payload)).json()

    resp = await client.get(f"/api/agenda/{created['id']}/export")
    assert resp.status_code == 200

    cal = Calendar.from_ical(resp.content)
    assert any(c.name == "VTIMEZONE" for c in cal.walk())

    vevent = next(c for c in cal.walk() if c.name == "VEVENT")
    assert vevent["DTSTART"].params["TZID"] == "Europe/Amsterdam"
    # Wall-clock time must survive the round trip unchanged
    assert vevent.decoded("DTSTART").replace(tzinfo=None) == datetime(2026, 8, 25, 18, 30)
    assert vevent.decoded("DTSTAMP").tzinfo is not None


@pytest.mark.asyncio
async def test_export_all_day_end_date_is_exclusive(client):
    payload = {
        "title": "Vrije dag",
        "start_time": "2026-08-25T00:00:00",
        "end_time": "2026-08-25T23:59:59",
        "all_day": True,
        "member_ids": [],
    }
    created = (await client.post("/api/agenda/", json=payload)).json()

    resp = await client.get(f"/api/agenda/{created['id']}/export")
    cal = Calendar.from_ical(resp.content)
    vevent = next(c for c in cal.walk() if c.name == "VEVENT")

    assert vevent.decoded("DTSTART") == date(2026, 8, 25)
    assert vevent.decoded("DTEND") == date(2026, 8, 26)


@pytest.mark.asyncio
async def test_subscription_declares_app_timezone(client):
    resp = await client.get("/api/agenda/export/calendar.ics")
    assert resp.status_code == 200

    cal = Calendar.from_ical(resp.content)
    assert str(cal.get("X-WR-TIMEZONE")) == "Europe/Amsterdam"


# ── API round trip ──────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_event_time_round_trips_unchanged(client):
    """No hidden UTC conversion may happen between POST and GET."""
    payload = {
        "title": "Yoga",
        "start_time": "2026-08-25T19:00:00",
        "end_time": "2026-08-25T20:00:00",
        "all_day": False,
        "member_ids": [],
    }
    created = (await client.post("/api/agenda/", json=payload)).json()

    fetched = (await client.get(f"/api/agenda/{created['id']}")).json()
    assert fetched["start_time"].startswith("2026-08-25T19:00:00")
    assert fetched["end_time"].startswith("2026-08-25T20:00:00")
