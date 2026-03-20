"""API router for Mealie recipe integration (proxy)."""

import httpx
from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile
from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.settings import AppSetting
from app.schemas.recipes import RecipeCreate, RecipeListResponse, RecipeOut, RecipeStub, RecipeUpdate

router = APIRouter(prefix="/api/recipes", tags=["recipes"])


async def _get_mealie_config(db: AsyncSession) -> tuple[str, str]:
    """Get Mealie server URL and API token from settings."""
    url_row = await db.get(AppSetting, "mealie_server_url")
    token_row = await db.get(AppSetting, "mealie_api_token")

    url = url_row.value.strip() if url_row else ""
    token = token_row.value.strip() if token_row else ""

    if not url:
        raise HTTPException(503, "Mealie server URL niet geconfigureerd. Ga naar Instellingen.")
    if not token:
        raise HTTPException(503, "Mealie API token niet geconfigureerd. Ga naar Instellingen.")

    return url, token


async def _mealie_request(method: str, url: str, token: str, path: str, **kwargs) -> dict | list | None:
    """Make authenticated request to Mealie API."""
    headers = {"Authorization": f"Bearer {token}"}
    if "headers" in kwargs:
        headers.update(kwargs["headers"])
    kwargs["headers"] = headers

    full_url = f"{url.rstrip('/')}/api{path}"

    async with httpx.AsyncClient(timeout=10.0) as client:
        try:
            response = await client.request(method, full_url, **kwargs)

            if response.status_code == 401:
                raise HTTPException(401, "Ongeldige Mealie API token. Controleer token in instellingen.")
            if response.status_code == 404:
                raise HTTPException(404, "Recept niet gevonden op Mealie server.")
            if response.status_code >= 400:
                raise HTTPException(response.status_code, f"Mealie API fout: {response.status_code}")

            if response.status_code == 204:
                return None

            return response.json()  # type: ignore[no-any-return]

        except httpx.TimeoutException as e:
            raise HTTPException(504, "Mealie server timeout - controleer of server bereikbaar is.") from e
        except httpx.ConnectError as e:
            raise HTTPException(503, "Kan geen verbinding maken met Mealie server - controleer URL.") from e
        except Exception as e:
            logger.error("mealie_request_failed method={} path={} error={}", method, path, str(e))
            raise HTTPException(500, f"Fout bij communicatie met Mealie: {str(e)}") from e


def _fix_image_url(mealie_url: str, image: str | None) -> str | None:
    """Convert relative Mealie image paths to absolute URLs."""
    if not image:
        return None
    if image.startswith("http://") or image.startswith("https://"):
        return image
    # Mealie returns either:
    # - short image ID like "zDeP" -> /api/media/recipes/{id}/images/min-original.webp
    # - full path like "/api/media/..."
    if image.startswith("/"):
        return f"{mealie_url.rstrip('/')}{image}"
    else:
        # Short image ID - construct full path
        return f"{mealie_url.rstrip('/')}/api/media/recipes/{image}/images/min-original.webp"


def _transform_recipe_images(mealie_url: str, data: dict | list) -> dict | list:
    """Transform image URLs in recipe data to absolute URLs."""
    if isinstance(data, list):
        return [_transform_recipe_images(mealie_url, item) for item in data]
    if isinstance(data, dict):
        if "image" in data:
            data["image"] = _fix_image_url(mealie_url, data.get("image"))
        if "items" in data and isinstance(data["items"], list):
            data["items"] = [_transform_recipe_images(mealie_url, item) for item in data["items"]]
    return data


@router.get("/", response_model=RecipeListResponse)
async def list_recipes(
    page: int = Query(1, ge=1),
    per_page: int = Query(50, ge=1, le=100),
    search: str | None = Query(None),
    tags: str | None = Query(None),  # comma-separated
    categories: str | None = Query(None),  # comma-separated
    db: AsyncSession = Depends(get_db),
):
    """List recipes with pagination, search, and filtering."""
    mealie_url, token = await _get_mealie_config(db)

    params = {
        "page": page,
        "perPage": per_page,
        "orderBy": "name",
        "orderDirection": "asc",
    }
    if search:
        params["search"] = search
    if tags:
        params["tags"] = tags
    if categories:
        params["categories"] = categories

    data = await _mealie_request("GET", mealie_url, token, "/recipes", params=params)

    # Transform image URLs to absolute
    if data is not None:
        data = _transform_recipe_images(mealie_url, data)

    # Transform Mealie response to our schema
    if isinstance(data, dict):
        return RecipeListResponse(
            page=data.get("page", page),
            per_page=data.get("per_page", per_page),
            total=data.get("total", 0),
            total_pages=data.get("total_pages", 0),
            items=data.get("items", []),
        )

    # Fallback for unexpected response
    return RecipeListResponse(page=page, per_page=per_page, total=0, total_pages=0, items=[])


@router.get("/{slug}", response_model=RecipeOut)
async def get_recipe(slug: str, db: AsyncSession = Depends(get_db)):
    """Get single recipe by slug."""
    mealie_url, token = await _get_mealie_config(db)
    data = await _mealie_request("GET", mealie_url, token, f"/recipes/{slug}")
    if data is not None:
        data = _transform_recipe_images(mealie_url, data)
    return data


@router.post("/", response_model=RecipeStub, status_code=201)
async def create_recipe(payload: RecipeCreate, db: AsyncSession = Depends(get_db)):
    """Create new recipe (returns stub with slug for subsequent PUT)."""
    mealie_url, token = await _get_mealie_config(db)
    data = await _mealie_request("POST", mealie_url, token, "/recipes", json=payload.model_dump())
    if data is not None:
        data = _transform_recipe_images(mealie_url, data)
    if isinstance(data, dict):
        logger.info("recipes.recipe.created slug={}", data.get("slug"))
    return data


@router.put("/{slug}", response_model=RecipeOut)
async def update_recipe(slug: str, payload: RecipeUpdate, db: AsyncSession = Depends(get_db)):
    """Update full recipe details."""
    mealie_url, token = await _get_mealie_config(db)

    # Convert category/tag names to full objects for Mealie
    update_data = payload.model_dump(exclude_unset=True)

    # Handle categories - convert names to objects
    if "recipeCategory" in update_data and update_data["recipeCategory"]:
        categories_data = await _mealie_request("GET", mealie_url, token, "/organizers/categories")
        if isinstance(categories_data, dict) and "items" in categories_data:
            category_map = {cat["slug"]: cat for cat in categories_data["items"]}
            # Match by slug or name
            matched_categories = []
            for cat_name in update_data["recipeCategory"]:
                slug_version = cat_name.lower().replace(" ", "-")
                if slug_version in category_map:
                    matched_categories.append(category_map[slug_version])
                else:
                    # Try to find by name
                    for cat in categories_data["items"]:
                        if cat["name"].lower() == cat_name.lower():
                            matched_categories.append(cat)
                            break
            update_data["recipeCategory"] = matched_categories

    # Handle tags - convert names to objects
    if "tags" in update_data and update_data["tags"]:
        tags_data = await _mealie_request("GET", mealie_url, token, "/organizers/tags")
        if isinstance(tags_data, dict) and "items" in tags_data:
            tag_map = {tag["slug"]: tag for tag in tags_data["items"]}
            matched_tags = []
            for tag_name in update_data["tags"]:
                slug_version = tag_name.lower().replace(" ", "-")
                if slug_version in tag_map:
                    matched_tags.append(tag_map[slug_version])
                else:
                    # Try to find by name
                    for tag in tags_data["items"]:
                        if tag["name"].lower() == tag_name.lower():
                            matched_tags.append(tag)
                            break
            update_data["tags"] = matched_tags

    data = await _mealie_request("PATCH", mealie_url, token, f"/recipes/{slug}", json=update_data)
    if data is not None:
        data = _transform_recipe_images(mealie_url, data)
    logger.info("recipes.recipe.updated slug={}", slug)
    return data


@router.patch("/{slug}", response_model=RecipeOut)
async def patch_recipe(slug: str, payload: dict, db: AsyncSession = Depends(get_db)):
    """Partial update of recipe."""
    mealie_url, token = await _get_mealie_config(db)
    data = await _mealie_request("PATCH", mealie_url, token, f"/recipes/{slug}", json=payload)
    if data is not None:
        data = _transform_recipe_images(mealie_url, data)
    logger.info("recipes.recipe.patched slug={}", slug)
    return data


@router.delete("/{slug}", status_code=204)
async def delete_recipe(slug: str, db: AsyncSession = Depends(get_db)):
    """Delete recipe."""
    mealie_url, token = await _get_mealie_config(db)
    await _mealie_request("DELETE", mealie_url, token, f"/recipes/{slug}")
    logger.info("recipes.recipe.deleted slug={}", slug)


@router.put("/{slug}/image")
async def upload_recipe_image(slug: str, file: UploadFile = File(...), db: AsyncSession = Depends(get_db)):
    """Upload recipe image to Mealie."""
    mealie_url, token = await _get_mealie_config(db)

    # Read file content
    content = await file.read()
    files = {"image": (file.filename, content, file.content_type)}

    data = await _mealie_request("PUT", mealie_url, token, f"/recipes/{slug}/image", files=files)
    if data:
        data = _transform_recipe_images(mealie_url, data)
    logger.info("recipes.recipe.image_uploaded slug={}", slug)
    return data


@router.get("/categories/all")
async def list_categories(db: AsyncSession = Depends(get_db)):
    """Get all available recipe categories with slugs for filtering."""
    mealie_url, token = await _get_mealie_config(db)
    try:
        data = await _mealie_request("GET", mealie_url, token, "/organizers/categories")
        # Return name and slug for each category
        if isinstance(data, dict) and "items" in data:
            return [{"name": cat["name"], "slug": cat["slug"]} for cat in data["items"]]
        return []
    except HTTPException as e:
        # If categories endpoint doesn't exist, return empty list
        logger.warning("categories_endpoint_failed status={} detail={}", e.status_code, e.detail)
        return []


@router.get("/tags/all")
async def list_tags(db: AsyncSession = Depends(get_db)):
    """Get all available recipe tags with slugs for filtering."""
    mealie_url, token = await _get_mealie_config(db)
    try:
        data = await _mealie_request("GET", mealie_url, token, "/organizers/tags")
        # Return name and slug for each tag
        if isinstance(data, dict) and "items" in data:
            return [{"name": tag["name"], "slug": tag["slug"]} for tag in data["items"]]
        return []
    except HTTPException as e:
        # If tags endpoint doesn't exist, return empty list
        logger.warning("tags_endpoint_failed status={} detail={}", e.status_code, e.detail)
        return []
