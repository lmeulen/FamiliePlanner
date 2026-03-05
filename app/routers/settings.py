"""API router for application settings."""
from fastapi import APIRouter, Depends
from loguru import logger
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth import get_auth_required, set_auth_required
from app.database import get_db
from app.models.settings import AppSetting

router = APIRouter(prefix="/api/settings", tags=["settings"])

# Keys managed by this router
_KEYS = {"auth_required", "dashboard_photo_height", "theme"}


async def _get(db: AsyncSession, key: str, default: str) -> str:
    row = await db.get(AppSetting, key)
    return row.value if row else default


async def _set(db: AsyncSession, key: str, value: str) -> None:
    row = await db.get(AppSetting, key)
    if row:
        row.value = value
    else:
        db.add(AppSetting(key=key, value=value))
    await db.commit()


@router.get("/", response_model=dict)
async def get_settings(db: AsyncSession = Depends(get_db)):
    return {
        "auth_required": (await _get(db, "auth_required", str(get_auth_required()))).lower() in ("1", "true"),
        "dashboard_photo_height": int(await _get(db, "dashboard_photo_height", "35")),
        "theme": await _get(db, "theme", "system"),
    }


@router.put("/", response_model=dict)
async def update_settings(payload: dict, db: AsyncSession = Depends(get_db)):
    if "auth_required" in payload:
        val = bool(payload["auth_required"])
        await _set(db, "auth_required", str(val).lower())
        set_auth_required(val)

    if "dashboard_photo_height" in payload:
        h = max(10, min(80, int(payload["dashboard_photo_height"])))
        await _set(db, "dashboard_photo_height", str(h))

    if "theme" in payload:
        t = payload["theme"] if payload["theme"] in ("light", "dark", "system") else "system"
        await _set(db, "theme", t)

    logger.info("settings.updated payload={}", {k: v for k, v in payload.items() if k in _KEYS})
    return await get_settings(db)
