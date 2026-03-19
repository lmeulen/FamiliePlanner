"""Tests for Mealie recipe integration."""

from unittest.mock import AsyncMock, patch

import pytest
from httpx import AsyncClient


@pytest.fixture
async def setup_mealie_config(client: AsyncClient):
    """Setup Mealie server URL and API token in settings."""
    await client.put(
        "/api/settings/",
        json={
            "mealie_server_url": "http://mealie-test:9000",
            "mealie_api_token": "test-token-123",
        },
    )


# ── Configuration Tests ──────────────────────────────────────────


async def test_settings_store_mealie_config(client: AsyncClient):
    """Test that Mealie settings can be stored and retrieved."""
    resp = await client.put(
        "/api/settings/",
        json={
            "mealie_server_url": "http://localhost:9000",
            "mealie_api_token": "my-secret-token",
        },
    )
    assert resp.status_code == 200

    resp = await client.get("/api/settings/")
    assert resp.status_code == 200
    settings = resp.json()
    assert settings["mealie_server_url"] == "http://localhost:9000"
    assert settings["mealie_api_token"] == "my-secret-token"


async def test_settings_validate_url_format(client: AsyncClient):
    """Test that Mealie URL must start with http:// or https://."""
    # Invalid URL
    resp = await client.put(
        "/api/settings/",
        json={"mealie_server_url": "mealie-server:9000", "mealie_api_token": "token"},
    )
    assert resp.status_code == 400

    # Valid URLs
    for valid_url in ["http://localhost:9000", "https://mealie.example.com"]:
        resp = await client.put(
            "/api/settings/",
            json={"mealie_server_url": valid_url, "mealie_api_token": "token"},
        )
        assert resp.status_code == 200


# ── List Recipes Tests ───────────────────────────────────────────


@patch("app.routers.recipes._mealie_request")
async def test_list_recipes_success(mock_request, client: AsyncClient, setup_mealie_config):
    """Test listing recipes from Mealie."""
    mock_request.return_value = {
        "page": 1,
        "per_page": 50,
        "total": 2,
        "total_pages": 1,
        "items": [
            {
                "id": "recipe-1",
                "slug": "spaghetti-carbonara",
                "name": "Spaghetti Carbonara",
                "description": "Classic Italian pasta",
                "image": None,
                "recipeCategory": ["Italian"],
                "tags": ["easy"],
                "rating": 5,
                "dateAdded": "2024-01-01T10:00:00",
            },
        ],
    }

    resp = await client.get("/api/recipes/")
    assert resp.status_code == 200
    data = resp.json()
    assert data["page"] == 1
    assert len(data["items"]) == 1


async def test_list_recipes_missing_config(client: AsyncClient):
    """Test listing recipes without Mealie configuration."""
    resp = await client.get("/api/recipes/")
    assert resp.status_code == 503


# ── Get Single Recipe Tests ──────────────────────────────────────


@patch("app.routers.recipes._mealie_request")
async def test_get_recipe_success(mock_request, client: AsyncClient, setup_mealie_config):
    """Test getting a single recipe by slug."""
    mock_request.return_value = {
        "id": "recipe-1",
        "slug": "spaghetti-carbonara",
        "name": "Spaghetti Carbonara",
        "prepTime": "PT15M",
        "recipeIngredient": [],
        "recipeInstructions": [],
    }

    resp = await client.get("/api/recipes/spaghetti-carbonara")
    assert resp.status_code == 200
    recipe = resp.json()
    assert recipe["slug"] == "spaghetti-carbonara"


# ── Create Recipe Tests ──────────────────────────────────────────


@patch("app.routers.recipes._mealie_request")
async def test_create_recipe_success(mock_request, client: AsyncClient, setup_mealie_config):
    """Test creating a new recipe."""
    mock_request.return_value = {
        "id": "new-recipe-id",
        "slug": "my-new-recipe",
        "name": "My New Recipe",
    }

    resp = await client.post("/api/recipes/", json={"name": "My New Recipe"})
    assert resp.status_code == 201
    recipe = resp.json()
    assert recipe["slug"] == "my-new-recipe"


async def test_create_recipe_validation(client: AsyncClient, setup_mealie_config):
    """Test that recipe name is required."""
    resp = await client.post("/api/recipes/", json={})
    assert resp.status_code == 422


# ── Update Recipe Tests ──────────────────────────────────────────


@patch("app.routers.recipes._mealie_request")
async def test_update_recipe_success(mock_request, client: AsyncClient, setup_mealie_config):
    """Test updating an existing recipe."""
    mock_request.return_value = {
        "id": "recipe-1",
        "slug": "spaghetti-carbonara",
        "name": "Spaghetti Carbonara Updated",
    }

    payload = {"name": "Spaghetti Carbonara Updated", "description": "Updated"}
    resp = await client.put("/api/recipes/spaghetti-carbonara", json=payload)
    assert resp.status_code == 200
    recipe = resp.json()
    assert recipe["name"] == "Spaghetti Carbonara Updated"


# ── Delete Recipe Tests ──────────────────────────────────────────


@patch("app.routers.recipes._mealie_request")
async def test_delete_recipe_success(mock_request, client: AsyncClient, setup_mealie_config):
    """Test deleting a recipe."""
    mock_request.return_value = None

    resp = await client.delete("/api/recipes/spaghetti-carbonara")
    assert resp.status_code == 204


# ── Categories and Tags Tests ────────────────────────────────────


@patch("app.routers.recipes._mealie_request")
async def test_list_categories(mock_request, client: AsyncClient, setup_mealie_config):
    """Test listing recipe categories."""
    mock_request.return_value = [
        {"name": "Italian", "id": "cat-1"},
        {"name": "Asian", "id": "cat-2"},
    ]

    resp = await client.get("/api/recipes/categories/all")
    assert resp.status_code == 200
    categories = resp.json()
    assert len(categories) == 2
    assert "Italian" in categories


@patch("app.routers.recipes._mealie_request")
async def test_list_tags(mock_request, client: AsyncClient, setup_mealie_config):
    """Test listing recipe tags."""
    mock_request.return_value = [
        {"name": "vegetarian", "id": "tag-1"},
        {"name": "quick", "id": "tag-2"},
    ]

    resp = await client.get("/api/recipes/tags/all")
    assert resp.status_code == 200
    tags = resp.json()
    assert len(tags) == 2
    assert "vegetarian" in tags
