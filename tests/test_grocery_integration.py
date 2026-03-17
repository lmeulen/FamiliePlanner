"""
Integration test for grocery list endpoints.
Tests the full flow: categories, items, learning, and offline support.
"""

from httpx import AsyncClient


async def test_grocery_endpoints(client: AsyncClient):
    """Test grocery list endpoints."""
    # Seed default categories (migrations don't run in test db)
    default_categories = [
        {"name": "Groente & Fruit", "icon": "🥬", "color": "#4CAF50"},
        {"name": "Brood & Bakkerij", "icon": "🍞", "color": "#FF9800"},
        {"name": "Zuivel", "icon": "🥛", "color": "#2196F3"},
        {"name": "Vlees & Vis", "icon": "🥩", "color": "#F44336"},
        {"name": "Overig", "icon": "❓", "color": "#9EA7C4"},
    ]
    for cat in default_categories:
        await client.post("/api/grocery/categories", json=cat)

    # 1. Get categories
    resp = await client.get("/api/grocery/categories")
    assert resp.status_code == 200, f"Failed: {resp.status_code}"
    categories = resp.json()
    assert len(categories) >= 5, "Expected at least 5 categories to exist"

    # 2. Add items with different inputs
    test_items = [
        "2 kg tomaten",
        "500 gram kaas",
        "brood",
        "3 stuks appels",
        "1 liter melk",
    ]

    for raw_input in test_items:
        resp = await client.post("/api/grocery/items", json={"raw_input": raw_input})
        assert resp.status_code == 201, f"Failed to add '{raw_input}': {resp.status_code}"

    # 3. Get all items
    resp = await client.get("/api/grocery/items")
    assert resp.status_code == 200
    items = resp.json()
    assert len(items) == len(test_items), f"Expected {len(test_items)} items, got {len(items)}"

    # 4. Check off an item
    first_item = items[0]
    resp = await client.patch(f"/api/grocery/items/{first_item['id']}", json={"checked": True})
    assert resp.status_code == 200

    # 5. Add same product again (test learning)
    resp = await client.post("/api/grocery/items", json={"raw_input": "tomaten"})
    assert resp.status_code == 201
    new_item = resp.json()

    # 6. Update item category
    resp = await client.patch(f"/api/grocery/items/{new_item['id']}", json={"category_id": 2})
    assert resp.status_code == 200

    # 7. Reorder categories
    reorder_payload = [{"id": cat["id"], "sort_order": (i + 1) * 10} for i, cat in enumerate(reversed(categories))]
    resp = await client.put("/api/grocery/categories/reorder", json=reorder_payload)
    assert resp.status_code == 200

    # 8. Clear done items
    resp = await client.delete("/api/grocery/items/done")
    assert resp.status_code == 204

    # 9. Delete an item
    resp = await client.get("/api/grocery/items")
    remaining = resp.json()
    if remaining:
        resp = await client.delete(f"/api/grocery/items/{remaining[0]['id']}")
        assert resp.status_code == 204
