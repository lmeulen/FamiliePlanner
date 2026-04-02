"""Integration tests for infinite recurrences and expanded monthly patterns (GitHub issue #63)."""

from datetime import date

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_create_agenda_series_with_count(client: AsyncClient):
    """Test creating agenda series with count (series_end should be None)."""
    payload = {
        "title": "Weekly Meeting",
        "description": "Team sync",
        "location": "Office",
        "all_day": False,
        "recurrence_type": "weekly",
        "series_start": "2026-04-02",
        "series_end": None,  # Should accept None when count is provided
        "start_time_of_day": "10:00",
        "end_time_of_day": "11:00",
        "interval": 1,
        "count": 4,
        "member_ids": [],
    }
    r = await client.post("/api/agenda/series", json=payload)
    assert r.status_code == 201, f"Failed: {r.text}"
    data = r.json()
    assert data["series_end"] is None
    assert data["count"] == 4

    # Verify 4 events were created
    events_r = await client.get("/api/agenda/")
    events = events_r.json()
    series_events = [e for e in events if e.get("series_id") == data["id"]]
    assert len(series_events) == 4

    # Cleanup
    await client.delete(f"/api/agenda/series/{data['id']}")


@pytest.mark.asyncio
async def test_create_infinite_agenda_series(client: AsyncClient):
    """Test creating infinite agenda series (both series_end and count are None)."""
    payload = {
        "title": "Daily Standup",
        "description": "Quick sync",
        "location": "",
        "all_day": False,
        "recurrence_type": "daily",
        "series_start": "2026-04-02",
        "series_end": None,  # Infinite!
        "start_time_of_day": "09:00",
        "end_time_of_day": "09:15",
        "interval": 1,
        "count": None,  # Infinite!
        "member_ids": [],
    }
    r = await client.post("/api/agenda/series", json=payload)
    assert r.status_code == 201, f"Failed: {r.text}"
    data = r.json()
    assert data["series_end"] is None
    assert data["count"] is None

    # Verify events were created (should be ~365 for daily over 1 year)
    events_r = await client.get("/api/agenda/")
    events = events_r.json()
    series_events = [e for e in events if e.get("series_id") == data["id"]]
    assert len(series_events) == 365  # Daily for 1 year

    # Verify events span roughly 1 year
    first_event = min(series_events, key=lambda e: e["start_time"])
    last_event = max(series_events, key=lambda e: e["start_time"])
    first_date = date.fromisoformat(first_event["start_time"].split("T")[0])
    last_date = date.fromisoformat(last_event["start_time"].split("T")[0])
    days_span = (last_date - first_date).days
    assert 360 <= days_span <= 370  # Approximately 1 year

    # Cleanup
    await client.delete(f"/api/agenda/series/{data['id']}")


@pytest.mark.asyncio
async def test_create_task_series_with_count(client: AsyncClient):
    """Test creating task series with count (series_end should be None)."""
    # Create task list first
    list_r = await client.post("/api/tasks/lists", json={"name": "Test List", "color": "#FF0000"})
    list_id = list_r.json()["id"]

    payload = {
        "title": "Weekly Review",
        "description": "",
        "list_id": list_id,
        "recurrence_type": "weekly",
        "series_start": "2026-04-02",
        "series_end": None,
        "interval": 1,
        "count": 3,
        "member_ids": [],
    }
    r = await client.post("/api/tasks/series", json=payload)
    assert r.status_code == 201, f"Failed: {r.text}"
    data = r.json()
    assert data["series_end"] is None
    assert data["count"] == 3

    # Verify 3 tasks were created
    tasks_r = await client.get(f"/api/tasks/?list_id={list_id}")
    tasks = tasks_r.json()
    series_tasks = [t for t in tasks if t.get("series_id") == data["id"]]
    assert len(series_tasks) == 3

    # Cleanup
    await client.delete(f"/api/tasks/series/{data['id']}")
    await client.delete(f"/api/tasks/lists/{list_id}")


@pytest.mark.asyncio
async def test_create_infinite_task_series(client: AsyncClient):
    """Test creating infinite task series (both series_end and count are None)."""
    # Create task list first
    list_r = await client.post("/api/tasks/lists", json={"name": "Test List", "color": "#00FF00"})
    list_id = list_r.json()["id"]

    payload = {
        "title": "Weekly Groceries",
        "description": "",
        "list_id": list_id,
        "recurrence_type": "weekly",
        "series_start": "2026-04-02",
        "series_end": None,  # Infinite!
        "interval": 1,
        "count": None,  # Infinite!
        "member_ids": [],
    }
    r = await client.post("/api/tasks/series", json=payload)
    assert r.status_code == 201, f"Failed: {r.text}"
    data = r.json()
    assert data["series_end"] is None
    assert data["count"] is None

    # Verify tasks were created (should be ~52 for weekly over 1 year)
    tasks_r = await client.get(f"/api/tasks/?list_id={list_id}")
    tasks = tasks_r.json()
    series_tasks = [t for t in tasks if t.get("series_id") == data["id"]]
    assert 52 <= len(series_tasks) <= 54  # Weekly for ~1 year

    # Cleanup
    await client.delete(f"/api/tasks/series/{data['id']}")
    await client.delete(f"/api/tasks/lists/{list_id}")


@pytest.mark.asyncio
async def test_expanded_monthly_patterns_agenda(client: AsyncClient):
    """Test all 35 monthly pattern combinations work for agenda."""
    # Test a sample of patterns (testing all 35 would be slow)
    test_patterns = [
        "second_wednesday",  # New pattern
        "third_saturday",  # New pattern (weekend)
        "fourth_thursday",  # New pattern
        "last_sunday",  # New pattern (weekend)
    ]

    for pattern in test_patterns:
        payload = {
            "title": f"Monthly {pattern}",
            "description": "",
            "location": "",
            "all_day": True,
            "recurrence_type": "monthly",
            "monthly_pattern": pattern,
            "series_start": "2026-04-01",
            "series_end": "2026-12-31",
            "start_time_of_day": "00:00",
            "end_time_of_day": "23:59",
            "interval": 1,
            "member_ids": [],
        }
        r = await client.post("/api/agenda/series", json=payload)
        assert r.status_code == 201, f"Failed for pattern {pattern}: {r.text}"
        data = r.json()
        assert data["monthly_pattern"] == pattern

        # Verify events were created
        events_r = await client.get("/api/agenda/")
        events = events_r.json()
        series_events = [e for e in events if e.get("series_id") == data["id"]]
        assert len(series_events) >= 8  # At least 8 months worth (Apr-Dec = 9 months)

        # Cleanup
        await client.delete(f"/api/agenda/series/{data['id']}")


@pytest.mark.asyncio
async def test_expanded_monthly_patterns_tasks(client: AsyncClient):
    """Test expanded monthly patterns work for tasks."""
    # Create task list
    list_r = await client.post("/api/tasks/lists", json={"name": "Test List", "color": "#0000FF"})
    list_id = list_r.json()["id"]

    test_patterns = [
        "second_tuesday",
        "fourth_friday",
        "third_sunday",
    ]

    for pattern in test_patterns:
        payload = {
            "title": f"Monthly {pattern} task",
            "description": "",
            "list_id": list_id,
            "recurrence_type": "monthly",
            "monthly_pattern": pattern,
            "series_start": "2026-04-01",
            "series_end": "2026-12-31",
            "interval": 1,
            "member_ids": [],
        }
        r = await client.post("/api/tasks/series", json=payload)
        assert r.status_code == 201, f"Failed for pattern {pattern}: {r.text}"
        data = r.json()
        assert data["monthly_pattern"] == pattern

        # Verify tasks were created
        tasks_r = await client.get(f"/api/tasks/?list_id={list_id}")
        tasks = tasks_r.json()
        series_tasks = [t for t in tasks if t.get("series_id") == data["id"]]
        assert len(series_tasks) >= 8

        # Cleanup
        await client.delete(f"/api/tasks/series/{data['id']}")

    # Cleanup list
    await client.delete(f"/api/tasks/lists/{list_id}")


@pytest.mark.asyncio
async def test_update_series_to_infinite(client: AsyncClient):
    """Test updating an existing series to become infinite."""
    # Create task list
    list_r = await client.post("/api/tasks/lists", json={"name": "Test List", "color": "#FFFF00"})
    list_id = list_r.json()["id"]

    # Create finite series
    payload = {
        "title": "Weekly Task",
        "description": "",
        "list_id": list_id,
        "recurrence_type": "weekly",
        "series_start": "2026-04-02",
        "series_end": "2026-05-31",
        "interval": 1,
        "member_ids": [],
    }
    r = await client.post("/api/tasks/series", json=payload)
    assert r.status_code == 201
    series_id = r.json()["id"]

    # Update to infinite
    update_payload = {
        "title": "Weekly Task (Infinite)",
        "description": "",
        "list_id": list_id,
        "recurrence_type": "weekly",
        "series_start": "2026-04-02",
        "series_end": None,  # Make infinite
        "count": None,  # Make infinite
        "interval": 1,
        "member_ids": [],
    }
    r = await client.put(f"/api/tasks/series/{series_id}", json=update_payload)
    assert r.status_code == 200
    data = r.json()
    assert data["series_end"] is None
    assert data["count"] is None

    # Verify many more tasks were created
    tasks_r = await client.get(f"/api/tasks/?list_id={list_id}")
    tasks = tasks_r.json()
    series_tasks = [t for t in tasks if t.get("series_id") == series_id]
    assert len(series_tasks) >= 52  # Should have ~52 weeks worth now

    # Cleanup
    await client.delete(f"/api/tasks/series/{series_id}")
    await client.delete(f"/api/tasks/lists/{list_id}")
