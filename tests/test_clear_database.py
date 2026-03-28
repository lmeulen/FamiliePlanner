"""Tests for database clearing endpoints."""

import pytest


@pytest.mark.asyncio
async def test_clear_all_agenda(client):
    """Test clearing all agenda events."""
    # Create some events
    await client.post("/api/agenda/", json={
        "title": "Event 1",
        "start_time": "2026-04-01T10:00",
        "end_time": "2026-04-01T11:00",
        "all_day": False
    })
    await client.post("/api/agenda/", json={
        "title": "Event 2",
        "start_time": "2026-04-02T14:00",
        "end_time": "2026-04-02T15:00",
        "all_day": False
    })

    # Verify events exist
    response = await client.get("/api/agenda/")
    assert response.status_code == 200
    assert len(response.json()) == 2

    # Clear all events
    response = await client.delete("/api/agenda/all")
    assert response.status_code == 204

    # Verify all events are deleted
    response = await client.get("/api/agenda/")
    assert response.status_code == 200
    assert len(response.json()) == 0


@pytest.mark.asyncio
async def test_clear_all_tasks(client):
    """Test clearing all tasks and lists."""
    # Create a task list (no trailing slash)
    list_resp = await client.post("/api/tasks/lists", json={"name": "Test List"})
    assert list_resp.status_code == 201
    list_id = list_resp.json()["id"]

    # Create some tasks
    await client.post("/api/tasks/", json={
        "title": "Task 1",
        "list_id": list_id
    })
    await client.post("/api/tasks/", json={
        "title": "Task 2",
        "list_id": list_id
    })

    # Verify tasks exist
    response = await client.get("/api/tasks/")
    assert response.status_code == 200
    assert len(response.json()) == 2

    # Clear all tasks
    response = await client.delete("/api/tasks/all")
    assert response.status_code == 204

    # Verify all tasks and lists are deleted
    response = await client.get("/api/tasks/")
    assert response.status_code == 200
    assert len(response.json()) == 0

    response = await client.get("/api/tasks/lists")
    assert response.status_code == 200
    assert len(response.json()) == 0


@pytest.mark.asyncio
async def test_clear_all_meals(client):
    """Test clearing all meals."""
    # Create some meals
    await client.post("/api/meals/", json={
        "name": "Breakfast",
        "meal_type": "breakfast",
        "date": "2026-04-01"
    })
    await client.post("/api/meals/", json={
        "name": "Dinner",
        "meal_type": "dinner",
        "date": "2026-04-01"
    })

    # Verify meals exist
    response = await client.get("/api/meals/")
    assert response.status_code == 200
    assert len(response.json()) == 2

    # Clear all meals
    response = await client.delete("/api/meals/all")
    assert response.status_code == 204

    # Verify all meals are deleted
    response = await client.get("/api/meals/")
    assert response.status_code == 200
    assert len(response.json()) == 0


@pytest.mark.asyncio
async def test_clear_all_grocery(client):
    """Test clearing all grocery items."""
    # Create a category first (grocery router creates defaults, but test DB might be empty)
    cat_resp = await client.post("/api/grocery/categories", json={"name": "Test Category", "sort_order": 1})
    if cat_resp.status_code == 201:
        category_id = cat_resp.json()["id"]
    else:
        # Category might already exist, get it
        cats_resp = await client.get("/api/grocery/categories")
        assert cats_resp.status_code == 200
        categories = cats_resp.json()
        if len(categories) == 0:
            pytest.skip("No categories available and cannot create one")
        category_id = categories[0]["id"]

    # Create some grocery items
    await client.post("/api/grocery/items", json={
        "product_name": "Milk",
        "category_id": category_id
    })
    await client.post("/api/grocery/items", json={
        "product_name": "Bread",
        "category_id": category_id
    })

    # Verify items exist
    response = await client.get("/api/grocery/items")
    assert response.status_code == 200
    assert len(response.json()) >= 2

    # Clear all grocery items
    response = await client.delete("/api/grocery/all")
    assert response.status_code == 204

    # Verify all items are deleted
    response = await client.get("/api/grocery/items")
    assert response.status_code == 200
    assert len(response.json()) == 0


@pytest.mark.asyncio
async def test_clear_all_family_members(client):
    """Test clearing all family members."""
    # Create some family members
    await client.post("/api/family/", json={
        "name": "John",
        "color": "#FF0000",
        "avatar": "👨"
    })
    await client.post("/api/family/", json={
        "name": "Jane",
        "color": "#00FF00",
        "avatar": "👩"
    })

    # Verify members exist
    response = await client.get("/api/family/")
    assert response.status_code == 200
    assert len(response.json()) == 2

    # Clear all family members
    response = await client.delete("/api/family/all")
    assert response.status_code == 204

    # Verify all members are deleted
    response = await client.get("/api/family/")
    assert response.status_code == 200
    assert len(response.json()) == 0


@pytest.mark.asyncio
async def test_clear_preserves_categories(client):
    """Test that clearing grocery items preserves categories."""
    # Get categories before
    cats_before = await client.get("/api/grocery/categories")
    assert cats_before.status_code == 200
    categories_before = cats_before.json()
    category_count = len(categories_before)

    # Add some items
    if category_count > 0:
        await client.post("/api/grocery/items", json={
            "product_name": "Test Item",
            "category_id": categories_before[0]["id"]
        })

    # Clear all items
    await client.delete("/api/grocery/all")

    # Verify categories are preserved
    cats_after = await client.get("/api/grocery/categories")
    assert cats_after.status_code == 200
    assert len(cats_after.json()) == category_count
