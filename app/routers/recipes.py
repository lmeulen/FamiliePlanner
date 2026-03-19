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

            return response.json()

        except httpx.TimeoutException as e:
            raise HTTPException(504, "Mealie server timeout - controleer of server bereikbaar is.") from e
        except httpx.ConnectError as e:
            raise HTTPException(503, "Kan geen verbinding maken met Mealie server - controleer URL.") from e
        except Exception as e:
            logger.error("mealie_request_failed method={} path={} error={}", method, path, str(e))
            raise HTTPException(500, f"Fout bij communicatie met Mealie: {str(e)}") from e


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

    # Transform Mealie response to our schema
    return RecipeListResponse(
        page=data.get("page", page),
        per_page=data.get("per_page", per_page),
        total=data.get("total", 0),
        total_pages=data.get("total_pages", 0),
        items=data.get("items", []),
    )


@router.get("/{slug}", response_model=RecipeOut)
async def get_recipe(slug: str, db: AsyncSession = Depends(get_db)):
    """Get single recipe by slug."""
    mealie_url, token = await _get_mealie_config(db)
    data = await _mealie_request("GET", mealie_url, token, f"/recipes/{slug}")
    return data


@router.post("/", response_model=RecipeStub, status_code=201)
async def create_recipe(payload: RecipeCreate, db: AsyncSession = Depends(get_db)):
    """Create new recipe (returns stub with slug for subsequent PUT)."""
    mealie_url, token = await _get_mealie_config(db)
    data = await _mealie_request("POST", mealie_url, token, "/recipes", json=payload.model_dump())
    logger.info("recipes.recipe.created slug={}", data.get("slug"))
    return data


@router.put("/{slug}", response_model=RecipeOut)
async def update_recipe(slug: str, payload: RecipeUpdate, db: AsyncSession = Depends(get_db)):
    """Update full recipe details."""
    mealie_url, token = await _get_mealie_config(db)
    data = await _mealie_request(
        "PUT", mealie_url, token, f"/recipes/{slug}", json=payload.model_dump(exclude_unset=True)
    )
    logger.info("recipes.recipe.updated slug={}", slug)
    return data


@router.patch("/{slug}", response_model=RecipeOut)
async def patch_recipe(slug: str, payload: dict, db: AsyncSession = Depends(get_db)):
    """Partial update of recipe."""
    mealie_url, token = await _get_mealie_config(db)
    data = await _mealie_request("PATCH", mealie_url, token, f"/recipes/{slug}", json=payload)
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
    logger.info("recipes.recipe.image_uploaded slug={}", slug)
    return data


@router.get("/categories/all", response_model=list[str])
async def list_categories(db: AsyncSession = Depends(get_db)):
    """Get all available recipe categories."""
    mealie_url, token = await _get_mealie_config(db)
    data = await _mealie_request("GET", mealie_url, token, "/recipes/category")
    # Extract just category names from response
    return [cat["name"] for cat in data] if isinstance(data, list) else []


@router.get("/tags/all", response_model=list[str])
async def list_tags(db: AsyncSession = Depends(get_db)):
    """Get all available recipe tags."""
    mealie_url, token = await _get_mealie_config(db)
    data = await _mealie_request("GET", mealie_url, token, "/recipes/tags")
    return [tag["name"] for tag in data] if isinstance(data, list) else []
