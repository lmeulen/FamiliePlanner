"""Utility script to remove calendar events, tasks and meals from the database.

Usage:
    python tools/clean_database.py
    python tools/clean_database.py --dry-run
"""

from __future__ import annotations

import argparse
import asyncio

from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import AsyncSessionLocal
from app.models.agenda import AgendaEvent
from app.models.meals import Meal
from app.models.tasks import Task


async def _count_rows(session: AsyncSession) -> dict[str, int]:
    events_result = await session.execute(select(func.count()).select_from(AgendaEvent))
    tasks_result = await session.execute(select(func.count()).select_from(Task))
    meals_result = await session.execute(select(func.count()).select_from(Meal))

    return {
        "agenda_events": int(events_result.scalar_one()),
        "tasks": int(tasks_result.scalar_one()),
        "meals": int(meals_result.scalar_one()),
    }


async def clean_database(dry_run: bool) -> None:
    async with AsyncSessionLocal() as session:
        before = await _count_rows(session)

        print("Current row counts:")
        print(f"- agenda_events: {before['agenda_events']}")
        print(f"- tasks: {before['tasks']}")
        print(f"- meals: {before['meals']}")

        if dry_run:
            print("\nDry-run mode: no changes were made.")
            return

        await session.execute(delete(AgendaEvent))
        await session.execute(delete(Task))
        await session.execute(delete(Meal))
        await session.commit()

        after = await _count_rows(session)

        print("\nCleanup completed.")
        print(f"- agenda_events removed: {before['agenda_events'] - after['agenda_events']}")
        print(f"- tasks removed: {before['tasks'] - after['tasks']}")
        print(f"- meals removed: {before['meals'] - after['meals']}")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Remove calendar events, tasks and meals from the FamiliePlanner database.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show how many rows would be removed without deleting anything.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    asyncio.run(clean_database(dry_run=args.dry_run))


if __name__ == "__main__":
    main()
