"""Tests for the one-way Google Calendar sync (no network access)."""

from datetime import date, datetime, time

import pytest
from sqlalchemy import select

from app.enums import RecurrenceType
from app.models.agenda import AgendaEvent, RecurrenceSeries
from app.models.family import FamilyMember
from app.models.google_sync import GoogleSyncLink, GoogleSyncQueue
from app.models.settings import AppSetting
from app.services import google_sync
from app.services.google_calendar import GoogleCalendarError
from app.services.google_sync import (
    ENTITY_EVENT,
    OP_DELETE,
    OP_UPSERT,
    GoogleSyncConfig,
    build_event_payload,
    build_series_payload,
    content_hash,
    enqueue,
    event_key,
    instance_key,
    process_queue,
    purge_calendar,
    series_key,
)
from app.utils.google_colors import (
    GOOGLE_EVENT_COLORS,
    assign_member_colors,
    nearest_color_id,
)
from app.utils.recurrence import build_rrule_string
from app.utils.timezone import UTC, to_aware

CONFIG = GoogleSyncConfig(
    enabled=True,
    calendar_id="fam@group.calendar.google.com",
    member_colors={"1": "11", "3": "7"},
    title_avatars=True,
    timezone="Europe/Amsterdam",
    app_base_url="https://planner.local",
)


def _member(member_id: int, name: str, color: str, avatar: str) -> FamilyMember:
    return FamilyMember(id=member_id, name=name, color=color, avatar=avatar)


def _event(**kwargs) -> AgendaEvent:
    defaults = {
        "id": 412,
        "title": "Voetbaltraining",
        "description": "Meenemen: scheenbeschermers",
        "location": "Sportpark",
        "start_time": datetime(2026, 8, 25, 18, 30),
        "end_time": datetime(2026, 8, 25, 20, 0),
        "all_day": False,
        "series_id": None,
        "is_exception": False,
    }
    defaults.update(kwargs)
    event = AgendaEvent(**defaults)
    event.members = kwargs.get("members", [])
    return event


# ── Colour mapping ──────────────────────────────────────────────────────────


def test_nearest_color_id_picks_perceptually_closest():
    assert nearest_color_id("#d50000") == "11"  # Tomato, exact match
    assert nearest_color_id("#039be5") == "7"  # Peacock, exact match


def test_nearest_color_id_respects_exclusions():
    assert nearest_color_id("#d50000", exclude={"11"}) != "11"


def test_assign_member_colors_is_distinct_and_stable():
    members = [(1, "#FF6B6B"), (2, "#4ECDC4"), (3, "#FFE66D"), (4, "#6C5CE7")]

    first = assign_member_colors(members)
    second = assign_member_colors(members)

    assert first == second  # deterministic
    assert len(set(first.values())) == len(members)  # no duplicates
    assert all(cid in GOOGLE_EVENT_COLORS for cid in first.values())


def test_assign_member_colors_handles_more_than_eleven_members():
    members = [(i, "#FF6B6B") for i in range(1, 15)]
    mapping = assign_member_colors(members)
    assert len(mapping) == 14


# ── Payload building ────────────────────────────────────────────────────────


def test_timed_event_uses_wall_clock_plus_tzid():
    """Stored naive values are app-local; they must not be UTC-shifted."""
    payload = build_event_payload(_event(), CONFIG)

    assert payload["start"] == {"dateTime": "2026-08-25T18:30:00", "timeZone": "Europe/Amsterdam"}
    assert payload["end"] == {"dateTime": "2026-08-25T20:00:00", "timeZone": "Europe/Amsterdam"}


def test_all_day_event_end_date_is_exclusive():
    payload = build_event_payload(
        _event(all_day=True, start_time=datetime(2026, 8, 25, 0, 0), end_time=datetime(2026, 8, 25, 23, 59, 59)),
        CONFIG,
    )

    assert payload["start"] == {"date": "2026-08-25"}
    assert payload["end"] == {"date": "2026-08-26"}


def test_event_carries_fp_id_in_extended_properties_and_description():
    payload = build_event_payload(_event(), CONFIG)

    assert payload["extendedProperties"]["private"]["fp_id"] == "event:412"
    assert payload["extendedProperties"]["private"]["fp_type"] == "event"
    assert payload["extendedProperties"]["private"]["fp_managed"] == "1"
    assert "fp-id: event:412" in payload["description"]


def test_description_contains_deep_link_and_member_names():
    members = [_member(1, "Sam", "#FF6B6B", "👦"), _member(3, "Noor", "#039be5", "🧒")]
    payload = build_event_payload(_event(members=members), CONFIG)

    assert "https://planner.local/agenda?event=412" in payload["description"]
    assert "FamiliePlanner · Sam, Noor" in payload["description"]


def test_multi_member_event_uses_primary_member_color_and_avatar_prefix():
    members = [_member(3, "Noor", "#039be5", "🧒"), _member(1, "Sam", "#FF6B6B", "👦")]
    payload = build_event_payload(_event(members=members), CONFIG)

    # Primary member = lowest id (Sam, colorId 11)
    assert payload["colorId"] == "11"
    assert payload["summary"] == "👦🧒 Voetbaltraining"


def test_event_without_members_uses_default_color():
    payload = build_event_payload(_event(), CONFIG)

    assert payload["colorId"] == "8"
    assert payload["summary"] == "Voetbaltraining"


def test_avatar_prefix_can_be_disabled():
    config = GoogleSyncConfig(**{**CONFIG.__dict__, "title_avatars": False})
    members = [_member(1, "Sam", "#FF6B6B", "👦")]
    payload = build_event_payload(_event(members=members), config)

    assert payload["summary"] == "Voetbaltraining"


def test_event_is_transparent_and_silent():
    payload = build_event_payload(_event(), CONFIG)

    assert payload["transparency"] == "transparent"
    assert payload["reminders"] == {"useDefault": False, "overrides": []}
    assert payload["guestsCanModify"] is False


# ── Hashing ─────────────────────────────────────────────────────────────────


def test_content_hash_is_stable_and_change_sensitive():
    a = build_event_payload(_event(), CONFIG)
    b = build_event_payload(_event(), CONFIG)
    c = build_event_payload(_event(title="Andere titel"), CONFIG)

    assert content_hash(a) == content_hash(b)
    assert content_hash(a) != content_hash(c)


# ── RRULE ───────────────────────────────────────────────────────────────────


@pytest.mark.parametrize(
    ("recurrence_type", "expected"),
    [
        (RecurrenceType.daily, "RRULE:FREQ=DAILY"),
        (RecurrenceType.every_other_day, "RRULE:FREQ=DAILY;INTERVAL=2"),
        (RecurrenceType.weekly, "RRULE:FREQ=WEEKLY"),
        (RecurrenceType.biweekly, "RRULE:FREQ=WEEKLY;INTERVAL=2"),
        (RecurrenceType.weekdays, "RRULE:FREQ=WEEKLY;BYDAY=MO,TU,WE,TH,FR"),
        (RecurrenceType.monthly, "RRULE:FREQ=MONTHLY"),
        (RecurrenceType.yearly, "RRULE:FREQ=YEARLY"),
    ],
)
def test_rrule_for_each_recurrence_type(recurrence_type, expected):
    assert build_rrule_string(recurrence_type) == expected


def test_rrule_interval_and_monthly_pattern():
    assert build_rrule_string(RecurrenceType.weekly, interval=3) == "RRULE:FREQ=WEEKLY;INTERVAL=3"
    assert (
        build_rrule_string(RecurrenceType.monthly, monthly_pattern="second_tuesday") == "RRULE:FREQ=MONTHLY;BYDAY=2TU"
    )
    assert build_rrule_string(RecurrenceType.monthly, monthly_pattern="last_friday") == "RRULE:FREQ=MONTHLY;BYDAY=-1FR"


def test_rrule_end_conditions():
    assert build_rrule_string(RecurrenceType.weekly, count=10) == "RRULE:FREQ=WEEKLY;COUNT=10"

    until = to_aware(datetime(2026, 12, 31, 23, 59, 59)).astimezone(UTC)
    assert build_rrule_string(RecurrenceType.weekly, until_utc=until).endswith("UNTIL=20261231T225959Z")

    # Infinite series must omit both.
    infinite = build_rrule_string(RecurrenceType.weekly)
    assert "COUNT" not in infinite and "UNTIL" not in infinite


def test_series_payload_uses_single_recurring_event():
    series = RecurrenceSeries(
        id=7,
        title="Voetbaltraining",
        description="",
        location="Sportpark",
        all_day=False,
        recurrence_type=RecurrenceType.weekly,
        series_start=date(2026, 8, 25),
        series_end=None,
        start_time_of_day=time(18, 30),
        end_time_of_day=time(20, 0),
        interval=1,
        count=None,
    )
    series.members = []
    base = _event(series_id=7)

    payload = build_series_payload(series, base, CONFIG)

    assert payload["recurrence"] == ["RRULE:FREQ=WEEKLY"]
    assert payload["extendedProperties"]["private"]["fp_id"] == "series:7"
    assert payload["start"]["dateTime"] == "2026-08-25T18:30:00"


# ── Entity keys ─────────────────────────────────────────────────────────────


def test_entity_keys_are_stable_natural_keys():
    assert event_key(412) == "event:412"
    assert series_key(7) == "series:7"
    # Keyed by date so it survives series regeneration wiping occurrence row ids.
    assert instance_key(7, date(2026, 8, 25)) == "series:7:2026-08-25"


# ── Queue ───────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_enqueue_collapses_repeated_edits(db_engine):
    from sqlalchemy.ext.asyncio import async_sessionmaker

    session_factory = async_sessionmaker(db_engine, expire_on_commit=False)
    async with session_factory() as db:
        await enqueue(db, ENTITY_EVENT, event_key(1), OP_UPSERT)
        await enqueue(db, ENTITY_EVENT, event_key(1), OP_UPSERT)
        await enqueue(db, ENTITY_EVENT, event_key(1), OP_DELETE)
        await db.commit()

        rows = (await db.execute(select(GoogleSyncQueue))).scalars().all()

    assert len(rows) == 1
    assert rows[0].operation == OP_DELETE


@pytest.mark.asyncio
async def test_process_queue_is_noop_when_disabled(db_engine):
    from sqlalchemy.ext.asyncio import async_sessionmaker

    session_factory = async_sessionmaker(db_engine, expire_on_commit=False)
    async with session_factory() as db:
        await enqueue(db, ENTITY_EVENT, event_key(1), OP_UPSERT)
        await db.commit()

        result = await process_queue(db)

    assert result.processed == 0


class FakeClient:
    """Records calls instead of hitting Google."""

    def __init__(self):
        self.inserted: list[dict] = []
        self.patched: list[tuple[str, dict]] = []
        self.deleted: list[str] = []
        self._next_id = 0

    async def insert(self, body):
        self._next_id += 1
        self.inserted.append(body)
        return {"id": f"g{self._next_id}"}

    async def patch(self, event_id, body):
        self.patched.append((event_id, body))
        return {"id": event_id}

    async def delete(self, event_id):
        self.deleted.append(event_id)
        return True

    async def instances(self, event_id, time_min, time_max):
        return [{"id": f"{event_id}_inst"}]

    async def list_synced(self, fp_type=None):
        return []

    async def list_all_events(self):
        return [{"id": "g1"}, {"id": "g2"}]


async def _enable_sync(db):
    db.add(AppSetting(key="google_sync_enabled", value="true"))
    db.add(AppSetting(key="google_calendar_id", value="fam@group.calendar.google.com"))
    await db.commit()


@pytest.mark.asyncio
async def test_process_queue_creates_then_skips_unchanged(db_engine, monkeypatch):
    from sqlalchemy.ext.asyncio import async_sessionmaker

    monkeypatch.setattr(google_sync, "credentials_available", lambda: True)

    session_factory = async_sessionmaker(db_engine, expire_on_commit=False)
    client = FakeClient()

    async with session_factory() as db:
        await _enable_sync(db)
        db.add(_event(id=1))
        await db.commit()

        await enqueue(db, ENTITY_EVENT, event_key(1), OP_UPSERT)
        await db.commit()

        first = await process_queue(db, client)
        assert first.created == 1
        assert len(client.inserted) == 1

        link = (await db.execute(select(GoogleSyncLink))).scalar_one()
        assert link.google_event_id == "g1"
        assert link.entity_key == "event:1"

        # Re-queueing without changes must not call the API again.
        await enqueue(db, ENTITY_EVENT, event_key(1), OP_UPSERT)
        await db.commit()
        second = await process_queue(db, client)

    assert second.unchanged == 1
    assert len(client.inserted) == 1
    assert client.patched == []


@pytest.mark.asyncio
async def test_process_queue_patches_changed_event(db_engine, monkeypatch):
    from sqlalchemy.ext.asyncio import async_sessionmaker

    monkeypatch.setattr(google_sync, "credentials_available", lambda: True)

    session_factory = async_sessionmaker(db_engine, expire_on_commit=False)
    client = FakeClient()

    async with session_factory() as db:
        await _enable_sync(db)
        event = _event(id=1)
        db.add(event)
        await db.commit()

        await enqueue(db, ENTITY_EVENT, event_key(1), OP_UPSERT)
        await db.commit()
        await process_queue(db, client)

        event.title = "Nieuwe titel"
        await db.commit()
        await enqueue(db, ENTITY_EVENT, event_key(1), OP_UPSERT)
        await db.commit()
        result = await process_queue(db, client)

    assert result.updated == 1
    assert client.patched[0][0] == "g1"
    assert client.patched[0][1]["summary"] == "Nieuwe titel"


@pytest.mark.asyncio
async def test_process_queue_deletes_and_drops_link(db_engine, monkeypatch):
    from sqlalchemy.ext.asyncio import async_sessionmaker

    monkeypatch.setattr(google_sync, "credentials_available", lambda: True)

    session_factory = async_sessionmaker(db_engine, expire_on_commit=False)
    client = FakeClient()

    async with session_factory() as db:
        await _enable_sync(db)
        db.add(_event(id=1))
        await db.commit()

        await enqueue(db, ENTITY_EVENT, event_key(1), OP_UPSERT)
        await db.commit()
        await process_queue(db, client)

        await enqueue(db, ENTITY_EVENT, event_key(1), OP_DELETE)
        await db.commit()
        result = await process_queue(db, client)

        links = (await db.execute(select(GoogleSyncLink))).scalars().all()

    assert result.deleted == 1
    assert client.deleted == ["g1"]
    assert links == []


@pytest.mark.asyncio
async def test_failed_job_is_retried_with_backoff(db_engine, monkeypatch):
    from sqlalchemy.ext.asyncio import async_sessionmaker

    monkeypatch.setattr(google_sync, "credentials_available", lambda: True)

    class BrokenClient(FakeClient):
        async def insert(self, body):
            raise RuntimeError("boom")

    session_factory = async_sessionmaker(db_engine, expire_on_commit=False)

    async with session_factory() as db:
        await _enable_sync(db)
        db.add(_event(id=1))
        await db.commit()

        await enqueue(db, ENTITY_EVENT, event_key(1), OP_UPSERT)
        await db.commit()

        result = await process_queue(db, BrokenClient())
        job = (await db.execute(select(GoogleSyncQueue))).scalar_one()

    assert result.failed == 1
    assert job.attempts == 1
    assert job.next_attempt_at is not None
    assert "boom" in job.last_error


# ── Router integration ──────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_creating_event_queues_a_push(client):
    payload = {
        "title": "Yoga",
        "start_time": "2026-08-25T19:00:00",
        "end_time": "2026-08-25T20:00:00",
        "all_day": False,
        "member_ids": [],
    }
    created = (await client.post("/api/agenda/", json=payload)).json()

    status = (await client.get("/api/google/status")).json()
    assert status["pending_jobs"] == 1
    assert status["enabled"] is False  # queued but not pushed while disabled

    await client.delete(f"/api/agenda/{created['id']}")
    status = (await client.get("/api/google/status")).json()
    assert status["pending_jobs"] == 1  # collapsed into a single delete job


@pytest.mark.asyncio
async def test_series_create_queues_one_job_not_per_occurrence(client):
    payload = {
        "title": "Wekelijkse training",
        "description": "",
        "location": "",
        "all_day": False,
        "recurrence_type": "weekly",
        "series_start": "2026-08-25",
        "series_end": "2026-12-31",
        "start_time_of_day": "18:30:00",
        "end_time_of_day": "20:00:00",
        "interval": 1,
        "member_ids": [],
    }
    r = await client.post("/api/agenda/series", json=payload)
    assert r.status_code == 201

    status = (await client.get("/api/google/status")).json()
    assert status["pending_jobs"] == 1


@pytest.mark.asyncio
async def test_status_endpoint_reports_not_configured(client):
    status = (await client.get("/api/google/status")).json()

    assert status["enabled"] is False
    assert status["configured"] is False
    assert status["usable"] is False


@pytest.mark.asyncio
async def test_colors_endpoint_returns_palette(client):
    await client.post("/api/family/", json={"name": "Sam", "color": "#FF6B6B", "avatar": "👦"})

    data = (await client.get("/api/google/colors")).json()

    assert len(data["palette"]) == 11
    assert data["members"]


@pytest.mark.asyncio
async def test_sync_rejected_when_not_configured(client):
    r = await client.post("/api/google/sync")
    assert r.status_code == 400


@pytest.mark.asyncio
async def test_purge_returns_gateway_error_when_google_is_unreachable(client, monkeypatch):
    async def failed_purge(_db):
        raise GoogleCalendarError("Google Calendar is tijdelijk niet bereikbaar.")

    monkeypatch.setattr("app.routers.google_sync.purge_calendar", failed_purge)

    response = await client.delete("/api/google/events")

    assert response.status_code == 502
    assert response.json()["details"] == "Google Calendar is tijdelijk niet bereikbaar."


@pytest.mark.asyncio
async def test_purge_calendar_works_while_sync_disabled_and_clears_old_jobs(db_engine, monkeypatch):
    from sqlalchemy.ext.asyncio import async_sessionmaker

    monkeypatch.setattr(google_sync, "credentials_available", lambda: True)

    session_factory = async_sessionmaker(db_engine, expire_on_commit=False)
    client = FakeClient()

    async with session_factory() as db:
        await _enable_sync(db)
        enabled = await db.get(AppSetting, "google_sync_enabled")
        enabled.value = "false"
        db.add(_event(id=1))
        await db.commit()

        await enqueue(db, ENTITY_EVENT, event_key(1), OP_UPSERT)
        await db.commit()

        removed = await purge_calendar(db, client)

        assert removed == 2
        assert client.deleted == ["g1", "g2"]

        queue_rows = (await db.execute(select(GoogleSyncQueue))).scalars().all()
        assert queue_rows == []

        link_rows = (await db.execute(select(GoogleSyncLink))).scalars().all()
        assert link_rows == []

        marker = (await db.get(AppSetting, "google_sync_last_purge_at"))
        assert marker is not None and marker.value

        old_jobs = await process_queue(db, client)
        assert old_jobs.processed == 0
