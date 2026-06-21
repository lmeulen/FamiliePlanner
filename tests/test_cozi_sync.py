"""Tests for /api/cozi endpoints."""

from datetime import date, datetime, timedelta
from unittest.mock import AsyncMock, patch

import pytest
from httpx import AsyncClient

from app.models.agenda import AgendaEvent, RecurrenceSeries
from app.models.family import FamilyMember
from app.models.meals import Meal
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
    with patch("app.routers.cozi.COZI_ICS_URL", ""):
        response = await client.get("/api/cozi/preview")
    assert response.status_code == 400



async def test_import_no_url_returns_400(client: AsyncClient):
    """Import should return 400 when no Cozi URL is configured."""
    with patch("app.routers.cozi.COZI_ICS_URL", ""):
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
            cozi_uid=None,   # no UID stored
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

    with _mock_fetch(ics_content=owned_ics), patch(
        "app.services.cozi_sync._load_family_members",
        new=AsyncMock(return_value=[FamilyMemberRecord(id=1, name="Alice"), FamilyMemberRecord(id=2, name="Bob")]),
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

    with _mock_fetch(ics_content=owned_ics), patch(
        "app.services.cozi_sync._load_family_members",
        new=AsyncMock(return_value=[FamilyMemberRecord(id=alice.id, name="Alice"), FamilyMemberRecord(id=bob.id, name="Bob")]),
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
            title="Oude titel",    # different from "Test afspraak" in ICS
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
        result = await db.execute(
            select(AgendaEvent).where(AgendaEvent.cozi_uid == "single-001@cozi.test")
        )
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
        result = await db.execute(
            select(RecurrenceSeries).where(RecurrenceSeries.cozi_uid == "series-001@cozi.test")
        )
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
        result = await db.execute(
            select(Meal).where(Meal.cozi_uid == "meal-001@cozi.test")
        )
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
            select(func.count()).select_from(AgendaEvent).where(
                AgendaEvent.cozi_uid == "single-001@cozi.test"
            )
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
