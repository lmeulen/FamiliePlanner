"""API endpoints for the one-way Google Calendar sync."""

from fastapi import APIRouter, Depends, HTTPException, Query
from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.services.google_calendar import (
    GoogleCalendarClient,
    GoogleCalendarError,
    GoogleCalendarNotConfigured,
)
from app.services.google_sync import (
    enqueue_all,
    ensure_member_colors,
    get_google_config,
    process_queue,
    purge_calendar,
    reconcile,
    sync_status,
)
from app.utils.google_colors import GOOGLE_COLOR_NAMES, GOOGLE_EVENT_COLORS

router = APIRouter(prefix="/api/google", tags=["google"])


@router.get("/status")
async def status(db: AsyncSession = Depends(get_db)):
    return await sync_status(db)


@router.get("/colors")
async def colors(db: AsyncSession = Depends(get_db)):
    """Available Google colours plus the current member assignment."""
    mapping = await ensure_member_colors(db)
    return {
        "palette": [
            {"id": cid, "name": GOOGLE_COLOR_NAMES[cid], "hex": chex} for cid, chex in GOOGLE_EVENT_COLORS.items()
        ],
        "members": mapping,
    }


@router.post("/test")
async def test_connection(db: AsyncSession = Depends(get_db)):
    """Verify credentials and calendar access without writing anything."""
    config = await get_google_config(db)
    if not config.calendar_id:
        raise HTTPException(400, "Er is nog geen Google Calendar ID opgeslagen. Vul het in en klik eerst op Opslaan.")

    try:
        info = await GoogleCalendarClient(config.calendar_id).verify()
    except GoogleCalendarNotConfigured as exc:
        raise HTTPException(400, str(exc)) from exc
    except GoogleCalendarError as exc:
        raise HTTPException(502, str(exc)) from exc
    except Exception as exc:
        logger.exception("Google Calendar connection test failed.")
        raise HTTPException(502, f"Verbinding met Google Calendar mislukt: {exc}") from exc

    return {"ok": True, **info}


@router.post("/backfill")
async def backfill(db: AsyncSession = Depends(get_db)):
    """Queue every event in the sync window for an initial push."""
    await ensure_member_colors(db)
    queued = await enqueue_all(db)
    logger.info("Google Calendar backfill queued.", queued=queued)
    return {"queued": queued}


@router.post("/sync")
async def sync_now(db: AsyncSession = Depends(get_db)):
    """Drain the queue immediately instead of waiting for the scheduler."""
    config = await get_google_config(db)
    reason = config.blocking_reason()
    if reason:
        raise HTTPException(400, reason)

    try:
        result = await process_queue(db)
    except GoogleCalendarNotConfigured as exc:
        raise HTTPException(400, str(exc)) from exc

    return {
        "processed": result.processed,
        "created": result.created,
        "updated": result.updated,
        "deleted": result.deleted,
        "unchanged": result.unchanged,
        "failed": result.failed,
        "skipped": result.skipped,
    }


@router.post("/reconcile")
async def reconcile_now(
    dry_run: bool = Query(False, description="Only report what would change"),
    db: AsyncSession = Depends(get_db),
):
    config = await get_google_config(db)
    reason = config.blocking_reason()
    if reason:
        raise HTTPException(400, reason)

    return await reconcile(db, dry_run=dry_run)


@router.delete("/events")
async def purge(db: AsyncSession = Depends(get_db)):
    """Remove every one-time and recurring event from the configured calendar."""
    try:
        removed = await purge_calendar(db)
    except GoogleCalendarNotConfigured as exc:
        raise HTTPException(400, str(exc)) from exc
    except GoogleCalendarError as exc:
        logger.warning("Google Calendar purge failed.", error=str(exc))
        raise HTTPException(502, str(exc)) from exc

    return {"removed": removed}
