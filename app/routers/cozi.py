"""API router for Cozi ICS synchronization."""

from fastapi import APIRouter, Depends, HTTPException
from loguru import logger
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import COZI_ICS_URL
from app.database import get_db
from app.models.agenda import AgendaEvent, RecurrenceSeries
from app.models.meals import Meal
from app.models.settings import AppSetting
from app.services.cozi_sync import classify_cozi_events, fetch_and_parse_cozi, import_selected_events

router = APIRouter(prefix="/api/cozi", tags=["cozi"])


async def _get_cozi_url(db: AsyncSession) -> str:
    """Return Cozi URL from DB setting, fall back to environment variable."""
    row = await db.get(AppSetting, "cozi_url")
    if row and row.value:
        return row.value
    return COZI_ICS_URL or ""


async def _get_link_item(db: AsyncSession, item_type: str, item_id: int):
    if item_type == "event":
        return await db.get(AgendaEvent, item_id), "Afspraak"
    if item_type == "series":
        return await db.get(RecurrenceSeries, item_id), "Reeks"
    if item_type == "meal":
        return await db.get(Meal, item_id), "Maaltijd"
    raise HTTPException(400, f"Ongeldig item type: {item_type}")


async def _resolve_link_target(db: AsyncSession, payload: "CoziLinkRequest"):
    item, label = await _get_link_item(db, payload.item_type, payload.item_id)
    if item is not None:
        return item, payload.item_type, label

    url = await _get_cozi_url(db)
    if not url:
        return None, payload.item_type, label

    events = await fetch_and_parse_cozi(url)
    event = next((candidate for candidate in events if candidate.uid == payload.cozi_uid), None)
    if event is None:
        return None, payload.item_type, label

    preview_items = await classify_cozi_events([event], db)
    if not preview_items:
        return None, payload.item_type, label

    preview = preview_items[0]
    if not preview.matched_fp_id or not preview.matched_fp_type:
        return None, payload.item_type, label

    item, label = await _get_link_item(db, preview.matched_fp_type, preview.matched_fp_id)
    return item, preview.matched_fp_type, label


@router.get("/preview")
async def cozi_preview(db: AsyncSession = Depends(get_db)):
    """Fetch Cozi feed and classify each event vs existing FamiliePlanner data."""
    url = await _get_cozi_url(db)
    if not url:
        raise HTTPException(
            400,
            "Geen Cozi ICS URL geconfigureerd. Voer deze in via Instellingen → Cozi Synchronisatie.",
        )

    try:
        events = await fetch_and_parse_cozi(url)
    except Exception as exc:
        logger.warning("cozi.preview.fetch_failed url={} error={}", url, exc)
        raise HTTPException(502, f"Kon Cozi feed niet ophalen: {exc}") from exc

    preview = await classify_cozi_events(events, db)
    logger.info("cozi.preview.done url={} total={}", url, len(preview))
    return [item.to_dict() for item in preview]


class CoziImportRequest(BaseModel):
    selected_uids: list[str]
    default_series_count: int = 60


@router.post("/import")
async def cozi_import(payload: CoziImportRequest, db: AsyncSession = Depends(get_db)):
    """Import selected Cozi events into FamiliePlanner."""
    url = await _get_cozi_url(db)
    if not url:
        raise HTTPException(400, "Geen Cozi ICS URL geconfigureerd.")

    if not payload.selected_uids:
        return {
            "imported_events": 0, "imported_series": 0, "imported_meals": 0,
            "updated_events": 0, "updated_series": 0, "updated_meals": 0,
            "skipped": 0,
        }

    series_count = max(1, min(365, payload.default_series_count))

    try:
        result = await import_selected_events(payload.selected_uids, db, url, series_count)
    except Exception as exc:
        logger.error("cozi.import.failed error={}", exc)
        raise HTTPException(502, f"Importeren mislukt: {exc}") from exc

    return {
        "imported_events": result.imported_events,
        "imported_series": result.imported_series,
        "imported_meals": result.imported_meals,
        "updated_events": result.updated_events,
        "updated_series": result.updated_series,
        "updated_meals": result.updated_meals,
        "skipped": result.skipped,
    }


class CoziLinkRequest(BaseModel):
    """Link an existing FamiliePlanner item to a Cozi UID."""

    cozi_uid: str
    item_type: str  # 'event', 'series', or 'meal'
    item_id: int


@router.post("/link")
async def cozi_link(payload: CoziLinkRequest, db: AsyncSession = Depends(get_db)):
    """Associate an existing FamiliePlanner item with a Cozi UID."""
    item, resolved_type, label = await _resolve_link_target(db, payload)
    if not item:
        raise HTTPException(404, f"{label} niet gevonden")

    item.cozi_uid = payload.cozi_uid

    await db.commit()
    logger.info(
        "cozi.link.done item_type={} item_id={} cozi_uid={}",
        resolved_type,
        item.id,
        payload.cozi_uid,
    )
    return {"status": "ok", "message": f"{resolved_type} gekoppeld aan Cozi"}
