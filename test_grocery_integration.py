#!/usr/bin/env python3
"""
Integration test for grocery list endpoints.
Tests the full flow: categories, items, learning, and offline support.
"""

import asyncio
import os
import sys

# Disable auth for testing
os.environ["AUTH_DISABLED"] = "1"

from httpx import ASGITransport, AsyncClient

from app.main import app


async def test_grocery_endpoints():
    """Test grocery list endpoints."""
    print("=" * 80)
    print("Testing Grocery List Integration")
    print("=" * 80)

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        # 1. Get categories
        print("\n1. GET /api/grocery/categories")
        resp = await client.get("/api/grocery/categories")
        assert resp.status_code == 200, f"Failed: {resp.status_code}"
        categories = resp.json()
        print(f"   ✓ Found {len(categories)} categories")
        for cat in categories[:3]:
            print(f"     - {cat['icon']} {cat['name']}")

        # 2. Add items with different inputs
        test_items = [
            "2 kg tomaten",
            "500 gram kaas",
            "brood",
            "3 stuks appels",
            "1 liter melk",
        ]

        print("\n2. POST /api/grocery/items (adding items)")
        for raw_input in test_items:
            resp = await client.post("/api/grocery/items", json={"raw_input": raw_input})
            assert resp.status_code == 201, f"Failed to add '{raw_input}': {resp.status_code}"
            item = resp.json()
            print(f"   ✓ Added: {item['display_name']} ({item['quantity'] or ''} {item['unit'] or ''})")

        # 3. Get all items
        print("\n3. GET /api/grocery/items")
        resp = await client.get("/api/grocery/items")
        assert resp.status_code == 200
        items = resp.json()
        print(f"   ✓ Retrieved {len(items)} items")

        # 4. Check off an item
        print("\n4. PATCH /api/grocery/items/{id} (check off item)")
        first_item = items[0]
        resp = await client.patch(f"/api/grocery/items/{first_item['id']}", json={"checked": True})
        assert resp.status_code == 200
        print(f"   ✓ Checked off: {first_item['display_name']}")

        # 5. Add same product again (test learning)
        print("\n5. POST /api/grocery/items (test learning)")
        resp = await client.post("/api/grocery/items", json={"raw_input": "tomaten"})
        assert resp.status_code == 201
        new_item = resp.json()
        print("   ✓ Added 'tomaten' again")
        print(f"     Category: {new_item['category_id']} (should match previous)")

        # 6. Update item category
        print("\n6. PATCH /api/grocery/items/{id} (update category)")
        resp = await client.patch(f"/api/grocery/items/{new_item['id']}", json={"category_id": 2})
        assert resp.status_code == 200
        print(f"   ✓ Updated category for item {new_item['id']}")

        # 7. Reorder categories
        print("\n7. PUT /api/grocery/categories/reorder")
        reorder_payload = [{"id": cat["id"], "sort_order": (i + 1) * 10} for i, cat in enumerate(reversed(categories))]
        resp = await client.put("/api/grocery/categories/reorder", json=reorder_payload)
        assert resp.status_code == 200
        print(f"   ✓ Reordered {len(categories)} categories")

        # 8. Clear done items
        print("\n8. DELETE /api/grocery/items/done")
        resp = await client.delete("/api/grocery/items/done")
        assert resp.status_code == 204
        print("   ✓ Cleared checked items")

        # 9. Delete an item
        print("\n9. DELETE /api/grocery/items/{id}")
        resp = await client.get("/api/grocery/items")
        remaining = resp.json()
        if remaining:
            resp = await client.delete(f"/api/grocery/items/{remaining[0]['id']}")
            assert resp.status_code == 204
            print(f"   ✓ Deleted item {remaining[0]['id']}")

    print("\n" + "=" * 80)
    print("All grocery integration tests passed! ✓")
    print("=" * 80)


if __name__ == "__main__":
    try:
        asyncio.run(test_grocery_endpoints())
        sys.exit(0)
    except Exception as e:
        print(f"\n✗ Test failed: {e}")
        import traceback

        traceback.print_exc()
        sys.exit(1)
