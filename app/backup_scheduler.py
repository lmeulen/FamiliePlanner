"""Nightly backup scheduler.

Creates a backup file every night at 00:00 in backups/DDMMYYYY.json.
"""

from __future__ import annotations

import asyncio
import json
from datetime import datetime, timedelta
from pathlib import Path

from loguru import logger

from app.config import BASE_DIR
from app.database import AsyncSessionLocal
from app.routers.settings import export_backup_data

BACKUP_DIR = BASE_DIR / "backups"


def _seconds_until_next_midnight(now: datetime) -> float:
    next_midnight = datetime.combine(now.date() + timedelta(days=1), datetime.min.time())
    return max(1.0, (next_midnight - now).total_seconds())


async def _write_nightly_backup_file() -> Path:
    async with AsyncSessionLocal() as db:
        backup_data = await export_backup_data(db)

    BACKUP_DIR.mkdir(parents=True, exist_ok=True)
    file_name = datetime.now().strftime("%d%m%Y") + ".json"
    file_path = BACKUP_DIR / file_name

    json_content = json.dumps(backup_data, indent=2, ensure_ascii=False)
    await asyncio.to_thread(file_path.write_text, json_content, "utf-8")

    return file_path


async def create_backup_now() -> Path:
    """Create a backup file immediately using the same exporter and naming format."""
    return await _write_nightly_backup_file()


async def run_nightly_backup_scheduler(stop_event: asyncio.Event) -> None:
    """Run a loop that writes one backup every day at 00:00."""
    logger.info("nightly-backup.scheduler.started")

    while not stop_event.is_set():
        wait_seconds = _seconds_until_next_midnight(datetime.now())
        try:
            await asyncio.wait_for(stop_event.wait(), timeout=wait_seconds)
            break
        except TimeoutError:
            try:
                file_path = await _write_nightly_backup_file()
                logger.info("nightly-backup.completed file={}", file_path)
            except Exception as exc:  # noqa: BLE001
                logger.exception("nightly-backup.failed error={}", exc)

    logger.info("nightly-backup.scheduler.stopped")
