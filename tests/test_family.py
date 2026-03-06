"""Tests for /api/family endpoints."""

from httpx import AsyncClient


async def test_list_members_empty(client: AsyncClient):
    r = await client.get("/api/family/")
    assert r.status_code == 200
    assert r.json() == []


async def test_create_member(client: AsyncClient):
    r = await client.post("/api/family/", json={"name": "Alice", "color": "#FF0000", "avatar": "👩"})
    assert r.status_code == 201
    data = r.json()
    assert data["name"] == "Alice"
    assert data["color"] == "#FF0000"
    assert "id" in data


async def test_create_member_name_required(client: AsyncClient):
    r = await client.post("/api/family/", json={"name": "", "color": "#FF0000", "avatar": "👩"})
    assert r.status_code == 422


async def test_get_member(client: AsyncClient):
    created = (await client.post("/api/family/", json={"name": "Bob", "color": "#00FF00", "avatar": "👨"})).json()
    r = await client.get(f"/api/family/{created['id']}")
    assert r.status_code == 200
    assert r.json()["name"] == "Bob"


async def test_get_member_not_found(client: AsyncClient):
    r = await client.get("/api/family/9999")
    assert r.status_code == 404


async def test_update_member(client: AsyncClient):
    created = (await client.post("/api/family/", json={"name": "Carol", "color": "#0000FF", "avatar": "🧒"})).json()
    r = await client.put(
        f"/api/family/{created['id']}", json={"name": "Carol Updated", "color": "#0000FF", "avatar": "🧒"}
    )
    assert r.status_code == 200
    assert r.json()["name"] == "Carol Updated"


async def test_update_member_not_found(client: AsyncClient):
    r = await client.put("/api/family/9999", json={"name": "X", "color": "#000000", "avatar": "👤"})
    assert r.status_code == 404


async def test_delete_member(client: AsyncClient):
    created = (await client.post("/api/family/", json={"name": "Dave", "color": "#FF00FF", "avatar": "👤"})).json()
    r = await client.delete(f"/api/family/{created['id']}")
    assert r.status_code == 204
    assert (await client.get(f"/api/family/{created['id']}")).status_code == 404


async def test_delete_member_not_found(client: AsyncClient):
    r = await client.delete("/api/family/9999")
    assert r.status_code == 404


async def test_list_members_returns_all(client: AsyncClient):
    for name in ["Eve", "Frank", "Grace"]:
        await client.post("/api/family/", json={"name": name, "color": "#AAAAAA", "avatar": "👤"})
    r = await client.get("/api/family/")
    assert r.status_code == 200
    assert len(r.json()) == 3
