"""Tests for /api/agenda endpoints."""
import pytest
from httpx import AsyncClient


EVENT_BASE = {
    "title": "Vergadering",
    "description": "",
    "location": "",
    "start_time": "2026-06-01T10:00:00",
    "end_time": "2026-06-01T11:00:00",
    "all_day": False,
    "member_ids": [],
    "color": "#FF6B6B",
}

SERIES_BASE = {
    "title": "Dagelijkse standup",
    "description": "",
    "location": "",
    "start_time_of_day": "09:00:00",
    "end_time_of_day": "09:15:00",
    "all_day": False,
    "member_ids": [],
    "color": "#4ECDC4",
    "recurrence_type": "daily",
    "series_start": "2026-06-01",
    "series_end": "2026-06-07",
}


# ── Single events ─────────────────────────────────────────────────

async def test_list_events_empty(client: AsyncClient):
    r = await client.get("/api/agenda/")
    assert r.status_code == 200
    assert r.json() == []


async def test_create_event(client: AsyncClient):
    r = await client.post("/api/agenda/", json=EVENT_BASE)
    assert r.status_code == 201
    data = r.json()
    assert data["title"] == "Vergadering"
    assert "id" in data


async def test_create_event_title_required(client: AsyncClient):
    payload = {**EVENT_BASE, "title": ""}
    r = await client.post("/api/agenda/", json=payload)
    assert r.status_code == 422


async def test_get_event(client: AsyncClient):
    created = (await client.post("/api/agenda/", json=EVENT_BASE)).json()
    r = await client.get(f"/api/agenda/{created['id']}")
    assert r.status_code == 200
    assert r.json()["title"] == "Vergadering"


async def test_get_event_not_found(client: AsyncClient):
    r = await client.get("/api/agenda/9999")
    assert r.status_code == 404


async def test_update_event(client: AsyncClient):
    created = (await client.post("/api/agenda/", json=EVENT_BASE)).json()
    r = await client.put(f"/api/agenda/{created['id']}", json={**EVENT_BASE, "title": "Aangepast"})
    assert r.status_code == 200
    assert r.json()["title"] == "Aangepast"


async def test_update_event_not_found(client: AsyncClient):
    r = await client.put("/api/agenda/9999", json=EVENT_BASE)
    assert r.status_code == 404


async def test_delete_event(client: AsyncClient):
    created = (await client.post("/api/agenda/", json=EVENT_BASE)).json()
    r = await client.delete(f"/api/agenda/{created['id']}")
    assert r.status_code == 204
    assert (await client.get(f"/api/agenda/{created['id']}")).status_code == 404


async def test_delete_event_not_found(client: AsyncClient):
    r = await client.delete("/api/agenda/9999")
    assert r.status_code == 404


async def test_list_events_date_filter(client: AsyncClient):
    await client.post("/api/agenda/", json=EVENT_BASE)
    r = await client.get("/api/agenda/", params={"start": "2026-06-01", "end": "2026-06-01"})
    assert r.status_code == 200
    assert len(r.json()) == 1

    r2 = await client.get("/api/agenda/", params={"start": "2026-07-01", "end": "2026-07-31"})
    assert r2.json() == []


async def test_today_events_endpoint(client: AsyncClient):
    r = await client.get("/api/agenda/today")
    assert r.status_code == 200
    assert isinstance(r.json(), list)


async def test_week_events_endpoint(client: AsyncClient):
    r = await client.get("/api/agenda/week")
    assert r.status_code == 200
    assert isinstance(r.json(), list)


# ── Recurrence series ─────────────────────────────────────────────

async def test_create_series_generates_occurrences(client: AsyncClient):
    r = await client.post("/api/agenda/series", json=SERIES_BASE)
    assert r.status_code == 201
    series_id = r.json()["id"]
    # Daily from 2026-06-01 to 2026-06-07 = 7 events
    events = (await client.get("/api/agenda/", params={"start": "2026-06-01", "end": "2026-06-07"})).json()
    assert len(events) == 7
    assert all(e["series_id"] == series_id for e in events)


async def test_create_series_end_before_start_rejected(client: AsyncClient):
    bad = {**SERIES_BASE, "series_start": "2026-06-10", "series_end": "2026-06-01"}
    r = await client.post("/api/agenda/series", json=bad)
    assert r.status_code == 422


async def test_get_series(client: AsyncClient):
    created = (await client.post("/api/agenda/series", json=SERIES_BASE)).json()
    r = await client.get(f"/api/agenda/series/{created['id']}")
    assert r.status_code == 200
    assert r.json()["title"] == SERIES_BASE["title"]


async def test_get_series_not_found(client: AsyncClient):
    r = await client.get("/api/agenda/series/9999")
    assert r.status_code == 404


async def test_update_series_regenerates(client: AsyncClient):
    created = (await client.post("/api/agenda/series", json=SERIES_BASE)).json()
    series_id = created["id"]
    # Extend end date by 3 more days → 10 occurrences
    r = await client.put(f"/api/agenda/series/{series_id}", json={
        **SERIES_BASE,
        "series_end": "2026-06-10",
    })
    assert r.status_code == 200
    events = (await client.get("/api/agenda/", params={"start": "2026-06-01", "end": "2026-06-10"})).json()
    assert len(events) == 10


async def test_delete_series_removes_events(client: AsyncClient):
    created = (await client.post("/api/agenda/series", json=SERIES_BASE)).json()
    series_id = created["id"]
    r = await client.delete(f"/api/agenda/series/{series_id}")
    assert r.status_code == 204
    events = (await client.get("/api/agenda/", params={"start": "2026-06-01", "end": "2026-06-07"})).json()
    assert events == []


async def test_edit_single_event_marks_exception(client: AsyncClient):
    created_series = (await client.post("/api/agenda/series", json=SERIES_BASE)).json()
    series_id = created_series["id"]
    events = (await client.get("/api/agenda/", params={"start": "2026-06-01", "end": "2026-06-07"})).json()
    event_id = events[0]["id"]

    r = await client.put(f"/api/agenda/{event_id}", json={**EVENT_BASE, "title": "Exception event"})
    assert r.status_code == 200
    updated = r.json()
    assert updated["is_exception"] is True
    assert updated["series_id"] == series_id
