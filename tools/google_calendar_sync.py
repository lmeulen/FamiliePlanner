"""Manage the one-way Google Calendar sync from the command line.

Usage:
    python -m tools.google_calendar_sync --status
    python -m tools.google_calendar_sync --backfill
    python -m tools.google_calendar_sync --sync
    python -m tools.google_calendar_sync --reconcile --dry-run
    python -m tools.google_calendar_sync --purge
"""

from __future__ import annotations

import argparse
import asyncio

from app.database import AsyncSessionLocal
from app.services.google_calendar import GoogleCalendarClient, GoogleCalendarError
from app.services.google_sync import (
    enqueue_all,
    ensure_member_colors,
    get_google_config,
    process_queue,
    purge_remote,
    reconcile,
    sync_status,
)
from app.utils.google_colors import GOOGLE_COLOR_NAMES


async def _status() -> int:
    async with AsyncSessionLocal() as db:
        status = await sync_status(db)
        for key, value in status.items():
            if key != "errors":
                print(f"{key:<22}: {value}")
        if status["errors"]:
            print("\nFouten:")
            for err in status["errors"]:
                print(f"  {err['entity']} (pogingen: {err['attempts']}) - {err['error']}")
    return 0


async def _test() -> int:
    async with AsyncSessionLocal() as db:
        config = await get_google_config(db)
        if not config.calendar_id:
            print("Geen Google Calendar ID ingesteld.")
            return 1
        try:
            info = await GoogleCalendarClient(config.calendar_id).verify()
        except GoogleCalendarError as exc:
            print(f"Verbinding mislukt: {exc}")
            return 1
    print(f"Verbonden met agenda: {info['summary'] or info['calendar_id']}")
    return 0


async def _colors() -> int:
    async with AsyncSessionLocal() as db:
        mapping = await ensure_member_colors(db)
    for member_id, color_id in sorted(mapping.items(), key=lambda kv: int(kv[0])):
        print(f"  lid {member_id:<4} -> {color_id:<3} {GOOGLE_COLOR_NAMES.get(color_id, '?')}")
    return 0


async def _backfill() -> int:
    async with AsyncSessionLocal() as db:
        await ensure_member_colors(db)
        queued = await enqueue_all(db)
    print(f"{queued} items in de wachtrij gezet.")
    return 0


async def _sync() -> int:
    async with AsyncSessionLocal() as db:
        config = await get_google_config(db)
        if not config.usable:
            print("Google sync is niet ingeschakeld of niet geconfigureerd.")
            return 1
        result = await process_queue(db)
    print(
        f"Verwerkt: {result.processed} (nieuw {result.created}, bijgewerkt {result.updated}, "
        f"verwijderd {result.deleted}, ongewijzigd {result.unchanged}, mislukt {result.failed})"
    )
    return 0


async def _reconcile(dry_run: bool) -> int:
    async with AsyncSessionLocal() as db:
        result = await reconcile(db, dry_run=dry_run)
    print(result)
    return 0


async def _purge(force: bool) -> int:
    if not force:
        answer = input("Alle FamiliePlanner events uit Google Calendar verwijderen? [ja/nee] ")
        if answer.strip().lower() not in ("ja", "j", "yes", "y"):
            print("Geannuleerd.")
            return 1

    async with AsyncSessionLocal() as db:
        removed = await purge_remote(db)
    print(f"{removed} events verwijderd uit Google Calendar.")
    return 0


def main() -> None:
    parser = argparse.ArgumentParser(description="Beheer de Google Calendar sync")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--status", action="store_true", help="Toon sync status")
    group.add_argument("--test", action="store_true", help="Test de verbinding met Google Calendar")
    group.add_argument("--colors", action="store_true", help="Toon/genereer kleurtoewijzing per gezinslid")
    group.add_argument("--backfill", action="store_true", help="Zet alle events in de wachtrij")
    group.add_argument("--sync", action="store_true", help="Verwerk de wachtrij nu")
    group.add_argument("--reconcile", action="store_true", help="Vergelijk en herstel verschillen")
    group.add_argument("--purge", action="store_true", help="Verwijder alle events uit Google Calendar")
    parser.add_argument("--dry-run", action="store_true", help="Alleen tonen wat er zou gebeuren")
    parser.add_argument("--force", action="store_true", help="Sla bevestiging over bij --purge")
    args = parser.parse_args()

    if args.status:
        code = asyncio.run(_status())
    elif args.test:
        code = asyncio.run(_test())
    elif args.colors:
        code = asyncio.run(_colors())
    elif args.backfill:
        code = asyncio.run(_backfill())
    elif args.sync:
        code = asyncio.run(_sync())
    elif args.reconcile:
        code = asyncio.run(_reconcile(args.dry_run))
    else:
        code = asyncio.run(_purge(args.force))

    raise SystemExit(code)


if __name__ == "__main__":
    main()
