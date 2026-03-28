"""Test to reproduce family member update bug."""

import pytest


@pytest.mark.asyncio
async def test_family_member_color_and_avatar_update(client):
    """Test that color and avatar updates persist through the API."""

    # Create a test family member via API (cleaner)
    create_data = {"name": "Test Person", "color": "#FF0000", "avatar": "👤"}
    response = await client.post("/api/family/", json=create_data)
    assert response.status_code == 201
    created = response.json()
    member_id = created["id"]

    print(
        f"\n✓ Created member via API: id={member_id}, name='{created['name']}', color={created['color']}, avatar={created['avatar']}"
    )

    # Update via API
    update_data = {"name": "Test Person Updated", "color": "#00FF00", "avatar": "🚀"}

    print(f"→ Sending PUT /api/family/{member_id} with: {update_data}")
    response = await client.put(f"/api/family/{member_id}", json=update_data)

    print(f"← Response status: {response.status_code}")
    assert response.status_code == 200

    result = response.json()
    print(f"← Response body: {result}")

    # Check API response
    assert (
        result["name"] == "Test Person Updated"
    ), f"Name not updated! Expected 'Test Person Updated', got '{result['name']}'"
    assert (
        result["color"] == "#00FF00"
    ), f"❌ Color not updated in API response! Expected '#00FF00', got '{result['color']}'"
    assert result["avatar"] == "🚀", f"❌ Avatar not updated in API response! Expected '🚀', got '{result['avatar']}'"

    # Verify by fetching via API (this tests actual persistence)
    print(f"→ Fetching member {member_id} via GET to verify persistence...")
    response = await client.get(f"/api/family/{member_id}")
    assert response.status_code == 200
    fetched = response.json()

    print(f"← Fetched from DB: name='{fetched['name']}', color={fetched['color']}, avatar={fetched['avatar']}")

    assert fetched["name"] == "Test Person Updated", f"❌ Name not persisted! Got '{fetched['name']}'"
    assert fetched["color"] == "#00FF00", f"❌ Color not persisted! Expected '#00FF00', got '{fetched['color']}'"
    assert fetched["avatar"] == "🚀", f"❌ Avatar not persisted! Expected '🚀', got '{fetched['avatar']}'"

    print("✅ All assertions passed - update works correctly!")
