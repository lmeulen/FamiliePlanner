"""Tests for /api/meals endpoints."""

from datetime import date, timedelta

from httpx import AsyncClient

TODAY = date.today().isoformat()
TOMORROW = (date.today() + timedelta(days=1)).isoformat()

MEAL_BASE = {
    "date": TODAY,
    "meal_type": "dinner",
    "name": "Pasta Bolognese",
    "description": "Klassiek Italiaans gerecht",
    "recipe_url": "",
    "cook_member_id": None,
}


async def test_list_meals_empty(client: AsyncClient):
    r = await client.get("/api/meals/")
    assert r.status_code == 200
    assert r.json() == []


async def test_create_meal(client: AsyncClient):
    r = await client.post("/api/meals/", json=MEAL_BASE)
    assert r.status_code == 201
    data = r.json()
    assert data["name"] == "Pasta Bolognese"
    assert data["meal_type"] == "dinner"
    assert "id" in data


async def test_create_meal_name_required(client: AsyncClient):
    r = await client.post("/api/meals/", json={**MEAL_BASE, "name": ""})
    assert r.status_code == 422


async def test_create_meal_invalid_recipe_url(client: AsyncClient):
    r = await client.post("/api/meals/", json={**MEAL_BASE, "recipe_url": "not-a-url"})
    assert r.status_code == 422


async def test_create_meal_valid_recipe_url(client: AsyncClient):
    r = await client.post("/api/meals/", json={**MEAL_BASE, "recipe_url": "https://example.com/recipe"})
    assert r.status_code == 201
    assert r.json()["recipe_url"] == "https://example.com/recipe"


async def test_get_meal(client: AsyncClient):
    created = (await client.post("/api/meals/", json=MEAL_BASE)).json()
    r = await client.get(f"/api/meals/{created['id']}")
    assert r.status_code == 200
    assert r.json()["name"] == "Pasta Bolognese"


async def test_get_meal_not_found(client: AsyncClient):
    r = await client.get("/api/meals/9999")
    assert r.status_code == 404


async def test_update_meal(client: AsyncClient):
    created = (await client.post("/api/meals/", json=MEAL_BASE)).json()
    r = await client.put(f"/api/meals/{created['id']}", json={**MEAL_BASE, "name": "Lasagne"})
    assert r.status_code == 200
    assert r.json()["name"] == "Lasagne"


async def test_update_meal_not_found(client: AsyncClient):
    r = await client.put("/api/meals/9999", json=MEAL_BASE)
    assert r.status_code == 404


async def test_delete_meal(client: AsyncClient):
    created = (await client.post("/api/meals/", json=MEAL_BASE)).json()
    r = await client.delete(f"/api/meals/{created['id']}")
    assert r.status_code == 204
    assert (await client.get(f"/api/meals/{created['id']}")).status_code == 404


async def test_delete_meal_not_found(client: AsyncClient):
    r = await client.delete("/api/meals/9999")
    assert r.status_code == 404


async def test_list_meals_date_filter(client: AsyncClient):
    await client.post("/api/meals/", json=MEAL_BASE)
    await client.post("/api/meals/", json={**MEAL_BASE, "date": TOMORROW, "name": "Soep"})

    r = await client.get("/api/meals/", params={"start": TODAY, "end": TODAY})
    assert r.status_code == 200
    data = r.json()
    assert len(data) == 1
    assert data[0]["name"] == "Pasta Bolognese"


async def test_list_meals_type_filter(client: AsyncClient):
    await client.post("/api/meals/", json=MEAL_BASE)
    await client.post("/api/meals/", json={**MEAL_BASE, "meal_type": "lunch", "name": "Broodje"})

    r = await client.get("/api/meals/", params={"meal_type": "lunch"})
    assert r.status_code == 200
    data = r.json()
    assert all(m["meal_type"] == "lunch" for m in data)


async def test_today_meals(client: AsyncClient):
    await client.post("/api/meals/", json=MEAL_BASE)
    r = await client.get("/api/meals/today")
    assert r.status_code == 200
    assert isinstance(r.json(), list)


async def test_week_meals(client: AsyncClient):
    await client.post("/api/meals/", json=MEAL_BASE)
    r = await client.get("/api/meals/week")
    assert r.status_code == 200
    assert isinstance(r.json(), list)


async def test_invalid_meal_type(client: AsyncClient):
    r = await client.post("/api/meals/", json={**MEAL_BASE, "meal_type": "brunch"})
    assert r.status_code == 422
