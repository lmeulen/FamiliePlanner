"""Tests for /api/stats endpoint."""

from httpx import AsyncClient


async def test_stats_empty_database(client: AsyncClient):
    """Test statistics with empty database."""
    r = await client.get("/api/stats/?period=all")
    assert r.status_code == 200

    data = r.json()
    assert data["period"] == "all"
    assert data["database_counts"]["family_members"] == 0
    assert data["database_counts"]["tasks"] == 0
    assert data["database_counts"]["agenda_events"] == 0
    assert data["database_counts"]["meals"] == 0
    assert data["task_completions"] == []
    assert data["cooking_frequency"] == []
    assert data["top_meals"] == []


async def test_stats_with_data(client: AsyncClient):
    """Test statistics with actual data."""
    # Create family member
    member_r = await client.post("/api/family/", json={"name": "Test Member", "avatar": "👤"})
    member_id = member_r.json()["id"]

    # Create task list
    list_r = await client.post("/api/tasks/lists", json={"name": "Test List", "color": "#4ECDC4"})
    list_id = list_r.json()["id"]

    # Create and complete tasks
    task1_r = await client.post(
        "/api/tasks/",
        json={
            "title": "Task 1",
            "description": "",
            "list_id": list_id,
            "member_ids": [member_id],
            "due_date": None,
        },
    )
    task1_id = task1_r.json()["id"]
    await client.patch(f"/api/tasks/{task1_id}/toggle")  # Mark as done

    # Create incomplete task
    await client.post(
        "/api/tasks/",
        json={
            "title": "Task 2",
            "description": "",
            "list_id": list_id,
            "member_ids": [member_id],
            "due_date": None,
        },
    )

    # Create meals
    await client.post(
        "/api/meals/",
        json={
            "date": "2026-03-10",
            "meal_type": "dinner",
            "name": "Spaghetti",
            "description": "",
            "recipe_url": "",
            "cook_member_id": member_id,
        },
    )
    await client.post(
        "/api/meals/",
        json={
            "date": "2026-03-11",
            "meal_type": "dinner",
            "name": "Spaghetti",
            "description": "",
            "recipe_url": "",
            "cook_member_id": member_id,
        },
    )

    # Create agenda event
    await client.post(
        "/api/agenda/",
        json={
            "title": "Test Event",
            "description": "",
            "location": "",
            "start_time": "2026-03-10T10:00:00",
            "end_time": "2026-03-10T11:00:00",
            "all_day": False,
            "member_ids": [],
            "color": "#4ECDC4",
        },
    )

    # Get statistics
    r = await client.get("/api/stats/?period=all")
    assert r.status_code == 200

    data = r.json()
    assert data["database_counts"]["family_members"] == 1
    assert data["database_counts"]["tasks"] == 2
    assert data["database_counts"]["task_lists"] == 1
    assert data["database_counts"]["agenda_events"] == 1
    assert data["database_counts"]["meals"] == 2

    # Task completion stats
    assert len(data["task_completions"]) == 1
    assert data["task_completions"][0]["member_id"] == member_id
    assert data["task_completions"][0]["count"] == 1
    assert data["task_stats"]["total"] == 2
    assert data["task_stats"]["completed"] == 1
    assert data["task_stats"]["completion_rate"] == 50.0

    # Cooking stats
    assert len(data["cooking_frequency"]) == 1
    assert data["cooking_frequency"][0]["member_id"] == member_id
    assert data["cooking_frequency"][0]["count"] == 2

    # Top meals
    assert len(data["top_meals"]) == 1
    assert data["top_meals"][0]["name"] == "Spaghetti"
    assert data["top_meals"][0]["count"] == 2

    # Agenda activity
    assert data["agenda_activity"]["total_events"] == 1


async def test_stats_period_filter_week(client: AsyncClient):
    """Test statistics with week period filter."""
    r = await client.get("/api/stats/?period=week")
    assert r.status_code == 200
    assert r.json()["period"] == "week"


async def test_stats_period_filter_month(client: AsyncClient):
    """Test statistics with month period filter."""
    r = await client.get("/api/stats/?period=month")
    assert r.status_code == 200
    assert r.json()["period"] == "month"


async def test_stats_period_filter_year(client: AsyncClient):
    """Test statistics with year period filter."""
    r = await client.get("/api/stats/?period=year")
    assert r.status_code == 200
    assert r.json()["period"] == "year"


async def test_stats_invalid_period(client: AsyncClient):
    """Test statistics with invalid period."""
    r = await client.get("/api/stats/?period=invalid")
    assert r.status_code == 422  # Validation error


async def test_stats_top_meals_limit(client: AsyncClient):
    """Test that top meals respects 10-item limit."""
    member_r = await client.post("/api/family/", json={"name": "Cook", "avatar": "👨‍🍳"})
    member_id = member_r.json()["id"]

    # Create 15 different meals
    for i in range(15):
        await client.post(
            "/api/meals/",
            json={
                "date": "2026-03-10",
                "meal_type": "dinner",
                "name": f"Meal {i}",
                "description": "",
                "recipe_url": "",
                "cook_member_id": member_id,
            },
        )

    r = await client.get("/api/stats/?period=all")
    assert r.status_code == 200

    data = r.json()
    assert len(data["top_meals"]) == 10  # Should be limited to 10


async def test_stats_task_completion_multiple_members(client: AsyncClient):
    """Test task completion stats with multiple members."""
    # Create two members
    member1_r = await client.post("/api/family/", json={"name": "Member 1", "avatar": "👤"})
    member1_id = member1_r.json()["id"]

    member2_r = await client.post("/api/family/", json={"name": "Member 2", "avatar": "👥"})
    member2_id = member2_r.json()["id"]

    # Create task list
    list_r = await client.post("/api/tasks/lists", json={"name": "Test List", "color": "#4ECDC4"})
    list_id = list_r.json()["id"]

    # Create tasks for member 1 (2 completed)
    for _ in range(2):
        task_r = await client.post(
            "/api/tasks/",
            json={
                "title": "Task",
                "description": "",
                "list_id": list_id,
                "member_ids": [member1_id],
                "due_date": None,
            },
        )
        await client.patch(f"/api/tasks/{task_r.json()['id']}/toggle")

    # Create tasks for member 2 (3 completed)
    for _ in range(3):
        task_r = await client.post(
            "/api/tasks/",
            json={
                "title": "Task",
                "description": "",
                "list_id": list_id,
                "member_ids": [member2_id],
                "due_date": None,
            },
        )
        await client.patch(f"/api/tasks/{task_r.json()['id']}/toggle")

    r = await client.get("/api/stats/?period=all")
    assert r.status_code == 200

    data = r.json()
    assert len(data["task_completions"]) == 2

    # Should be sorted by count (member2 first with 3)
    assert data["task_completions"][0]["member_id"] == member2_id
    assert data["task_completions"][0]["count"] == 3
    assert data["task_completions"][1]["member_id"] == member1_id
    assert data["task_completions"][1]["count"] == 2
