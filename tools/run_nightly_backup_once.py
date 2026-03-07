"""Run the nightly backup logic once, immediately.

Usage:
    python tools/run_nightly_backup_once.py
"""

from __future__ import annotations

import asyncio

from app.backup_scheduler import create_backup_now


async def _run() -> None:
    file_path = await create_backup_now()
    print(f"Backup created: {file_path}")


def main() -> None:
    asyncio.run(_run())


if __name__ == "__main__":
    main()
