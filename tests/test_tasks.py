"""Tests for /api/tasks endpoints."""
import pytest
from datetime import date, timedelta
from httpx import AsyncClient


TODAY = date.today().isoformat()
YESTERDAY = (date.today() - timedelta(days=1)).isoformat()
TOMORROW = (date.today() + timedelta(days=1)).isoformat()

TASK_BASE = {
    "title": "Boodschappen",
    "description": "",
    "done": False,
    "due_date": TODAY,
    "list_id": None,
    "member_id": None,
}

SERIES_BASE = {
    "title": "Dagelijkse taak",
    "description": "",
    "list_id": None,
    "member_id": None,
    "recurrence_type": "daily",
    "series_start": TODAY,
    "series_end": TOMORROW,
}


# ── Task Lists ────────────────────────────────────────────────────

async def test_list_task_lists_empty(client: AsyncClient):
    r = await client.get("/api/tasks/lists")
    assert r.status_code == 200
    assert r.json() == []


async def test_create_task_list(client: AsyncClient):
    r = await client.post("/api/tasks/lists", json={"name": "Huishouden", "color": "#FF6B6B"})
    assert r.status_code == 201
    data = r.json()
    assert data["name"] == "Huishouden"
    assert "id" in data


async def test_create_task_list_name_required(client: AsyncClient):
    r = await client.post("/api/tasks/lists", json={"name": "", "color": "#FF6B6B"})
    assert r.status_code == 422


async def test_update_task_list(client: AsyncClient):
    created = (await client.post("/api/tasks/lists", json={"name": "Taken", "color": "#AAAAAA"})).json()
    r = await client.put(f"/api/tasks/lists/{created['id']}", json={"name": "Taken bijgewerkt", "color": "#BBBBBB"})
    assert r.status_code == 200
    assert r.json()["name"] == "Taken bijgewerkt"


async def test_update_task_list_not_found(client: AsyncClient):
    r = await client.put("/api/tasks/lists/9999", json={"name": "X", "color": "#000000"})
    assert r.status_code == 404


async def test_delete_task_list(client: AsyncClient):
    created = (await client.post("/api/tasks/lists", json={"name": "Tijdelijk", "color": "#FFFFFF"})).json()
    r = await client.delete(f"/api/tasks/lists/{created['id']}")
    assert r.status_code == 204


async def test_delete_task_list_not_found(client: AsyncClient):
    r = await client.delete("/api/tasks/lists/9999")
    assert r.status_code == 404


# ── Tasks CRUD ────────────────────────────────────────────────────

async def test_list_tasks_empty(client: AsyncClient):
    r = await client.get("/api/tasks/")
    assert r.status_code == 200
    assert r.json() == []


async def test_create_task(client: AsyncClient):
    r = await client.post("/api/tasks/", json=TASK_BASE)
    assert r.status_code == 201
    data = r.json()
    assert data["title"] == "Boodschappen"
    assert data["done"] is False
    assert "id" in data


async def test_create_task_title_required(client: AsyncClient):
    r = await client.post("/api/tasks/", json={**TASK_BASE, "title": ""})
    assert r.status_code == 422


async def test_get_task(client: AsyncClient):
    created = (await client.post("/api/tasks/", json=TASK_BASE)).json()
    r = await client.get(f"/api/tasks/{created['id']}")
    assert r.status_code == 200
    assert r.json()["title"] == "Boodschappen"


async def test_get_task_not_found(client: AsyncClient):
    r = await client.get("/api/tasks/9999")
    assert r.status_code == 404


async def test_update_task(client: AsyncClient):
    created = (await client.post("/api/tasks/", json=TASK_BASE)).json()
    r = await client.put(f"/api/tasks/{created['id']}", json={**TASK_BASE, "title": "Aangepast"})
    assert r.status_code == 200
    assert r.json()["title"] == "Aangepast"


async def test_update_task_not_found(client: AsyncClient):
    r = await client.put("/api/tasks/9999", json=TASK_BASE)
    assert r.status_code == 404


async def test_toggle_task(client: AsyncClient):
    created = (await client.post("/api/tasks/", json=TASK_BASE)).json()
    task_id = created["id"]
    assert created["done"] is False
    r = await client.patch(f"/api/tasks/{task_id}/toggle")
    assert r.status_code == 200
    assert r.json()["done"] is True
    r2 = await client.patch(f"/api/tasks/{task_id}/toggle")
    assert r2.json()["done"] is False


async def test_toggle_task_not_found(client: AsyncClient):
    r = await client.patch("/api/tasks/9999/toggle")
    assert r.status_code == 404


async def test_delete_task(client: AsyncClient):
    created = (await client.post("/api/tasks/", json=TASK_BASE)).json()
    r = await client.delete(f"/api/tasks/{created['id']}")
    assert r.status_code == 204
    assert (await client.get(f"/api/tasks/{created['id']}")).status_code == 404


async def test_delete_task_not_found(client: AsyncClient):
    r = await client.delete("/api/tasks/9999")
    assert r.status_code == 404


# ── Task filters ──────────────────────────────────────────────────

async def test_list_tasks_filter_done(client: AsyncClient):
    await client.post("/api/tasks/", json=TASK_BASE)
    created2 = (await client.post("/api/tasks/", json={**TASK_BASE, "title": "Taak 2"})).json()
    await client.patch(f"/api/tasks/{created2['id']}/toggle")

    r_undone = await client.get("/api/tasks/", params={"done": "false"})
    assert all(not t["done"] for t in r_undone.json())

    r_done = await client.get("/api/tasks/", params={"done": "true"})
    assert all(t["done"] for t in r_done.json())


async def test_today_tasks(client: AsyncClient):
    await client.post("/api/tasks/", json={**TASK_BASE, "due_date": TODAY})
    await client.post("/api/tasks/", json={**TASK_BASE, "title": "Andere dag", "due_date": TOMORROW})
    r = await client.get("/api/tasks/today")
    assert r.status_code == 200
    titles = [t["title"] for t in r.json()]
    assert "Boodschappen" in titles
    assert "Andere dag" not in titles


async def test_overdue_tasks(client: AsyncClient):
    await client.post("/api/tasks/", json={**TASK_BASE, "due_date": YESTERDAY})
    await client.post("/api/tasks/", json={**TASK_BASE, "title": "Vandaag", "due_date": TODAY})
    r = await client.get("/api/tasks/overdue")
    assert r.status_code == 200
    data = r.json()
    assert any(t["due_date"] == YESTERDAY for t in data)
    assert all(t["due_date"] < TODAY for t in data)


# ── Recurrence series ─────────────────────────────────────────────

async def test_create_task_series_generates_tasks(client: AsyncClient):
    r = await client.post("/api/tasks/series", json=SERIES_BASE)
    assert r.status_code == 201
    series_id = r.json()["id"]
    tasks = (await client.get("/api/tasks/", params={"due_date": TODAY})).json()
    assert any(t["series_id"] == series_id for t in tasks)


async def test_create_task_series_end_before_start_rejected(client: AsyncClient):
    bad = {**SERIES_BASE, "series_start": TOMORROW, "series_end": TODAY}
    r = await client.post("/api/tasks/series", json=bad)
    assert r.status_code == 422


async def test_get_task_series(client: AsyncClient):
    created = (await client.post("/api/tasks/series", json=SERIES_BASE)).json()
    r = await client.get(f"/api/tasks/series/{created['id']}")
    assert r.status_code == 200
    assert r.json()["title"] == SERIES_BASE["title"]


async def test_get_task_series_not_found(client: AsyncClient):
    r = await client.get("/api/tasks/series/9999")
    assert r.status_code == 404


async def test_update_task_series(client: AsyncClient):
    next_week = (date.today() + timedelta(days=7)).isoformat()
    series_payload = {**SERIES_BASE, "series_end": next_week}
    created = (await client.post("/api/tasks/series", json=series_payload)).json()
    series_id = created["id"]

    r = await client.put(f"/api/tasks/series/{series_id}", json={**series_payload, "title": "Bijgewerkte reeks"})
    assert r.status_code == 200
    assert r.json()["title"] == "Bijgewerkte reeks"


async def test_delete_task_series_removes_tasks(client: AsyncClient):
    created = (await client.post("/api/tasks/series", json=SERIES_BASE)).json()
    series_id = created["id"]

    r = await client.delete(f"/api/tasks/series/{series_id}")
    assert r.status_code == 204

    tasks = (await client.get("/api/tasks/")).json()
    assert all(t["series_id"] != series_id for t in tasks)


async def test_edit_single_task_in_series_marks_exception(client: AsyncClient):
    next_week = (date.today() + timedelta(days=7)).isoformat()
    created_series = (await client.post("/api/tasks/series", json={**SERIES_BASE, "series_end": next_week})).json()
    series_id = created_series["id"]

    tasks = (await client.get("/api/tasks/", params={"due_date": TODAY})).json()
    task_id = next(t["id"] for t in tasks if t["series_id"] == series_id)

    r = await client.put(f"/api/tasks/{task_id}", json={**TASK_BASE, "title": "Uitzondering"})
    assert r.status_code == 200
    updated = r.json()
    assert updated["is_exception"] is True
    assert updated["series_id"] == series_id
