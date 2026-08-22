"""Repair agenda events imported before the Cozi timezone conversion fix.

Older imports stored ICS UTC timestamps verbatim, so events are shifted by the
UTC offset (2h in summer, 1h in winter for Europe/Amsterdam). This script
re-fetches the Cozi feed and corrects only those rows whose stored time differs
from the correct local time by exactly that offset.

Usage:
    python -m tools.fix_cozi_timezone_offset --dry-run
    python -m tools.fix_cozi_timezone_offset --apply
"""

from __future__ import annotations

import argparse
import asyncio
from datetime import datetime

from sqlalchemy import select

from app.config import BASE_DIR
from app.database import AsyncSessionLocal
from app.models.agenda import AgendaEvent
from app.services.cozi_sync import fetch_and_parse_cozi, get_configured_cozi_url
from app.utils.timezone import app_timezone_name, now_local, to_aware


def _utc_offset_hours(dt: datetime) -> float:
    offset = to_aware(dt).utcoffset()
    return offset.total_seconds() / 3600 if offset else 0.0


async def _run(apply_changes: bool, force: bool) -> int:
    backup_file = BASE_DIR / "backups" / (now_local().strftime("%d%m%Y") + ".json")
    if apply_changes and not backup_file.exists() and not force:
        print(f"Geen backup van vandaag gevonden ({backup_file.name}).")
        print("Draai eerst: python -m tools.run_nightly_backup_once   (of gebruik --force)")
        return 1

    async with AsyncSessionLocal() as db:
        url = await get_configured_cozi_url(db)
        if not url:
            print("Geen Cozi URL geconfigureerd.")
            return 1

        parsed = await fetch_and_parse_cozi(url)
        correct_by_uid = {p.uid: p for p in parsed if p.uid and not p.all_day}

        result = await db.execute(select(AgendaEvent).where(AgendaEvent.cozi_uid.isnot(None)))
        events = result.scalars().all()

        fixed = 0
        skipped_no_feed_match = 0
        skipped_other_diff = 0
        unchanged = 0

        for event in events:
            expected = correct_by_uid.get(event.cozi_uid or "")
            if expected is None:
                skipped_no_feed_match += 1
                continue

            if event.start_time == expected.start_dt:
                unchanged += 1
                continue

            shift_hours = (expected.start_dt - event.start_time).total_seconds() / 3600
            if shift_hours != _utc_offset_hours(expected.start_dt):
                skipped_other_diff += 1
                print(
                    f"  OVERGESLAGEN  {event.title[:40]:<40} "
                    f"{event.start_time} -> {expected.start_dt} (verschil {shift_hours:+.1f}u, geen tz-offset)"
                )
                continue

            duration = event.end_time - event.start_time
            print(f"  HERSTEL       {event.title[:40]:<40} {event.start_time} -> {expected.start_dt}")
            if apply_changes:
                event.start_time = expected.start_dt
                event.end_time = expected.start_dt + duration
            fixed += 1

        if apply_changes:
            await db.commit()

        print()
        print(f"Timezone: {app_timezone_name()}")
        print(f"Cozi events in database : {len(events)}")
        print(f"Al correct              : {unchanged}")
        print(f"{'Hersteld' if apply_changes else 'Te herstellen':<24}: {fixed}")
        print(f"Niet in feed gevonden   : {skipped_no_feed_match}")
        print(f"Ander verschil (skip)   : {skipped_other_diff}")
        if not apply_changes and fixed:
            print("\nDit was een dry-run. Draai met --apply om de wijzigingen op te slaan.")

    return 0


def main() -> None:
    parser = argparse.ArgumentParser(description="Herstel tijdzone-offset van geïmporteerde Cozi events")
    parser.add_argument("--apply", action="store_true", help="Wijzigingen daadwerkelijk opslaan")
    parser.add_argument("--dry-run", action="store_true", help="Alleen tonen wat er zou gebeuren (standaard)")
    parser.add_argument("--force", action="store_true", help="Doorgaan zonder backup van vandaag")
    args = parser.parse_args()

    raise SystemExit(asyncio.run(_run(apply_changes=args.apply and not args.dry_run, force=args.force)))


if __name__ == "__main__":
    main()
