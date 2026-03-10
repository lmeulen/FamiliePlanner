"""Tests for /api/search endpoint."""

from httpx import AsyncClient


async def test_search_requires_min_3_chars(client: AsyncClient):
    """Test that search requires minimum 3 characters."""
    r = await client.get("/api/search/?q=ab")
    assert r.status_code == 422  # Validation error


async def test_search_empty_database(client: AsyncClient):
    """Test search returns empty results when database is empty."""
    r = await client.get("/api/search/?q=test")
    assert r.status_code == 200
    data = r.json()
    assert data["events"] == []
    assert data["tasks"] == []
    assert data["meals"] == []


async def test_search_events(client: AsyncClient):
    """Test searching in agenda events."""
    # Create event
    await client.post(
        "/api/agenda/",
        json={
            "title": "Voetbaltraining",
            "description": "Wekelijkse training",
            "location": "Sporthal",
            "start_time": "2026-03-10T18:00:00",
            "end_time": "2026-03-10T19:00:00",
            "all_day": False,
            "member_ids": [],
        },
    )

    # Search by title
    r = await client.get("/api/search/?q=voetbal")
    assert r.status_code == 200
    data = r.json()
    assert len(data["events"]) == 1
    assert "voetbal" in data["events"][0]["title"].lower()

    # Search by location
    r = await client.get("/api/search/?q=sporthal")
    assert r.status_code == 200
    data = r.json()
    assert len(data["events"]) == 1
    assert "sporthal" in data["events"][0]["location"].lower()


async def test_search_tasks(client: AsyncClient):
    """Test searching in tasks."""
    # Create task list
    list_r = await client.post("/api/tasks/lists", json={"name": "Boodschappen", "color": "#4ECDC4"})
    list_id = list_r.json()["id"]

    # Create task
    await client.post(
        "/api/tasks/",
        json={
            "title": "Melk kopen",
            "description": "Volle melk",
            "list_id": list_id,
            "member_ids": [],
            "due_date": "2026-03-10",
        },
    )

    # Search by title
    r = await client.get("/api/search/?q=melk")
    assert r.status_code == 200
    data = r.json()
    assert len(data["tasks"]) == 1
    assert "melk" in data["tasks"][0]["title"].lower()

    # Search by list name
    r = await client.get("/api/search/?q=boodschappen")
    assert r.status_code == 200
    data = r.json()
    assert len(data["tasks"]) == 1


async def test_search_meals(client: AsyncClient):
    """Test searching in meals."""
    await client.post(
        "/api/meals/",
        json={
            "date": "2026-03-10",
            "meal_type": "dinner",
            "name": "Spaghetti bolognese",
            "description": "Klassieke Italiaanse pasta",
            "recipe_url": "",
            "cook_member_id": None,
        },
    )

    # Search by name
    r = await client.get("/api/search/?q=spaghetti")
    assert r.status_code == 200
    data = r.json()
    assert len(data["meals"]) == 1
    assert "spaghetti" in data["meals"][0]["name"].lower()

    # Search by description
    r = await client.get("/api/search/?q=italiaanse")
    assert r.status_code == 200
    data = r.json()
    assert len(data["meals"]) == 1


async def test_search_across_all_types(client: AsyncClient):
    """Test search returns results across all types."""
    # Create one of each type
    await client.post(
        "/api/agenda/",
        json={
            "title": "Doktersafspraak",
            "description": "",
            "location": "",
            "start_time": "2026-03-10T14:00:00",
            "end_time": "2026-03-10T15:00:00",
            "all_day": False,
            "member_ids": [],
        },
    )

    list_r = await client.post("/api/tasks/lists", json={"name": "Privé", "color": "#4ECDC4"})
    await client.post(
        "/api/tasks/",
        json={
            "title": "Dokter bellen",
            "description": "",
            "list_id": list_r.json()["id"],
            "member_ids": [],
            "due_date": None,
        },
    )

    await client.post(
        "/api/meals/",
        json={
            "date": "2026-03-10",
            "meal_type": "lunch",
            "name": "Doktersbrood",
            "description": "",
            "recipe_url": "",
            "cook_member_id": None,
        },
    )

    # Search with common term
    r = await client.get("/api/search/?q=dokter")
    assert r.status_code == 200
    data = r.json()
    assert len(data["events"]) == 1
    assert len(data["tasks"]) == 1
    assert len(data["meals"]) == 1


async def test_search_case_insensitive(client: AsyncClient):
    """Test that search is case-insensitive."""
    await client.post(
        "/api/agenda/",
        json={
            "title": "BELANGRIJKE Vergadering",
            "description": "",
            "location": "",
            "start_time": "2026-03-10T10:00:00",
            "end_time": "2026-03-10T11:00:00",
            "all_day": False,
            "member_ids": [],
        },
    )

    # Search lowercase
    r = await client.get("/api/search/?q=belangrijke")
    assert r.status_code == 200
    assert len(r.json()["events"]) == 1

    # Search uppercase
    r = await client.get("/api/search/?q=BELANGRIJKE")
    assert r.status_code == 200
    assert len(r.json()["events"]) == 1

    # Search mixed case
    r = await client.get("/api/search/?q=BeLaNgRiJkE")
    assert r.status_code == 200
    assert len(r.json()["events"]) == 1


async def test_search_respects_limit(client: AsyncClient):
    """Test that search respects the 7-result limit per type."""
    # Create 10 events
    for i in range(10):
        await client.post(
            "/api/agenda/",
            json={
                "title": f"Test Event {i}",
                "description": "",
                "location": "",
                "start_time": f"2026-03-{10 + i}T10:00:00",
                "end_time": f"2026-03-{10 + i}T11:00:00",
                "all_day": False,
                "member_ids": [],
            },
        )

    r = await client.get("/api/search/?q=test")
    assert r.status_code == 200
    data = r.json()
    assert len(data["events"]) <= 7  # Should not exceed limit
