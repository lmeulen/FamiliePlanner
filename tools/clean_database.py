"""Utility script to remove calendar events, tasks, meals and birthdays from the database.

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
from app.models.agenda import AgendaEvent, RecurrenceSeries
from app.models.birthdays import Birthday
from app.models.meals import Meal
from app.models.tasks import Task


async def _count_rows(session: AsyncSession) -> dict[str, int]:
    events_result = await session.execute(select(func.count()).select_from(AgendaEvent))
    tasks_result = await session.execute(select(func.count()).select_from(Task))
    meals_result = await session.execute(select(func.count()).select_from(Meal))
    birthdays_result = await session.execute(select(func.count()).select_from(Birthday))

    return {
        "agenda_events": int(events_result.scalar_one()),
        "tasks": int(tasks_result.scalar_one()),
        "meals": int(meals_result.scalar_one()),
        "birthdays": int(birthdays_result.scalar_one()),
    }


async def clean_database(dry_run: bool) -> None:
    async with AsyncSessionLocal() as session:
        before = await _count_rows(session)

        print("Current row counts:")
        print(f"- agenda_events: {before['agenda_events']}")
        print(f"- tasks: {before['tasks']}")
        print(f"- meals: {before['meals']}")
        print(f"- birthdays: {before['birthdays']}")

        if dry_run:
            print("\nDry-run mode: no changes were made.")
            return

        # Get all birthday series IDs before deleting
        birthdays_result = await session.execute(select(Birthday.series_id).where(Birthday.series_id.is_not(None)))
        birthday_series_ids = [row[0] for row in birthdays_result.all()]

        # Delete birthday-linked agenda series first (cascade deletes agenda events)
        if birthday_series_ids:
            await session.execute(delete(RecurrenceSeries).where(RecurrenceSeries.id.in_(birthday_series_ids)))

        # Delete birthdays
        await session.execute(delete(Birthday))

        # Delete remaining agenda events and tasks/meals
        await session.execute(delete(AgendaEvent))
        await session.execute(delete(Task))
        await session.execute(delete(Meal))
        await session.commit()

        after = await _count_rows(session)

        print("\nCleanup completed.")
        print(f"- agenda_events removed: {before['agenda_events'] - after['agenda_events']}")
        print(f"- tasks removed: {before['tasks'] - after['tasks']}")
        print(f"- meals removed: {before['meals'] - after['meals']}")
        print(f"- birthdays removed: {before['birthdays'] - after['birthdays']}")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Remove calendar events, tasks, meals and birthdays from the FamiliePlanner database.",
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
