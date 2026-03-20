"""Tests for Mealie recipe integration."""

from unittest.mock import patch

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
    mock_request.return_value = {
        "page": 1,
        "per_page": 50,
        "total": 2,
        "items": [
            {"name": "Italian", "id": "cat-1", "slug": "italian"},
            {"name": "Asian", "id": "cat-2", "slug": "asian"},
        ],
    }

    resp = await client.get("/api/recipes/categories/all")
    assert resp.status_code == 200
    categories = resp.json()
    assert len(categories) == 2
    assert categories[0] == {"name": "Italian", "slug": "italian"}
    assert categories[1] == {"name": "Asian", "slug": "asian"}


@patch("app.routers.recipes._mealie_request")
async def test_list_tags(mock_request, client: AsyncClient, setup_mealie_config):
    """Test listing recipe tags."""
    mock_request.return_value = {
        "page": 1,
        "per_page": 50,
        "total": 2,
        "items": [
            {"name": "vegetarian", "id": "tag-1", "slug": "vegetarian"},
            {"name": "quick", "id": "tag-2", "slug": "quick"},
        ],
    }

    resp = await client.get("/api/recipes/tags/all")
    assert resp.status_code == 200
    tags = resp.json()
    assert len(tags) == 2
    assert tags[0] == {"name": "vegetarian", "slug": "vegetarian"}
    assert tags[1] == {"name": "quick", "slug": "quick"}


@patch("app.routers.recipes._mealie_request")
async def test_list_categories_graceful_failure(mock_request, client: AsyncClient, setup_mealie_config):
    """Test that categories endpoint returns empty list on error."""
    from fastapi import HTTPException

    mock_request.side_effect = HTTPException(404, "Not found")

    resp = await client.get("/api/recipes/categories/all")
    assert resp.status_code == 200
    categories = resp.json()
    assert categories == []


@patch("app.routers.recipes._mealie_request")
async def test_list_tags_graceful_failure(mock_request, client: AsyncClient, setup_mealie_config):
    """Test that tags endpoint returns empty list on error."""
    from fastapi import HTTPException

    mock_request.side_effect = HTTPException(404, "Not found")

    resp = await client.get("/api/recipes/tags/all")
    assert resp.status_code == 200
    tags = resp.json()
    assert tags == []


@patch("app.routers.recipes._mealie_request")
async def test_list_categories_empty(mock_request, client: AsyncClient, setup_mealie_config):
    """Test listing categories when none exist."""
    mock_request.return_value = {"page": 1, "per_page": 50, "total": 0, "items": []}

    resp = await client.get("/api/recipes/categories/all")
    assert resp.status_code == 200
    categories = resp.json()
    assert categories == []


@patch("app.routers.recipes._mealie_request")
async def test_list_tags_empty(mock_request, client: AsyncClient, setup_mealie_config):
    """Test listing tags when none exist."""
    mock_request.return_value = {"page": 1, "per_page": 50, "total": 0, "items": []}

    resp = await client.get("/api/recipes/tags/all")
    assert resp.status_code == 200
    tags = resp.json()
    assert tags == []


# ── Image URL Transformation Tests ───────────────────────────────


def test_fix_image_url_short_id():
    """Test image URL transformation with short ID."""
    from app.routers.recipes import _fix_image_url

    result = _fix_image_url("http://localhost:9000", "zDeP")
    assert result == "http://localhost:9000/api/media/recipes/zDeP/images/min-original.webp"


def test_fix_image_url_full_path():
    """Test image URL transformation with full path."""
    from app.routers.recipes import _fix_image_url

    result = _fix_image_url("http://localhost:9000", "/api/media/recipes/abc/images/original.webp")
    assert result == "http://localhost:9000/api/media/recipes/abc/images/original.webp"


def test_fix_image_url_absolute():
    """Test image URL transformation with absolute URL."""
    from app.routers.recipes import _fix_image_url

    result = _fix_image_url("http://localhost:9000", "http://example.com/image.jpg")
    assert result == "http://example.com/image.jpg"


def test_fix_image_url_none():
    """Test image URL transformation with None."""
    from app.routers.recipes import _fix_image_url

    result = _fix_image_url("http://localhost:9000", None)
    assert result is None


def test_transform_recipe_images_list():
    """Test transforming list of recipes."""
    from app.routers.recipes import _transform_recipe_images

    data = {
        "items": [
            {"name": "Recipe 1", "image": "zDeP"},
            {"name": "Recipe 2", "image": "/api/media/xyz.jpg"},
            {"name": "Recipe 3", "image": None},
        ]
    }

    result = _transform_recipe_images("http://localhost:9000", data)

    assert result["items"][0]["image"] == "http://localhost:9000/api/media/recipes/zDeP/images/min-original.webp"
    assert result["items"][1]["image"] == "http://localhost:9000/api/media/xyz.jpg"
    assert result["items"][2]["image"] is None


def test_transform_recipe_images_single():
    """Test transforming single recipe."""
    from app.routers.recipes import _transform_recipe_images

    data = {"name": "Test Recipe", "image": "abc123", "slug": "test-recipe"}

    result = _transform_recipe_images("http://localhost:9000", data)

    assert result["image"] == "http://localhost:9000/api/media/recipes/abc123/images/min-original.webp"
    assert result["name"] == "Test Recipe"
    assert result["slug"] == "test-recipe"


@patch("app.routers.recipes._mealie_request")
async def test_list_recipes_with_images(mock_request, client: AsyncClient, setup_mealie_config):
    """Test that recipe list transforms image URLs correctly."""
    mock_request.return_value = {
        "page": 1,
        "per_page": 50,
        "total": 2,
        "total_pages": 1,
        "items": [
            {
                "id": "recipe-1",
                "slug": "test-recipe-1",
                "name": "Test Recipe 1",
                "image": "zDeP",  # Short ID
                "description": "",
                "recipeCategory": [],
                "tags": [],
                "rating": None,
                "dateAdded": "2024-01-01T10:00:00",
            },
            {
                "id": "recipe-2",
                "slug": "test-recipe-2",
                "name": "Test Recipe 2",
                "image": None,  # No image
                "description": "",
                "recipeCategory": [],
                "tags": [],
                "rating": None,
                "dateAdded": "2024-01-01T10:00:00",
            },
        ],
    }

    resp = await client.get("/api/recipes/")
    assert resp.status_code == 200
    data = resp.json()

    # Check first recipe has transformed image URL
    assert "http://mealie-test:9000/api/media/recipes/zDeP/images/min-original.webp" in data["items"][0]["image"]

    # Check second recipe has None for image
    assert data["items"][1]["image"] is None


@patch("app.routers.recipes._mealie_request")
async def test_list_recipes_with_category_filter(mock_request, client: AsyncClient, setup_mealie_config):
    """Test that category filter passes slug to Mealie."""
    mock_request.return_value = {
        "page": 1,
        "per_page": 50,
        "total": 1,
        "total_pages": 1,
        "items": [
            {
                "id": "recipe-1",
                "slug": "italian-pasta",
                "name": "Italian Pasta",
                "image": None,
                "description": "",
                "recipeCategory": [{"name": "Italian"}],
                "tags": [],
                "rating": None,
                "dateAdded": "2024-01-01T10:00:00",
            }
        ],
    }

    resp = await client.get("/api/recipes/?categories=italian")
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] == 1

    # Verify the mock was called with correct params
    mock_request.assert_called_once()
    call_args = mock_request.call_args
    assert call_args[1]["params"]["categories"] == "italian"


@patch("app.routers.recipes._mealie_request")
async def test_list_recipes_with_tag_filter(mock_request, client: AsyncClient, setup_mealie_config):
    """Test that tag filter passes slug to Mealie."""
    mock_request.return_value = {
        "page": 1,
        "per_page": 50,
        "total": 1,
        "total_pages": 1,
        "items": [
            {
                "id": "recipe-1",
                "slug": "quick-meal",
                "name": "Quick Meal",
                "image": None,
                "description": "",
                "recipeCategory": [],
                "tags": [{"name": "quick"}],
                "rating": None,
                "dateAdded": "2024-01-01T10:00:00",
            }
        ],
    }

    resp = await client.get("/api/recipes/?tags=quick")
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] == 1

    # Verify the mock was called with correct params
    mock_request.assert_called_once()
    call_args = mock_request.call_args
    assert call_args[1]["params"]["tags"] == "quick"
