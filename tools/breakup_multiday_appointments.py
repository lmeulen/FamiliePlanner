"""Utility script to split multi-day all-day events into daily recurring series.

This corrects events that span multiple days by converting them into a daily
recurring series so they appear on all days instead of just the first day.

Usage:
    python -m tools.breakup_multiday_appointments
    python -m tools.breakup_multiday_appointments --dry-run
"""

from __future__ import annotations

import argparse
import asyncio
from datetime import datetime, timedelta

from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.database import AsyncSessionLocal
from app.enums import RecurrenceType
from app.models.agenda import AgendaEvent, RecurrenceSeries, agenda_event_members, recurrence_series_members
from app.utils.db import set_junction_members
from app.utils.recurrence import generate_occurrence_dates


async def _get_multiday_events(session: AsyncSession) -> list[AgendaEvent]:
    """Find all multi-day all-day events (events where end > start + 1 day)."""
    result = await session.execute(
        select(AgendaEvent)
        .where(
            and_(
                AgendaEvent.all_day == True,  # noqa: E712
                AgendaEvent.series_id == None,  # noqa: E711
            )
        )
        .options(selectinload(AgendaEvent.members))
    )
    events = result.scalars().all()

    # Filter to only events that span more than 1 day
    multiday = []
    for ev in events:
        days_diff = (ev.end_time.date() - ev.start_time.date()).days
        if days_diff > 0:
            multiday.append(ev)

    return multiday


def _make_events_for_series(series: RecurrenceSeries) -> list[AgendaEvent]:
    """Generate event occurrences for a recurring series."""
    occurrence_dates = generate_occurrence_dates(
        recurrence_type=series.recurrence_type,
        series_start=series.series_start,
        series_end=series.series_end,
        interval=series.interval,
        count=series.count,
        monthly_pattern=series.monthly_pattern,
        rrule_string=series.rrule,
    )
    return [
        AgendaEvent(
            title=series.title,
            description=series.description,
            location=series.location,
            start_time=datetime.combine(d, series.start_time_of_day),
            end_time=datetime.combine(d, series.end_time_of_day),
            all_day=series.all_day,
            series_id=series.id,
            is_exception=False,
        )
        for d in occurrence_dates
    ]


async def breakup_multiday_appointments(dry_run: bool) -> None:
    """Convert multi-day all-day events into daily recurring series."""
    async with AsyncSessionLocal() as session:
        multiday_events = await _get_multiday_events(session)

        if not multiday_events:
            print("No multi-day all-day events found.")
            return

        print(f"Found {len(multiday_events)} multi-day all-day event(s):")
        print()

        for ev in multiday_events:
            days_span = (ev.end_time.date() - ev.start_time.date()).days
            member_ids = [m.id for m in ev.members]
            print(f"Event ID {ev.id}: '{ev.title}'")
            print(f"  Spans {days_span + 1} days: {ev.start_time.date()} to {ev.end_time.date()}")
            print(f"  Members: {len(member_ids)}")
            print()

        if dry_run:
            print("Dry-run mode: no changes were made.")
            return

        converted_count = 0
        for ev in multiday_events:
            # Get member IDs before we delete the event
            member_ids = [m.id for m in ev.members]

            # Determine series_end: if end_time is at midnight (00:00), exclude that day
            series_end = ev.end_time.date()
            if ev.end_time.time().hour == 0 and ev.end_time.time().minute == 0 and ev.end_time.time().second == 0:
                # End time is at midnight, so the event ends at the END of the previous day
                series_end = series_end - timedelta(days=1)

            # Create recurring series
            series = RecurrenceSeries(
                title=ev.title,
                description=ev.description,
                location=ev.location,
                recurrence_type=RecurrenceType.daily,
                series_start=ev.start_time.date(),
                series_end=series_end,
                start_time_of_day=ev.start_time.time(),
                end_time_of_day=ev.end_time.time(),
                all_day=True,
                interval=1,
                count=None,
                monthly_pattern=None,
                rrule=None,
            )
            session.add(series)
            await session.flush()

            # Set members on series
            await set_junction_members(session, recurrence_series_members, "series_id", series.id, member_ids)

            # Generate occurrences
            occurrences = _make_events_for_series(series)
            session.add_all(occurrences)
            await session.flush()

            # Set members on all occurrences
            if member_ids:
                for occurrence in occurrences:
                    await set_junction_members(session, agenda_event_members, "event_id", occurrence.id, member_ids)

            # Delete original event
            await session.delete(ev)

            converted_count += 1
            print(f"✓ Converted '{ev.title}' to daily series with {len(occurrences)} occurrences")

        await session.commit()

        print()
        print(f"Conversion completed: {converted_count} event(s) converted to daily series.")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Split multi-day all-day events into daily recurring series.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show which events would be converted without making changes.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    asyncio.run(breakup_multiday_appointments(dry_run=args.dry_run))


if __name__ == "__main__":
    main()
