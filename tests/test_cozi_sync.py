"""Tests for /api/cozi endpoints."""

import asyncio
from datetime import date, datetime
from unittest.mock import AsyncMock, patch

import pytest
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker

from app.cozi_scheduler import run_cozi_sync_scheduler
from app.enums import RecurrenceType
from app.models.agenda import AgendaEvent, RecurrenceSeries
from app.models.family import FamilyMember
from app.models.google_sync import GoogleSyncQueue
from app.models.meals import Meal
from app.models.settings import AppSetting
from app.services.cozi_sync import run_automatic_cozi_sync
from app.services.google_sync import ENTITY_EVENT, ENTITY_SERIES, OP_DELETE, event_key, series_key
from tools.cozi_import_advisor import FamilyMemberRecord

TODAY = date.today()

# Minimal ICS fixture with three events: one single, one series, one meal
SAMPLE_ICS = f"""BEGIN:VCALENDAR
VERSION:2.0
PRODID:-//Cozi//Test//EN
BEGIN:VEVENT
UID:single-001@cozi.test
DTSTART:{TODAY.strftime('%Y%m%d')}T100000
DTEND:{TODAY.strftime('%Y%m%d')}T110000
SUMMARY:Test afspraak
DESCRIPTION:Beschrijving
LOCATION:Amsterdam
END:VEVENT
BEGIN:VEVENT
UID:series-001@cozi.test
DTSTART:{TODAY.strftime('%Y%m%d')}T090000
DTEND:{TODAY.strftime('%Y%m%d')}T100000
SUMMARY:Wekelijkse vergadering
RRULE:FREQ=WEEKLY;COUNT=4
END:VEVENT
BEGIN:VEVENT
UID:meal-001@cozi.test
DTSTART:{TODAY.strftime('%Y%m%d')}T180000
DTEND:{TODAY.strftime('%Y%m%d')}T200000
SUMMARY:Pasta carbonara
END:VEVENT
END:VCALENDAR
"""


def _mock_fetch(ics_content: str = SAMPLE_ICS):
    """Return an async patcher that returns the given ICS content."""
    return patch(
        "app.services.cozi_sync.fetch_ics",
        new=AsyncMock(return_value=ics_content),
    )


# ── Basic endpoint behaviour ──────────────────────────────────────


async def test_preview_no_url_returns_400(client: AsyncClient):
    """Preview should return 400 when no Cozi URL is configured."""
    with patch("app.config.COZI_ICS_URL", ""):
        response = await client.get("/api/cozi/preview")
    assert response.status_code == 400


async def test_import_no_url_returns_400(client: AsyncClient):
    """Import should return 400 when no Cozi URL is configured."""
    with patch("app.config.COZI_ICS_URL", ""):
        response = await client.post("/api/cozi/import", json={"selected_uids": ["uid-1"]})
    assert response.status_code == 400


async def test_import_empty_selection_returns_zeros(client: AsyncClient):
    """Importing an empty selection should return all-zero stats without touching the DB."""
    # Set a URL so the endpoint doesn't reject on missing config
    await client.put("/api/settings/", json={"cozi_url": "https://example.test/feed.ics"})
    response = await client.post("/api/cozi/import", json={"selected_uids": []})
    assert response.status_code == 200
    data = response.json()
    assert data["imported_events"] == 0
    assert data["imported_series"] == 0
    assert data["imported_meals"] == 0


# ── Preview classification ────────────────────────────────────────


async def test_preview_new_events(client: AsyncClient):
    """All events are classified as 'new' on a fresh database."""
    await client.put("/api/settings/", json={"cozi_url": "https://example.test/feed.ics"})
    with _mock_fetch():
        response = await client.get("/api/cozi/preview")
    assert response.status_code == 200
    items = response.json()
    assert len(items) == 3
    assert all(i["status"] == "new" for i in items)
    assert all(i["recommendation"] == "import" for i in items)


async def test_preview_uid_match_gives_exists(client: AsyncClient, db_engine):
    """An event whose UID is already stored in the DB should be classified 'exists'."""
    await client.put("/api/settings/", json={"cozi_url": "https://example.test/feed.ics"})

    # Pre-create a matching event with the known Cozi UID
    from sqlalchemy.ext.asyncio import async_sessionmaker

    Session = async_sessionmaker(db_engine, expire_on_commit=False)
    async with Session() as db:
        event = AgendaEvent(
            title="Test afspraak",
            description="Beschrijving",
            location="Amsterdam",
            start_time=datetime.combine(TODAY, datetime.strptime("10:00", "%H:%M").time()),
            end_time=datetime.combine(TODAY, datetime.strptime("11:00", "%H:%M").time()),
            all_day=False,
            cozi_uid="single-001@cozi.test",
        )
        db.add(event)
        await db.commit()

    with _mock_fetch():
        response = await client.get("/api/cozi/preview")
    assert response.status_code == 200
    items = response.json()
    single = next(i for i in items if i["uid"] == "single-001@cozi.test")
    assert single["status"] == "exists"
    assert single["recommendation"] == "skip"
    assert single["matched_fp_id"] is not None


async def test_preview_fuzzy_match_gives_likely_exists(client: AsyncClient, db_engine):
    """Event with matching title+date but no cozi_uid should be 'likely_exists'."""
    await client.put("/api/settings/", json={"cozi_url": "https://example.test/feed.ics"})

    from sqlalchemy.ext.asyncio import async_sessionmaker

    Session = async_sessionmaker(db_engine, expire_on_commit=False)
    async with Session() as db:
        event = AgendaEvent(
            title="Test afspraak",
            description="",
            location="Amsterdam",
            start_time=datetime.combine(TODAY, datetime.strptime("10:00", "%H:%M").time()),
            end_time=datetime.combine(TODAY, datetime.strptime("11:00", "%H:%M").time()),
            all_day=False,
            cozi_uid=None,  # no UID stored
        )
        db.add(event)
        await db.commit()

    with _mock_fetch():
        response = await client.get("/api/cozi/preview")
    assert response.status_code == 200
    items = response.json()
    single = next(i for i in items if i["uid"] == "single-001@cozi.test")
    assert single["status"] == "likely_exists"
    assert single["recommendation"] == "skip"


async def test_preview_fuzzy_match_prefers_same_owner(client: AsyncClient, db_engine):
    """When multiple same-day matches exist, Cozi owner should pick the matching FamiliePlanner owner."""
    await client.put("/api/settings/", json={"cozi_url": "https://example.test/feed.ics"})

    owned_ics = f"""BEGIN:VCALENDAR
VERSION:2.0
PRODID:-//Cozi//Test//EN
BEGIN:VEVENT
UID:single-001@cozi.test
DTSTART:{TODAY.strftime('%Y%m%d')}T100000
DTEND:{TODAY.strftime('%Y%m%d')}T110000
SUMMARY:Alice: Test afspraak
DESCRIPTION:Beschrijving
LOCATION:Amsterdam
END:VEVENT
END:VCALENDAR
"""

    from sqlalchemy.ext.asyncio import async_sessionmaker

    Session = async_sessionmaker(db_engine, expire_on_commit=False)
    async with Session() as db:
        alice = FamilyMember(name="Alice")
        bob = FamilyMember(name="Bob")
        alice_event = AgendaEvent(
            title="Test afspraak",
            description="",
            location="Amsterdam",
            start_time=datetime.combine(TODAY, datetime.strptime("11:00", "%H:%M").time()),
            end_time=datetime.combine(TODAY, datetime.strptime("12:00", "%H:%M").time()),
            all_day=False,
            cozi_uid=None,
            members=[alice],
        )
        bob_event = AgendaEvent(
            title="Test afspraak",
            description="",
            location="Amsterdam",
            start_time=datetime.combine(TODAY, datetime.strptime("10:00", "%H:%M").time()),
            end_time=datetime.combine(TODAY, datetime.strptime("11:00", "%H:%M").time()),
            all_day=False,
            cozi_uid=None,
            members=[bob],
        )
        db.add_all([alice, bob, alice_event, bob_event])
        await db.commit()
        await db.refresh(alice_event)
        await db.refresh(bob_event)

    with (
        _mock_fetch(ics_content=owned_ics),
        patch(
            "app.services.cozi_sync._load_family_members",
            new=AsyncMock(return_value=[FamilyMemberRecord(id=1, name="Alice"), FamilyMemberRecord(id=2, name="Bob")]),
        ),
    ):
        response = await client.get("/api/cozi/preview")

    assert response.status_code == 200
    items = response.json()
    single = next(i for i in items if i["uid"] == "single-001@cozi.test")
    assert single["status"] == "likely_exists"
    assert single["matched_fp_id"] == alice_event.id


async def test_preview_fuzzy_match_rejects_different_owner(client: AsyncClient, db_engine):
    """A same-day title match with a different owner should not be treated as likely existing."""
    await client.put("/api/settings/", json={"cozi_url": "https://example.test/feed.ics"})

    owned_ics = f"""BEGIN:VCALENDAR
VERSION:2.0
PRODID:-//Cozi//Test//EN
BEGIN:VEVENT
UID:single-001@cozi.test
DTSTART:{TODAY.strftime('%Y%m%d')}T100000
DTEND:{TODAY.strftime('%Y%m%d')}T110000
SUMMARY:Alice: Test afspraak
DESCRIPTION:Beschrijving
LOCATION:Amsterdam
END:VEVENT
END:VCALENDAR
"""

    from sqlalchemy.ext.asyncio import async_sessionmaker

    Session = async_sessionmaker(db_engine, expire_on_commit=False)
    async with Session() as db:
        alice = FamilyMember(name="Alice")
        bob = FamilyMember(name="Bob")
        bob_event = AgendaEvent(
            title="Test afspraak",
            description="",
            location="Amsterdam",
            start_time=datetime.combine(TODAY, datetime.strptime("10:00", "%H:%M").time()),
            end_time=datetime.combine(TODAY, datetime.strptime("11:00", "%H:%M").time()),
            all_day=False,
            cozi_uid=None,
            members=[bob],
        )
        db.add_all([alice, bob, bob_event])
        await db.commit()
        await db.refresh(alice)
        await db.refresh(bob)

    with (
        _mock_fetch(ics_content=owned_ics),
        patch(
            "app.services.cozi_sync._load_family_members",
            new=AsyncMock(
                return_value=[FamilyMemberRecord(id=alice.id, name="Alice"), FamilyMemberRecord(id=bob.id, name="Bob")]
            ),
        ),
    ):
        response = await client.get("/api/cozi/preview")

    assert response.status_code == 200
    items = response.json()
    single = next(i for i in items if i["uid"] == "single-001@cozi.test")
    assert single["status"] == "new"
    assert single["matched_fp_id"] is None


async def test_preview_uid_change_detected(client: AsyncClient, db_engine):
    """When the UID matches but the title differs, status should be 'changed'."""
    await client.put("/api/settings/", json={"cozi_url": "https://example.test/feed.ics"})

    from sqlalchemy.ext.asyncio import async_sessionmaker

    Session = async_sessionmaker(db_engine, expire_on_commit=False)
    async with Session() as db:
        event = AgendaEvent(
            title="Oude titel",  # different from "Test afspraak" in ICS
            description="",
            location="Amsterdam",
            start_time=datetime.combine(TODAY, datetime.strptime("10:00", "%H:%M").time()),
            end_time=datetime.combine(TODAY, datetime.strptime("11:00", "%H:%M").time()),
            all_day=False,
            cozi_uid="single-001@cozi.test",
        )
        db.add(event)
        await db.commit()

    with _mock_fetch():
        response = await client.get("/api/cozi/preview")
    assert response.status_code == 200
    items = response.json()
    single = next(i for i in items if i["uid"] == "single-001@cozi.test")
    assert single["status"] == "changed"
    assert single["recommendation"] == "import"
    assert any(c["field"] == "titel" for c in single["changes"])


async def test_preview_fuzzy_ignores_already_linked_other_uid(client: AsyncClient, db_engine):
    """Fuzzy matching should not reuse an event already linked to a different Cozi UID."""
    await client.put("/api/settings/", json={"cozi_url": "https://example.test/feed.ics"})

    from sqlalchemy.ext.asyncio import async_sessionmaker

    Session = async_sessionmaker(db_engine, expire_on_commit=False)
    async with Session() as db:
        event = AgendaEvent(
            title="Test afspraak",
            description="",
            location="Amsterdam",
            start_time=datetime.combine(TODAY, datetime.strptime("10:00", "%H:%M").time()),
            end_time=datetime.combine(TODAY, datetime.strptime("11:00", "%H:%M").time()),
            all_day=False,
            cozi_uid="different-cozi-uid@cozi.test",
        )
        db.add(event)
        await db.commit()

    with _mock_fetch():
        response = await client.get("/api/cozi/preview")
    assert response.status_code == 200
    items = response.json()
    single = next(i for i in items if i["uid"] == "single-001@cozi.test")
    assert single["status"] == "new"
    assert single["matched_fp_id"] is None


# ── Import ────────────────────────────────────────────────────────


async def test_import_creates_event_with_cozi_uid(client: AsyncClient, db_engine):
    """Importing a single event should create it in the DB with cozi_uid set."""
    await client.put("/api/settings/", json={"cozi_url": "https://example.test/feed.ics"})

    with _mock_fetch():
        response = await client.post(
            "/api/cozi/import",
            json={"selected_uids": ["single-001@cozi.test"]},
        )
    assert response.status_code == 200
    data = response.json()
    assert data["imported_events"] == 1

    # Verify event was created with cozi_uid
    from sqlalchemy import select
    from sqlalchemy.ext.asyncio import async_sessionmaker

    Session = async_sessionmaker(db_engine, expire_on_commit=False)
    async with Session() as db:
        result = await db.execute(select(AgendaEvent).where(AgendaEvent.cozi_uid == "single-001@cozi.test"))
        event = result.scalar_one_or_none()
    assert event is not None
    assert event.title == "Test afspraak"


async def test_import_creates_series(client: AsyncClient, db_engine):
    """Importing a recurring event should create a RecurrenceSeries."""
    await client.put("/api/settings/", json={"cozi_url": "https://example.test/feed.ics"})

    with _mock_fetch():
        response = await client.post(
            "/api/cozi/import",
            json={"selected_uids": ["series-001@cozi.test"]},
        )
    assert response.status_code == 200
    data = response.json()
    assert data["imported_series"] == 1

    from sqlalchemy import select
    from sqlalchemy.ext.asyncio import async_sessionmaker

    Session = async_sessionmaker(db_engine, expire_on_commit=False)
    async with Session() as db:
        result = await db.execute(select(RecurrenceSeries).where(RecurrenceSeries.cozi_uid == "series-001@cozi.test"))
        series = result.scalar_one_or_none()
    assert series is not None
    assert series.title == "Wekelijkse vergadering"


async def test_import_creates_meal(client: AsyncClient, db_engine):
    """Importing a 18:00-20:00 event should create a Meal record."""
    await client.put("/api/settings/", json={"cozi_url": "https://example.test/feed.ics"})

    with _mock_fetch():
        response = await client.post(
            "/api/cozi/import",
            json={"selected_uids": ["meal-001@cozi.test"]},
        )
    assert response.status_code == 200
    data = response.json()
    assert data["imported_meals"] == 1

    from sqlalchemy import select
    from sqlalchemy.ext.asyncio import async_sessionmaker

    Session = async_sessionmaker(db_engine, expire_on_commit=False)
    async with Session() as db:
        result = await db.execute(select(Meal).where(Meal.cozi_uid == "meal-001@cozi.test"))
        meal = result.scalar_one_or_none()
    assert meal is not None
    assert meal.name == "Pasta carbonara"


async def test_import_second_run_updates_event(client: AsyncClient, db_engine):
    """Second import of an event with same UID should update, not duplicate."""
    await client.put("/api/settings/", json={"cozi_url": "https://example.test/feed.ics"})

    with _mock_fetch():
        await client.post("/api/cozi/import", json={"selected_uids": ["single-001@cozi.test"]})

    # Import again
    with _mock_fetch():
        response = await client.post(
            "/api/cozi/import",
            json={"selected_uids": ["single-001@cozi.test"]},
        )
    assert response.status_code == 200
    data = response.json()
    # Should be an update, not a new import
    assert data["updated_events"] == 1
    assert data["imported_events"] == 0

    # Verify only one event exists with this UID
    from sqlalchemy import func, select
    from sqlalchemy.ext.asyncio import async_sessionmaker

    Session = async_sessionmaker(db_engine, expire_on_commit=False)
    async with Session() as db:
        result = await db.execute(
            select(func.count()).select_from(AgendaEvent).where(AgendaEvent.cozi_uid == "single-001@cozi.test")
        )
        count = result.scalar()
    assert count == 1


async def test_import_only_selected_uids(client: AsyncClient, db_engine):
    """Only events with UIDs in selected_uids should be imported."""
    await client.put("/api/settings/", json={"cozi_url": "https://example.test/feed.ics"})

    with _mock_fetch():
        response = await client.post(
            "/api/cozi/import",
            json={"selected_uids": ["meal-001@cozi.test"]},
        )
    assert response.status_code == 200
    data = response.json()
    assert data["imported_meals"] == 1
    assert data["imported_events"] == 0


async def test_link_recovers_from_stale_item_id(client: AsyncClient, db_engine):
    """Linking should still work when the UI sends a stale item_id but the Cozi UID can be reclassified."""
    await client.put("/api/settings/", json={"cozi_url": "https://example.test/feed.ics"})

    from sqlalchemy import select
    from sqlalchemy.ext.asyncio import async_sessionmaker

    Session = async_sessionmaker(db_engine, expire_on_commit=False)
    async with Session() as db:
        event = AgendaEvent(
            title="Test afspraak",
            description="",
            location="Amsterdam",
            start_time=datetime.combine(TODAY, datetime.strptime("10:00", "%H:%M").time()),
            end_time=datetime.combine(TODAY, datetime.strptime("11:00", "%H:%M").time()),
            all_day=False,
            cozi_uid=None,
        )
        db.add(event)
        await db.commit()
        await db.refresh(event)

    with _mock_fetch():
        response = await client.post(
            "/api/cozi/link",
            json={
                "cozi_uid": "single-001@cozi.test",
                "item_type": "event",
                "item_id": 999999,
            },
        )

    assert response.status_code == 200

    async with Session() as db:
        result = await db.execute(select(AgendaEvent).where(AgendaEvent.id == event.id))
        linked_event = result.scalar_one()

    assert linked_event.cozi_uid == "single-001@cozi.test"


async def test_automatic_sync_only_imports_safe_items(db_engine):
    """Automatic sync should import only new or changed items, not fuzzy likely matches."""
    custom_ics = f"""BEGIN:VCALENDAR
VERSION:2.0
PRODID:-//Cozi//Test//EN
BEGIN:VEVENT
UID:changed-001@cozi.test
DTSTART:{TODAY.strftime('%Y%m%d')}T100000
DTEND:{TODAY.strftime('%Y%m%d')}T110000
SUMMARY:Nieuwe titel
DESCRIPTION:Nieuwe beschrijving
LOCATION:Utrecht
END:VEVENT
BEGIN:VEVENT
UID:likely-001@cozi.test
DTSTART:{TODAY.strftime('%Y%m%d')}T120000
DTEND:{TODAY.strftime('%Y%m%d')}T130000
SUMMARY:Fuzzy afspraak
LOCATION:Rotterdam
END:VEVENT
BEGIN:VEVENT
UID:meal-automatic-001@cozi.test
DTSTART:{TODAY.strftime('%Y%m%d')}T180000
DTEND:{TODAY.strftime('%Y%m%d')}T200000
SUMMARY:Lasagna
END:VEVENT
END:VCALENDAR
"""

    Session = async_sessionmaker(db_engine, expire_on_commit=False)
    async with Session() as db:
        db.add_all(
            [
                AgendaEvent(
                    title="Oude titel",
                    description="",
                    location="Amsterdam",
                    start_time=datetime.combine(TODAY, datetime.strptime("10:00", "%H:%M").time()),
                    end_time=datetime.combine(TODAY, datetime.strptime("11:00", "%H:%M").time()),
                    all_day=False,
                    cozi_uid="changed-001@cozi.test",
                ),
                AgendaEvent(
                    title="Fuzzy afspraak",
                    description="",
                    location="Rotterdam",
                    start_time=datetime.combine(TODAY, datetime.strptime("12:00", "%H:%M").time()),
                    end_time=datetime.combine(TODAY, datetime.strptime("13:00", "%H:%M").time()),
                    all_day=False,
                    cozi_uid=None,
                ),
            ]
        )
        await db.commit()

    async with Session() as db:
        db.add(AppSetting(key="cozi_url", value="https://example.test/feed.ics"))
        await db.commit()

    with _mock_fetch(custom_ics):
        async with Session() as db:
            result = await run_automatic_cozi_sync(db)

    assert result.updated_events == 1
    assert result.imported_meals == 1
    assert result.imported_events == 0

    from sqlalchemy import func, select

    async with Session() as db:
        changed = await db.execute(select(AgendaEvent).where(AgendaEvent.cozi_uid == "changed-001@cozi.test"))
        changed_event = changed.scalar_one()
        fuzzy_count = await db.execute(
            select(func.count()).select_from(AgendaEvent).where(AgendaEvent.title == "Fuzzy afspraak")
        )
        fuzzy = await db.execute(select(AgendaEvent).where(AgendaEvent.title == "Fuzzy afspraak"))
        meal = await db.execute(select(Meal).where(Meal.cozi_uid == "meal-automatic-001@cozi.test"))

    assert changed_event.title == "Nieuwe titel"
    assert fuzzy_count.scalar() == 1
    assert fuzzy.scalar_one().cozi_uid is None
    assert meal.scalar_one().name == "Lasagna"


async def test_cozi_scheduler_runs_once_immediately_on_startup():
    """Scheduler should execute one sync cycle immediately when started."""
    stop_event = asyncio.Event()
    calls = []

    async def fake_execute() -> None:
        calls.append("called")
        stop_event.set()

    with patch("app.cozi_scheduler._execute_automatic_cozi_sync", new=fake_execute):
        await run_cozi_sync_scheduler(stop_event)

    assert calls == ["called"]


async def test_automatic_sync_removes_missing_cozi_records_and_queues_google_deletions(db_engine):
    """A valid empty Cozi feed is authoritative for records linked by Cozi UID."""
    Session = async_sessionmaker(db_engine, expire_on_commit=False)

    async with Session() as db:
        series = RecurrenceSeries(
            title="Cozi reeks",
            recurrence_type=RecurrenceType.weekly,
            series_start=TODAY,
            series_end=TODAY,
            start_time_of_day=datetime.strptime("09:00", "%H:%M").time(),
            end_time_of_day=datetime.strptime("10:00", "%H:%M").time(),
            cozi_uid="removed-series@cozi.test",
        )
        db.add_all(
            [
                AgendaEvent(
                    title="Cozi afspraak",
                    start_time=datetime.combine(TODAY, datetime.strptime("10:00", "%H:%M").time()),
                    end_time=datetime.combine(TODAY, datetime.strptime("11:00", "%H:%M").time()),
                    all_day=False,
                    cozi_uid="removed-event@cozi.test",
                ),
                AgendaEvent(
                    title="Lokale afspraak",
                    start_time=datetime.combine(TODAY, datetime.strptime("12:00", "%H:%M").time()),
                    end_time=datetime.combine(TODAY, datetime.strptime("13:00", "%H:%M").time()),
                    all_day=False,
                ),
                Meal(
                    date=TODAY,
                    name="Cozi maaltijd",
                    cozi_uid="removed-meal@cozi.test",
                ),
                series,
                AppSetting(key="cozi_url", value="https://example.test/feed.ics"),
            ]
        )
        await db.flush()
        db.add_all(
            [
                AgendaEvent(
                    title="Normale reeksafspraak",
                    start_time=datetime.combine(TODAY, datetime.strptime("09:00", "%H:%M").time()),
                    end_time=datetime.combine(TODAY, datetime.strptime("10:00", "%H:%M").time()),
                    all_day=False,
                    series_id=series.id,
                ),
                AgendaEvent(
                    title="Lokale reeksuitzondering",
                    start_time=datetime.combine(TODAY, datetime.strptime("11:00", "%H:%M").time()),
                    end_time=datetime.combine(TODAY, datetime.strptime("12:00", "%H:%M").time()),
                    all_day=False,
                    series_id=series.id,
                    is_exception=True,
                ),
            ]
        )
        await db.commit()
        event_id = (
            await db.execute(select(AgendaEvent.id).where(AgendaEvent.cozi_uid == "removed-event@cozi.test"))
        ).scalar_one()
        series_id = series.id

    with _mock_fetch("BEGIN:VCALENDAR\nVERSION:2.0\nEND:VCALENDAR\n"):
        async with Session() as db:
            result = await run_automatic_cozi_sync(db)

    assert (result.deleted_events, result.deleted_series, result.deleted_meals) == (1, 1, 1)

    async with Session() as db:
        remaining_events = (await db.execute(select(AgendaEvent))).scalars().all()
        remaining_meals = (await db.execute(select(Meal))).scalars().all()
        remaining_series = (await db.execute(select(RecurrenceSeries))).scalars().all()
        jobs = (await db.execute(select(GoogleSyncQueue))).scalars().all()

    assert [event.title for event in remaining_events] == ["Lokale afspraak"]
    assert remaining_meals == []
    assert remaining_series == []
    assert {(job.entity_type, job.entity_key, job.operation) for job in jobs} == {
        (ENTITY_EVENT, event_key(event_id), OP_DELETE),
        (ENTITY_SERIES, series_key(series_id), OP_DELETE),
    }


async def test_automatic_sync_fetch_failure_preserves_cozi_linked_records(db_engine):
    """A failed feed retrieval must not be mistaken for an authoritative empty feed."""
    Session = async_sessionmaker(db_engine, expire_on_commit=False)

    async with Session() as db:
        db.add_all(
            [
                AgendaEvent(
                    title="Cozi afspraak",
                    start_time=datetime.combine(TODAY, datetime.strptime("10:00", "%H:%M").time()),
                    end_time=datetime.combine(TODAY, datetime.strptime("11:00", "%H:%M").time()),
                    all_day=False,
                    cozi_uid="still-present@cozi.test",
                ),
                AppSetting(key="cozi_url", value="https://example.test/feed.ics"),
            ]
        )
        await db.commit()

    with patch("app.services.cozi_sync.fetch_ics", new=AsyncMock(side_effect=RuntimeError("feed unavailable"))):
        async with Session() as db:
            with pytest.raises(RuntimeError, match="feed unavailable"):
                await run_automatic_cozi_sync(db)

    async with Session() as db:
        events = (await db.execute(select(AgendaEvent))).scalars().all()
        jobs = (await db.execute(select(GoogleSyncQueue))).scalars().all()

    assert len(events) == 1
    assert jobs == []
