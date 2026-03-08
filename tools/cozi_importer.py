"""Import Cozi ICS feed into FamiliePlanner agenda.

Usage:
    python -m tools.cozi_importer --dry-run
    python -m tools.cozi_importer
    python -m tools.cozi_importer --today
"""

from __future__ import annotations

import argparse
import asyncio
import re
from dataclasses import dataclass
from datetime import date, datetime
from typing import Any

import httpx
from icalendar import Calendar
from sqlalchemy import and_, select
from sqlalchemy import delete as sa_delete
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import COZI_ICS_URL
from app.database import AsyncSessionLocal
from app.enums import MealType, RecurrenceType
from app.models.agenda import AgendaEvent, RecurrenceSeries, agenda_event_members, recurrence_series_members
from app.models.meals import Meal
from app.utils.db import set_junction_members
from app.utils.recurrence import generate_occurrence_dates
from tools.cozi_import_advisor import (
    FamilyMemberRecord,
    _build_found_name_mapping,
    _detect_meal_candidate,
    _extract_members_from_summary,
    _extract_start_end,
    _load_family_members,
    _map_rrule_to_familieplanner,
    _normalize_name,
    _normalize_rrule,
    _tokenize_name,
)


@dataclass
class ImportStats:
    total_events: int = 0
    recurring_events: int = 0
    single_events: int = 0
    imported_series: int = 0
    imported_single: int = 0
    imported_multiday_as_series: int = 0
    skipped_existing_series: int = 0
    skipped_existing_single: int = 0
    skipped_unsupported: int = 0
    skipped_invalid: int = 0
    detected_meal_candidates: int = 0
    imported_meals: int = 0
    skipped_existing_meals: int = 0
    cleared_events: int = 0
    cleared_series: int = 0


def _to_naive(dt: datetime) -> datetime:
    if dt.tzinfo is None:
        return dt
    return dt.replace(tzinfo=None)


def _is_today(component: Any) -> bool:
    dtstart = component.decoded("DTSTART")
    today = date.today()
    if isinstance(dtstart, datetime):
        return dtstart.date() == today
    if isinstance(dtstart, date):
        return dtstart == today
    return False


def _extract_ics_color(event: Any) -> str:
    raw = str(event.get("COLOR", "") or "").strip()
    if len(raw) == 7 and raw.startswith("#"):
        return raw
    return "#4ECDC4"


def _extract_members_and_title_for_import(
    summary_raw: str,
    family_members: list[FamilyMemberRecord],
) -> tuple[list[str], str]:
    summary = summary_raw.strip()
    members, cleaned_title = _extract_members_from_summary(summary)
    if members:
        return members, cleaned_title

    match = re.match(r"^([^:]+?)\s*:\s*(.+)$", summary)
    if not match:
        return [], summary

    prefix = match.group(1).strip()
    title = match.group(2).strip() or summary
    normalized_prefix = _normalize_name(prefix)
    if not normalized_prefix:
        return [], summary

    group_aliases = {"all", "iedereen", "everyone", "heelgezin", "gezin"}
    if normalized_prefix in group_aliases:
        return [prefix], title

    if any(_normalize_name(member.name) == normalized_prefix for member in family_members):
        return [prefix], title

    prefix_tokens = _tokenize_name(prefix)
    if prefix_tokens:
        prefix_first_token = prefix_tokens[0]
        for member in family_members:
            member_tokens = _tokenize_name(member.name)
            if member_tokens and member_tokens[0] == prefix_first_token:
                return [prefix], title

    return [], summary


def _extract_rrule_count(rrule: dict[str, list[Any]]) -> int | None:
    values = rrule.get("COUNT")
    if not values:
        return None
    try:
        count = int(values[0])
        if count < 1:
            return None
        return min(count, 365)
    except Exception:
        return None


def _extract_rrule_until_date(rrule: dict[str, list[Any]]) -> date | None:
    values = rrule.get("UNTIL")
    if not values:
        return None

    raw = values[0]
    if isinstance(raw, datetime):
        return _to_naive(raw).date()
    if isinstance(raw, date):
        return raw

    text = str(raw).strip()
    if not text:
        return None

    for parser in (datetime.fromisoformat,):
        try:
            return parser(text).date()
        except Exception:
            continue

    compact = text.replace("Z", "")
    for fmt in ("%Y%m%dT%H%M%S", "%Y%m%d"):
        try:
            return datetime.strptime(compact, fmt).date()
        except Exception:
            continue

    return None


async def _single_event_exists(
    db: AsyncSession,
    *,
    title: str,
    start_time: datetime,
    end_time: datetime,
    all_day: bool,
    location: str,
) -> bool:
    stmt = select(AgendaEvent.id).where(
        and_(
            AgendaEvent.title == title,
            AgendaEvent.start_time == start_time,
            AgendaEvent.end_time == end_time,
            AgendaEvent.all_day == all_day,
            AgendaEvent.location == location,
            AgendaEvent.series_id.is_(None),
        )
    )
    result = await db.execute(stmt)
    return result.scalar_one_or_none() is not None


async def _series_exists(
    db: AsyncSession,
    *,
    title: str,
    series_start: date,
    recurrence_type: RecurrenceType,
    interval: int,
    monthly_pattern: str | None,
    all_day: bool,
    location: str,
) -> bool:
    stmt = select(RecurrenceSeries.id).where(
        and_(
            RecurrenceSeries.title == title,
            RecurrenceSeries.series_start == series_start,
            RecurrenceSeries.recurrence_type == recurrence_type,
            RecurrenceSeries.interval == interval,
            RecurrenceSeries.monthly_pattern == monthly_pattern,
            RecurrenceSeries.all_day == all_day,
            RecurrenceSeries.location == location,
        )
    )
    result = await db.execute(stmt)
    return result.scalar_one_or_none() is not None


async def _meal_exists(
    db: AsyncSession,
    *,
    meal_date: date,
    name: str,
    meal_type: MealType,
) -> bool:
    stmt = select(Meal.id).where(
        and_(
            Meal.date == meal_date,
            Meal.name == name,
            Meal.meal_type == meal_type,
        )
    )
    result = await db.execute(stmt)
    return result.scalar_one_or_none() is not None


def _print_summary(stats: ImportStats, dry_run: bool) -> None:
    print("=" * 72)
    print("Cozi → FamiliePlanner importer")
    print("=" * 72)
    print(f"Mode: {'DRY-RUN (geen writes)' if dry_run else 'IMPORT (writes actief)'}")
    print(f"Totaal VEVENT items: {stats.total_events}")
    print(f"Recurring events gezien: {stats.recurring_events}")
    print(f"Single events gezien: {stats.single_events}")
    print(f"Gedetecteerde meal-kandidaten: {stats.detected_meal_candidates}")
    print(f"Verwijderde bestaande events: {stats.cleared_events}")
    print(f"Verwijderde bestaande series: {stats.cleared_series}")
    print(f"Geïmporteerde series: {stats.imported_series}")
    print(f"Geïmporteerde losse events: {stats.imported_single}")
    print(f"Geïmporteerde meerdaagse events (als daily series): {stats.imported_multiday_as_series}")
    print(f"Geïmporteerde diners (meals): {stats.imported_meals}")
    print(f"Overgeslagen bestaande series: {stats.skipped_existing_series}")
    print(f"Overgeslagen bestaande losse events: {stats.skipped_existing_single}")
    print(f"Overgeslagen bestaande diners: {stats.skipped_existing_meals}")
    print(f"Overgeslagen unsupported RRULE: {stats.skipped_unsupported}")
    print(f"Overgeslagen invalid items: {stats.skipped_invalid}")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Import Cozi ICS into FamiliePlanner agenda")
    parser.add_argument("--url", default=COZI_ICS_URL, help="ICS URL to import (default: COZI_ICS_URL from .env)")
    parser.add_argument(
        "--today",
        action="store_true",
        help="Import only events with DTSTART on today's date",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Analyze and simulate import without writing to database",
    )
    parser.add_argument(
        "--default-series-count",
        type=int,
        default=60,
        help="Fallback occurrence count when RRULE has no COUNT/UNTIL (1-365)",
    )
    return parser.parse_args()


async def run() -> None:
    args = parse_args()

    if not args.url:
        print("Error: No Cozi ICS URL configured.")
        print("Set COZI_ICS_URL in .env or use --url argument.")
        return

    default_series_count = max(1, min(365, args.default_series_count))

    async with httpx.AsyncClient(timeout=20) as client:
        response = await client.get(args.url)
        response.raise_for_status()
        ics_content = response.text

    calendar = Calendar.from_ical(ics_content)
    events = [component for component in calendar.walk() if component.name == "VEVENT"]
    if args.today:
        events = [component for component in events if _is_today(component)]

    stats = ImportStats(total_events=len(events))

    family_members = await _load_family_members()
    found_names: set[str] = set()
    for event in events:
        summary_raw = str(event.get("SUMMARY", "") or "")
        summary_members, _ = _extract_members_and_title_for_import(summary_raw, family_members)
        for member_name in summary_members:
            found_names.add(member_name)

    found_name_mapping = _build_found_name_mapping(found_names, family_members)

    async with AsyncSessionLocal() as db:
        event_count_result = await db.execute(select(AgendaEvent.id))
        series_count_result = await db.execute(select(RecurrenceSeries.id))
        stats.cleared_events = len(event_count_result.scalars().all())
        stats.cleared_series = len(series_count_result.scalars().all())

        if not args.dry_run:
            await db.execute(sa_delete(AgendaEvent))
            await db.execute(sa_delete(RecurrenceSeries))

        for event in events:
            summary_raw = str(event.get("SUMMARY", "")).strip() or "(zonder titel)"
            summary_members, summary_title = _extract_members_and_title_for_import(summary_raw, family_members)
            mapped_member_ids = sorted(
                {member_id for member_name in summary_members for member_id in found_name_mapping.get(member_name, [])}
            )

            try:
                start_dt, end_dt, all_day = _extract_start_end(event)
                start_dt = _to_naive(start_dt)
                end_dt = _to_naive(end_dt)
            except Exception:
                stats.skipped_invalid += 1
                continue

            is_meal_candidate, _, meal_start, _ = _detect_meal_candidate(event, summary_title)
            if is_meal_candidate and meal_start is not None:
                stats.detected_meal_candidates += 1
                meal_date = meal_start.date()
                meal_exists = await _meal_exists(
                    db,
                    meal_date=meal_date,
                    name=summary_title,
                    meal_type=MealType.dinner,
                )
                if meal_exists:
                    stats.skipped_existing_meals += 1
                    continue

                if args.dry_run:
                    stats.imported_meals += 1
                    continue

                cook_member_id = mapped_member_ids[0] if len(mapped_member_ids) == 1 else None
                meal = Meal(
                    date=meal_date,
                    meal_type=MealType.dinner,
                    name=summary_title,
                    description="",
                    recipe_url="",
                    cook_member_id=cook_member_id,
                )
                db.add(meal)
                stats.imported_meals += 1
                continue

            description = str(event.get("DESCRIPTION", "") or "")
            location = str(event.get("LOCATION", "") or "")
            color = _extract_ics_color(event)
            rrule = _normalize_rrule(event)
            advice = _map_rrule_to_familieplanner(rrule)

            if advice.recurrence_type:
                stats.recurring_events += 1

                recurrence_type = RecurrenceType(advice.recurrence_type)
                series_start = start_dt.date()
                count = _extract_rrule_count(rrule)
                series_end = None if count else _extract_rrule_until_date(rrule)
                if not count and not series_end:
                    count = default_series_count

                if series_end and series_end <= series_start:
                    series_end = None
                    count = count or default_series_count

                exists = await _series_exists(
                    db,
                    title=summary_title,
                    series_start=series_start,
                    recurrence_type=recurrence_type,
                    interval=advice.interval,
                    monthly_pattern=advice.monthly_pattern,
                    all_day=all_day,
                    location=location,
                )
                if exists:
                    stats.skipped_existing_series += 1
                    continue

                if args.dry_run:
                    stats.imported_series += 1
                    continue

                series = RecurrenceSeries(
                    title=summary_title,
                    description=description,
                    location=location,
                    all_day=all_day,
                    color=color,
                    recurrence_type=recurrence_type,
                    series_start=series_start,
                    series_end=series_end or series_start,
                    start_time_of_day=start_dt.time(),
                    end_time_of_day=end_dt.time(),
                    interval=advice.interval,
                    count=count,
                    monthly_pattern=advice.monthly_pattern,
                    rrule=None,
                )
                db.add(series)
                await db.flush()
                await set_junction_members(db, recurrence_series_members, "series_id", series.id, mapped_member_ids)

                occurrence_dates = generate_occurrence_dates(
                    recurrence_type=recurrence_type,
                    series_start=series.series_start,
                    series_end=series.series_end,
                    interval=series.interval,
                    count=series.count,
                    monthly_pattern=series.monthly_pattern,
                    rrule_string=series.rrule,
                )
                generated_events = [
                    AgendaEvent(
                        title=series.title,
                        description=series.description,
                        location=series.location,
                        start_time=datetime.combine(occurrence_date, series.start_time_of_day),
                        end_time=datetime.combine(occurrence_date, series.end_time_of_day),
                        all_day=series.all_day,
                        color=series.color,
                        series_id=series.id,
                        is_exception=False,
                    )
                    for occurrence_date in occurrence_dates
                ]
                db.add_all(generated_events)
                await db.flush()

                if mapped_member_ids:
                    for generated_event in generated_events:
                        await set_junction_members(
                            db, agenda_event_members, "event_id", generated_event.id, mapped_member_ids
                        )

                stats.imported_series += 1
                continue

            if rrule:
                stats.recurring_events += 1
                stats.skipped_unsupported += 1
                continue

            stats.single_events += 1

            # Check if this is a multi-day all-day event (should be converted to daily series)
            is_multiday_allday = all_day and (end_dt.date() - start_dt.date()).days > 0

            if is_multiday_allday:
                # Convert multi-day all-day event to daily series
                series_start = start_dt.date()
                series_end = end_dt.date()

                # Check if series already exists
                exists = await _series_exists(
                    db,
                    title=summary_title,
                    series_start=series_start,
                    recurrence_type=RecurrenceType.daily,
                    interval=1,
                    monthly_pattern=None,
                    all_day=True,
                    location=location,
                )
                if exists:
                    stats.skipped_existing_series += 1
                    continue

                if args.dry_run:
                    stats.imported_multiday_as_series += 1
                    continue

                # Create daily series
                series = RecurrenceSeries(
                    title=summary_title,
                    description=description,
                    location=location,
                    all_day=True,
                    color=color,
                    recurrence_type=RecurrenceType.daily,
                    series_start=series_start,
                    series_end=series_end,
                    start_time_of_day=start_dt.time(),
                    end_time_of_day=end_dt.time(),
                    interval=1,
                    count=None,
                    monthly_pattern=None,
                    rrule=None,
                )
                db.add(series)
                await db.flush()
                await set_junction_members(db, recurrence_series_members, "series_id", series.id, mapped_member_ids)

                # Generate occurrences
                occurrence_dates = generate_occurrence_dates(
                    recurrence_type=RecurrenceType.daily,
                    series_start=series.series_start,
                    series_end=series.series_end,
                    interval=1,
                    count=None,
                    monthly_pattern=None,
                    rrule_string=None,
                )
                generated_events = [
                    AgendaEvent(
                        title=series.title,
                        description=series.description,
                        location=series.location,
                        start_time=datetime.combine(occurrence_date, series.start_time_of_day),
                        end_time=datetime.combine(occurrence_date, series.end_time_of_day),
                        all_day=series.all_day,
                        color=series.color,
                        series_id=series.id,
                        is_exception=False,
                    )
                    for occurrence_date in occurrence_dates
                ]
                db.add_all(generated_events)
                await db.flush()

                if mapped_member_ids:
                    for generated_event in generated_events:
                        await set_junction_members(
                            db, agenda_event_members, "event_id", generated_event.id, mapped_member_ids
                        )

                stats.imported_multiday_as_series += 1
            else:
                # Regular single-day event
                exists = await _single_event_exists(
                    db,
                    title=summary_title,
                    start_time=start_dt,
                    end_time=end_dt,
                    all_day=all_day,
                    location=location,
                )
                if exists:
                    stats.skipped_existing_single += 1
                    continue

                if args.dry_run:
                    stats.imported_single += 1
                    continue

                single_event = AgendaEvent(
                    title=summary_title,
                    description=description,
                    location=location,
                    start_time=start_dt,
                    end_time=end_dt,
                    all_day=all_day,
                    color=color,
                )
                db.add(single_event)
                await db.flush()
                await set_junction_members(db, agenda_event_members, "event_id", single_event.id, mapped_member_ids)
                stats.imported_single += 1

        if args.dry_run:
            await db.rollback()
        else:
            await db.commit()

    _print_summary(stats, args.dry_run)


def main() -> None:
    asyncio.run(run())


if __name__ == "__main__":
    main()
