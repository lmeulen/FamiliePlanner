"""Background worker that drains the Google Calendar sync queue."""

from __future__ import annotations

import asyncio

from loguru import logger

from app.database import AsyncSessionLocal
from app.services.google_calendar import GoogleCalendarNotConfigured
from app.services.google_sync import get_google_config, process_queue, reconcile
from app.utils.timezone import now_local

QUEUE_INTERVAL_SECONDS = 60
RECONCILE_HOUR = 1  # local time, after the midnight backup


async def _drain_queue() -> None:
    async with AsyncSessionLocal() as db:
        config = await get_google_config(db)
        if not config.usable:
            return

        result = await process_queue(db)
        if result.processed or result.failed:
            logger.info(
                "Google Calendar sync cycle completed.",
                processed=result.processed,
                created=result.created,
                updated=result.updated,
                deleted=result.deleted,
                unchanged=result.unchanged,
                failed=result.failed,
                skipped=result.skipped,
            )


async def _reconcile() -> None:
    async with AsyncSessionLocal() as db:
        config = await get_google_config(db)
        if not config.usable:
            return
        await reconcile(db)


async def run_google_sync_scheduler(stop_event: asyncio.Event) -> None:
    """Drain the queue every minute and reconcile once a day at 01:00."""
    logger.info(
        "Google Calendar sync scheduler started.",
        interval_seconds=QUEUE_INTERVAL_SECONDS,
        reconcile_hour=RECONCILE_HOUR,
    )

    last_reconcile_date = now_local().date()

    while not stop_event.is_set():
        try:
            await asyncio.wait_for(stop_event.wait(), timeout=QUEUE_INTERVAL_SECONDS)
            break
        except TimeoutError:
            pass

        try:
            await _drain_queue()
        except GoogleCalendarNotConfigured as exc:
            logger.warning("Google Calendar sync is enabled but not configured.", reason=str(exc))
        except Exception:
            logger.exception("Google Calendar sync cycle failed; will retry on the next cycle.")

        now = now_local()
        if now.hour == RECONCILE_HOUR and now.date() != last_reconcile_date:
            last_reconcile_date = now.date()
            try:
                await _reconcile()
            except Exception:
                logger.exception("Google Calendar reconciliation failed.")

    logger.info("Google Calendar sync scheduler stopped.")
