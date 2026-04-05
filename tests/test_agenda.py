"""Tests for /api/agenda endpoints."""

from httpx import AsyncClient

EVENT_BASE = {
    "title": "Vergadering",
    "description": "",
    "location": "",
    "start_time": "2026-06-01T10:00:00",
    "end_time": "2026-06-01T11:00:00",
    "all_day": False,
    "member_ids": [],
}

SERIES_BASE = {
    "title": "Dagelijkse standup",
    "description": "",
    "location": "",
    "start_time_of_day": "09:00:00",
    "end_time_of_day": "09:15:00",
    "all_day": False,
    "member_ids": [],
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
    r = await client.put(
        f"/api/agenda/series/{series_id}",
        json={
            **SERIES_BASE,
            "series_end": "2026-06-10",
        },
    )
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


# ── Extended recurrence pattern tests ────────────────────────────────────


async def test_custom_interval_every_3_days(client: AsyncClient):
    """Test custom interval: every 3 days."""
    r = await client.post(
        "/api/agenda/series",
        json={
            **SERIES_BASE,
            "recurrence_type": "daily",
            "interval": 3,
            "series_start": "2026-06-01",
            "series_end": "2026-06-10",
        },
    )
    assert r.status_code == 201

    events = (await client.get("/api/agenda/", params={"start": "2026-06-01", "end": "2026-06-10"})).json()
    dates = [e["start_time"][:10] for e in events]
    assert dates == ["2026-06-01", "2026-06-04", "2026-06-07", "2026-06-10"]


async def test_monthly_first_monday(client: AsyncClient):
    """Test monthly pattern: first Monday of each month."""
    r = await client.post(
        "/api/agenda/series",
        json={
            **SERIES_BASE,
            "recurrence_type": "monthly",
            "monthly_pattern": "first_monday",
            "series_start": "2026-06-01",  # June 1, 2026 is a Monday
            "series_end": "2026-09-30",
        },
    )
    assert r.status_code == 201

    events = (await client.get("/api/agenda/", params={"start": "2026-06-01", "end": "2026-09-30"})).json()
    dates = [e["start_time"][:10] for e in events]
    # First Mondays: Jun 1, Jul 6, Aug 3, Sep 7
    assert "2026-06-01" in dates
    assert "2026-07-06" in dates
    assert "2026-08-03" in dates
    assert "2026-09-07" in dates


async def test_end_after_count(client: AsyncClient):
    """Test ending after a specific number of occurrences."""
    payload = {**SERIES_BASE, "recurrence_type": "weekly", "series_start": "2026-06-01", "count": 5}
    payload.pop("series_end")  # Remove series_end since we're using count

    r = await client.post("/api/agenda/series", json=payload)
    assert r.status_code == 201

    events = (await client.get("/api/agenda/", params={"start": "2026-06-01", "end": "2026-12-31"})).json()
    assert len(events) == 5


async def test_yearly_recurrence_with_count(client: AsyncClient):
    """Test yearly recurrence pattern for agenda series."""
    payload = {
        **SERIES_BASE,
        "recurrence_type": "yearly",
        "series_start": "2026-06-01",
        "count": 3,
    }
    payload.pop("series_end")

    r = await client.post("/api/agenda/series", json=payload)
    assert r.status_code == 201

    events = (await client.get("/api/agenda/", params={"start": "2026-01-01", "end": "2028-12-31"})).json()
    dates = [e["start_time"][:10] for e in events]
    assert dates == ["2026-06-01", "2027-06-01", "2028-06-01"]


async def test_validation_count_and_series_end_exclusive(client: AsyncClient):
    """Test that both count and series_end cannot be specified together."""
    r = await client.post(
        "/api/agenda/series",
        json={
            **SERIES_BASE,
            "recurrence_type": "weekly",
            "series_start": "2026-06-01",
            "count": 10,
            "series_end": "2026-12-31",
        },
    )
    assert r.status_code == 422  # Validation error


async def test_validation_neither_count_nor_series_end(client: AsyncClient):
    """Test that infinite series is created when neither count nor series_end is provided."""
    payload = {**SERIES_BASE, "recurrence_type": "weekly", "series_start": "2026-06-01"}
    payload.pop("series_end")  # Remove series_end - creates infinite series
    r = await client.post("/api/agenda/series", json=payload)
    assert r.status_code == 201  # Infinite series should be created successfully
    data = r.json()
    assert data["series_end"] is None
    assert data["count"] is None
    # Cleanup
    await client.delete(f"/api/agenda/series/{data['id']}")


async def test_daily_allday_series_correct_end_date(client: AsyncClient):
    """Test that a daily all-day series generates events on the correct days.

    This test verifies that series_end is inclusive. A series from June 1-3
    should create events on June 1, 2, and 3 (3 events total).

    This is important for multi-day all-day events: if an event ends at midnight
    on a day, that day should NOT be included in the series (e.g., an event
    from June 1 00:00 to June 3 00:00 should only appear on June 1 and 2).
    """
    payload = {
        **SERIES_BASE,
        "recurrence_type": "daily",
        "all_day": True,
        "series_start": "2026-06-01",
        "series_end": "2026-06-03",
        "start_time_of_day": "00:00:00",
        "end_time_of_day": "23:59:59",
    }

    r = await client.post("/api/agenda/series", json=payload)
    assert r.status_code == 201

    events = (await client.get("/api/agenda/", params={"start": "2026-06-01", "end": "2026-06-10"})).json()
    assert len(events) == 3
    dates = [e["start_time"][:10] for e in events]
    assert dates == ["2026-06-01", "2026-06-02", "2026-06-03"]
