"""Background scheduler for automatic Cozi synchronization."""

from __future__ import annotations

import asyncio

from loguru import logger

from app.database import AsyncSessionLocal
from app.services.cozi_sync import run_automatic_cozi_sync

COZI_SYNC_INTERVAL_SECONDS = 2 * 60 * 60


def _result_total(result) -> int:
    return (
        result.imported_events
        + result.imported_series
        + result.imported_meals
        + result.updated_events
        + result.updated_series
        + result.updated_meals
    )


async def _execute_automatic_cozi_sync() -> None:
    async with AsyncSessionLocal() as db:
        result = await run_automatic_cozi_sync(db)

    logger.info(
        "Automatic Cozi sync cycle completed.",
        total_processed=_result_total(result),
        imported_events=result.imported_events,
        imported_series=result.imported_series,
        imported_meals=result.imported_meals,
        updated_events=result.updated_events,
        updated_series=result.updated_series,
        updated_meals=result.updated_meals,
        skipped=result.skipped,
    )


async def run_cozi_sync_scheduler(stop_event: asyncio.Event) -> None:
    """Run automatic Cozi sync immediately and then every two hours."""
    logger.info(
        "Cozi sync scheduler started; first run executes immediately, then every two hours.",
        interval_seconds=COZI_SYNC_INTERVAL_SECONDS,
    )

    try:
        await _execute_automatic_cozi_sync()
    except Exception:
        logger.exception(
            "Automatic Cozi sync failed during the immediate startup run.",
            scheduler="cozi",
        )

    while not stop_event.is_set():
        try:
            await asyncio.wait_for(stop_event.wait(), timeout=COZI_SYNC_INTERVAL_SECONDS)
            break
        except TimeoutError:
            try:
                await _execute_automatic_cozi_sync()
            except Exception:
                logger.exception(
                    "Automatic Cozi sync failed during a scheduled run.",
                    scheduler="cozi",
                    next_attempt="next scheduled cycle",
                )

    logger.info("Cozi sync scheduler stopped.")