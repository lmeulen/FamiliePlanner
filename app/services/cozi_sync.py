"""Cozi ICS synchronization service.

Provides:
- fetch_and_parse_cozi(url): fetch ICS and return parsed internal events
- classify_cozi_events(events, db): compare against existing DB, return preview items
- import_selected_events(selected_uids, db, url, ...): import chosen items
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Any, Literal

import httpx
from icalendar import Calendar
from loguru import logger
from sqlalchemy import and_, select
from sqlalchemy import delete as sa_delete
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.enums import MealType, RecurrenceType
from app.models.agenda import AgendaEvent, RecurrenceSeries, agenda_event_members, recurrence_series_members
from app.models.meals import Meal
from app.utils.db import set_junction_members
from app.utils.recurrence import generate_occurrence_dates
from tools.cozi_import_advisor import (
    FamilyMemberRecord,
    MappingAdvice,
    _build_found_name_mapping,
    _detect_meal_candidate,
    _extract_start_end,
    _load_family_members,
    _map_rrule_to_familieplanner,
    _normalize_rrule,
)
from tools.cozi_importer import (
    _extract_members_and_title_for_import,
    _extract_rrule_count,
    _extract_rrule_until_date,
    _to_naive,
)

EventStatus = Literal["new", "changed", "likely_exists", "exists"]
EventType = Literal["event", "series", "meal"]
Recommendation = Literal["import", "skip"]

DEFAULT_SERIES_COUNT = 60


# ── Internal parsed event ─────────────────────────────────────────

@dataclass
class _ParsedEvent:
    uid: str
    title: str
    description: str
    location: str
    start_dt: datetime
    end_dt: datetime
    all_day: bool
    member_names: list[str]
    mapped_member_ids: list[int]
    rrule: dict
    advice: MappingAdvice
    is_meal: bool
    is_multiday_allday: bool
    event_type: EventType = field(init=False)

    def __post_init__(self) -> None:
        if self.is_meal:
            self.event_type = "meal"
        elif self.advice.recurrence_type or self.is_multiday_allday:
            self.event_type = "series"
        else:
            self.event_type = "event"


@dataclass
class _CoziChange:
    field: str
    old_value: str
    new_value: str


@dataclass
class CoziPreviewItem:
    uid: str
    status: EventStatus
    recommendation: Recommendation
    recommendation_reason: str
    event_type: EventType
    title: str
    start_date: str        # ISO date "YYYY-MM-DD"
    start_time: str | None  # "HH:MM" or None for all-day
    end_time: str | None
    all_day: bool
    location: str
    description: str
    member_ids: list[int]
    member_names: list[str]
    recurrence_type: str | None
    recurrence_interval: int
    matched_fp_id: int | None
    matched_fp_title: str | None
    matched_fp_type: str | None
    changes: list[dict]

    def to_dict(self) -> dict:
        return {
            "uid": self.uid,
            "status": self.status,
            "recommendation": self.recommendation,
            "recommendation_reason": self.recommendation_reason,
            "event_type": self.event_type,
            "title": self.title,
            "start_date": self.start_date,
            "start_time": self.start_time,
            "end_time": self.end_time,
            "all_day": self.all_day,
            "location": self.location,
            "description": self.description,
            "member_ids": self.member_ids,
            "member_names": self.member_names,
            "recurrence_type": self.recurrence_type,
            "recurrence_interval": self.recurrence_interval,
            "matched_fp_id": self.matched_fp_id,
            "matched_fp_title": self.matched_fp_title,
            "matched_fp_type": self.matched_fp_type,
            "changes": self.changes,
        }


@dataclass
class ImportResult:
    imported_events: int = 0
    imported_series: int = 0
    imported_meals: int = 0
    updated_events: int = 0
    updated_series: int = 0
    updated_meals: int = 0
    skipped: int = 0


# ── ICS Fetch & Parse ─────────────────────────────────────────────

async def fetch_ics(url: str) -> str:
    async with httpx.AsyncClient(timeout=20) as client:
        response = await client.get(url)
        response.raise_for_status()
        return response.text


def _parse_ics_events(content: str) -> list[Any]:
    cal = Calendar.from_ical(content)
    return [c for c in cal.walk() if c.name == "VEVENT"]


async def fetch_and_parse_cozi(url: str) -> list[_ParsedEvent]:
    """Fetch Cozi ICS feed and return list of parsed events."""
    content = await fetch_ics(url)
    raw_events = _parse_ics_events(content)

    family_members = await _load_family_members()

    found_names: set[str] = set()
    for ev in raw_events:
        summary_raw = str(ev.get("SUMMARY", "") or "")
        members, _ = _extract_members_and_title_for_import(summary_raw, family_members)
        found_names.update(members)

    name_mapping = _build_found_name_mapping(found_names, family_members)

    parsed: list[_ParsedEvent] = []
    for ev in raw_events:
        item = _parse_single_event(ev, family_members, name_mapping)
        if item is not None:
            parsed.append(item)

    logger.debug("cozi_sync.parsed url={} total={}", url, len(parsed))
    return parsed


def _parse_single_event(
    ev: Any,
    family_members: list[FamilyMemberRecord],
    name_mapping: dict[str, list[int]],
) -> _ParsedEvent | None:
    try:
        start_dt, end_dt, all_day = _extract_start_end(ev)
        start_dt = _to_naive(start_dt)
        end_dt = _to_naive(end_dt)
    except Exception:
        return None

    uid = str(ev.get("UID", "") or "")
    summary_raw = str(ev.get("SUMMARY", "") or "").strip() or "(zonder titel)"
    member_names, title = _extract_members_and_title_for_import(summary_raw, family_members)
    mapped_ids = sorted({mid for n in member_names for mid in name_mapping.get(n, [])})
    description = str(ev.get("DESCRIPTION", "") or "")
    location = str(ev.get("LOCATION", "") or "")
    rrule = _normalize_rrule(ev)
    advice = _map_rrule_to_familieplanner(rrule)

    is_meal, _, _, _ = _detect_meal_candidate(ev, title)
    is_multiday_allday = (
        all_day
        and not is_meal
        and not advice.recurrence_type
        and (end_dt.date() - start_dt.date()).days > 0
    )

    return _ParsedEvent(
        uid=uid,
        title=title,
        description=description,
        location=location,
        start_dt=start_dt,
        end_dt=end_dt,
        all_day=all_day,
        member_names=member_names,
        mapped_member_ids=mapped_ids,
        rrule=rrule,
        advice=advice,
        is_meal=is_meal,
        is_multiday_allday=is_multiday_allday,
    )


# ── Classification ────────────────────────────────────────────────

async def classify_cozi_events(
    events: list[_ParsedEvent],
    db: AsyncSession,
) -> list[CoziPreviewItem]:
    """Classify each parsed Cozi event against existing FamiliePlanner data."""
    return [await _classify_one(ev, db) for ev in events]


async def _classify_one(ev: _ParsedEvent, db: AsyncSession) -> CoziPreviewItem:
    changes: list[_CoziChange] = []
    matched_fp_id: int | None = None
    matched_fp_title: str | None = None
    matched_fp_type: str | None = None
    status: EventStatus = "new"
    recommendation: Recommendation = "import"
    reason = "Geen overeenkomst gevonden in FamiliePlanner"

    if ev.event_type == "meal":
        uid_match = await _meal_by_cozi_uid(db, ev.uid) if ev.uid else None
        if uid_match:
            matched_fp_id = uid_match.id
            matched_fp_title = uid_match.name
            matched_fp_type = "meal"
            changes = _diff_meal(uid_match, ev)
            if changes:
                status = "changed"
                recommendation = "import"
                reason = "Maaltijd gewijzigd in Cozi"
            else:
                status = "exists"
                recommendation = "skip"
                reason = "Maaltijd al aanwezig (geen wijzigingen)"
        else:
            fuzzy = await _meal_fuzzy_match(db, ev)
            if fuzzy:
                matched_fp_id = fuzzy.id
                matched_fp_title = fuzzy.name
                matched_fp_type = "meal"
                status = "likely_exists"
                recommendation = "skip"
                reason = "Vergelijkbare maaltijd al aanwezig (naam + datum)"

    elif ev.event_type == "series":
        uid_match = await _series_by_cozi_uid(db, ev.uid) if ev.uid else None
        if uid_match:
            matched_fp_id = uid_match.id
            matched_fp_title = uid_match.title
            matched_fp_type = "series"
            changes = _diff_series(uid_match, ev)
            if changes:
                status = "changed"
                recommendation = "import"
                reason = "Herhalende afspraak gewijzigd in Cozi"
            else:
                status = "exists"
                recommendation = "skip"
                reason = "Herhalende afspraak al aanwezig (geen wijzigingen)"
        else:
            fuzzy = await _series_fuzzy_match(db, ev)
            if fuzzy:
                matched_fp_id = fuzzy.id
                matched_fp_title = fuzzy.title
                matched_fp_type = "series"
                status = "likely_exists"
                recommendation = "skip"
                reason = "Vergelijkbare reeks al aanwezig (naam + datum)"

    else:  # event
        uid_match = await _event_by_cozi_uid(db, ev.uid) if ev.uid else None
        if uid_match:
            matched_fp_id = uid_match.id
            matched_fp_title = uid_match.title
            matched_fp_type = "event"
            changes = _diff_event(uid_match, ev)
            if changes:
                status = "changed"
                recommendation = "import"
                reason = "Afspraak gewijzigd in Cozi"
            else:
                status = "exists"
                recommendation = "skip"
                reason = "Afspraak al aanwezig (geen wijzigingen)"
        else:
            fuzzy = await _event_fuzzy_match(db, ev)
            if fuzzy:
                matched_fp_id = fuzzy.id
                matched_fp_title = fuzzy.title
                matched_fp_type = "event"
                status = "likely_exists"
                recommendation = "skip"
                reason = "Vergelijkbare afspraak al aanwezig (naam + datum)"

    start_time = ev.start_dt.strftime("%H:%M") if not ev.all_day else None
    end_time = ev.end_dt.strftime("%H:%M") if not ev.all_day else None

    return CoziPreviewItem(
        uid=ev.uid,
        status=status,
        recommendation=recommendation,
        recommendation_reason=reason,
        event_type=ev.event_type,
        title=ev.title,
        start_date=ev.start_dt.date().isoformat(),
        start_time=start_time,
        end_time=end_time,
        all_day=ev.all_day,
        location=ev.location,
        description=ev.description,
        member_ids=ev.mapped_member_ids,
        member_names=ev.member_names,
        recurrence_type=ev.advice.recurrence_type,
        recurrence_interval=ev.advice.interval,
        matched_fp_id=matched_fp_id,
        matched_fp_title=matched_fp_title,
        matched_fp_type=matched_fp_type,
        changes=[{"field": c.field, "old": c.old_value, "new": c.new_value} for c in changes],
    )


# ── DB Lookup helpers ─────────────────────────────────────────────

async def _meal_by_cozi_uid(db: AsyncSession, uid: str) -> Meal | None:
    result = await db.execute(select(Meal).where(Meal.cozi_uid == uid))
    return result.scalar_one_or_none()


async def _meal_fuzzy_match(db: AsyncSession, ev: _ParsedEvent) -> Meal | None:
    result = await db.execute(
        select(Meal).where(
            and_(
                Meal.name == ev.title,
                Meal.date == ev.start_dt.date(),
                Meal.cozi_uid.is_(None),
            )
        )
    )
    return result.scalar_one_or_none()


async def _series_by_cozi_uid(db: AsyncSession, uid: str) -> RecurrenceSeries | None:
    result = await db.execute(select(RecurrenceSeries).where(RecurrenceSeries.cozi_uid == uid))
    return result.scalar_one_or_none()


async def _series_fuzzy_match(db: AsyncSession, ev: _ParsedEvent) -> RecurrenceSeries | None:
    result = await db.execute(
        select(RecurrenceSeries)
        .options(selectinload(RecurrenceSeries.members))
        .where(
            and_(
                RecurrenceSeries.title == ev.title,
                RecurrenceSeries.series_start == ev.start_dt.date(),
                RecurrenceSeries.cozi_uid.is_(None),
            )
        )
    )
    matches = _filter_candidates_by_member_ids(ev.mapped_member_ids, result.scalars().all())
    if not matches:
        return None
    if len(matches) == 1:
        return matches[0]

    def _score(candidate: RecurrenceSeries) -> float:
        candidate_start = datetime.combine(candidate.series_start, candidate.start_time_of_day)
        return abs((candidate_start - ev.start_dt).total_seconds())

    return min(matches, key=_score)


async def _event_by_cozi_uid(db: AsyncSession, uid: str) -> AgendaEvent | None:
    result = await db.execute(
        select(AgendaEvent).where(
            and_(AgendaEvent.cozi_uid == uid, AgendaEvent.series_id.is_(None))
        )
    )
    return result.scalar_one_or_none()


async def _event_fuzzy_match(db: AsyncSession, ev: _ParsedEvent) -> AgendaEvent | None:
    start_of_day = ev.start_dt.replace(hour=0, minute=0, second=0, microsecond=0)
    end_of_day = start_of_day + timedelta(days=1)
    result = await db.execute(
        select(AgendaEvent)
        .options(selectinload(AgendaEvent.members))
        .where(
            and_(
                AgendaEvent.title == ev.title,
                AgendaEvent.start_time >= start_of_day,
                AgendaEvent.start_time < end_of_day,
                AgendaEvent.series_id.is_(None),
                AgendaEvent.cozi_uid.is_(None),
            )
        )
    )
    matches = _filter_candidates_by_member_ids(ev.mapped_member_ids, result.scalars().all())
    if not matches:
        return None
    if len(matches) == 1:
        return matches[0]

    def _score(candidate: AgendaEvent) -> float:
        if candidate.start_time is None:
            return float("inf")
        return abs((candidate.start_time - ev.start_dt).total_seconds())

    return min(matches, key=_score)


def _filter_candidates_by_member_ids(expected_member_ids: list[int], candidates: list[Any]) -> list[Any]:
    if not candidates:
        return []
    if not expected_member_ids:
        return candidates

    expected = set(expected_member_ids)
    exact_matches = [candidate for candidate in candidates if set(getattr(candidate, "member_ids", [])) == expected]
    if exact_matches:
        return exact_matches

    overlapping_matches = [
        candidate
        for candidate in candidates
        if expected.intersection(getattr(candidate, "member_ids", []))
    ]
    if overlapping_matches:
        return overlapping_matches

    return []


# ── Diff helpers ──────────────────────────────────────────────────

def _diff_meal(existing: Meal, ev: _ParsedEvent) -> list[_CoziChange]:
    changes = []
    if existing.name != ev.title:
        changes.append(_CoziChange("naam", existing.name, ev.title))
    if existing.date != ev.start_dt.date():
        changes.append(_CoziChange("datum", str(existing.date), ev.start_dt.date().isoformat()))
    return changes


def _diff_series(existing: RecurrenceSeries, ev: _ParsedEvent) -> list[_CoziChange]:
    changes = []
    if existing.title != ev.title:
        changes.append(_CoziChange("titel", existing.title, ev.title))
    if existing.series_start != ev.start_dt.date():
        changes.append(_CoziChange("startdatum", str(existing.series_start), ev.start_dt.date().isoformat()))
    if (existing.location or "") != (ev.location or ""):
        changes.append(_CoziChange("locatie", existing.location or "", ev.location or ""))
    if ev.advice.recurrence_type and existing.recurrence_type.value != ev.advice.recurrence_type:
        changes.append(_CoziChange("herhaling", existing.recurrence_type.value, ev.advice.recurrence_type))
    return changes


def _diff_event(existing: AgendaEvent, ev: _ParsedEvent) -> list[_CoziChange]:
    changes = []
    if existing.title != ev.title:
        changes.append(_CoziChange("titel", existing.title, ev.title))
    if existing.start_time != ev.start_dt:
        changes.append(_CoziChange("starttijd", str(existing.start_time), str(ev.start_dt)))
    if (existing.location or "") != (ev.location or ""):
        changes.append(_CoziChange("locatie", existing.location or "", ev.location or ""))
    return changes


# ── Import ────────────────────────────────────────────────────────

async def import_selected_events(
    selected_uids: list[str],
    db: AsyncSession,
    url: str,
    default_series_count: int = DEFAULT_SERIES_COUNT,
) -> ImportResult:
    """Re-fetch Cozi feed and import only events whose UID is in selected_uids."""
    content = await fetch_ics(url)
    raw_events = _parse_ics_events(content)

    family_members = await _load_family_members()
    found_names: set[str] = set()
    for ev in raw_events:
        summary_raw = str(ev.get("SUMMARY", "") or "")
        members, _ = _extract_members_and_title_for_import(summary_raw, family_members)
        found_names.update(members)
    name_mapping = _build_found_name_mapping(found_names, family_members)

    uid_set = set(selected_uids)
    result = ImportResult()

    for raw_ev in raw_events:
        uid = str(raw_ev.get("UID", "") or "")
        if uid not in uid_set:
            result.skipped += 1
            continue

        parsed = _parse_single_event(raw_ev, family_members, name_mapping)
        if parsed is None:
            result.skipped += 1
            continue

        if parsed.event_type == "meal":
            was_update = await _import_meal(parsed, db)
            if was_update:
                result.updated_meals += 1
            else:
                result.imported_meals += 1

        elif parsed.event_type == "series":
            was_update = await _import_series(parsed, db, default_series_count)
            if was_update:
                result.updated_series += 1
            else:
                result.imported_series += 1

        else:
            was_update = await _import_event(parsed, db)
            if was_update:
                result.updated_events += 1
            else:
                result.imported_events += 1

    await db.commit()

    total = (
        result.imported_events + result.imported_series + result.imported_meals
        + result.updated_events + result.updated_series + result.updated_meals
    )
    logger.info(
        "cozi_sync.imported total={} new_events={} new_series={} new_meals={} "
        "upd_events={} upd_series={} upd_meals={} skipped={}",
        total,
        result.imported_events, result.imported_series, result.imported_meals,
        result.updated_events, result.updated_series, result.updated_meals,
        result.skipped,
    )
    return result


async def _import_meal(ev: _ParsedEvent, db: AsyncSession) -> bool:
    """Import or update a meal. Returns True if an existing record was updated."""
    existing = await _meal_by_cozi_uid(db, ev.uid) if ev.uid else None
    if not existing:
        existing = await _meal_fuzzy_match(db, ev)
    cook_id = ev.mapped_member_ids[0] if len(ev.mapped_member_ids) == 1 else None

    if existing:
        existing.name = ev.title
        existing.date = ev.start_dt.date()
        existing.description = ev.description
        existing.cook_member_id = cook_id
        if ev.uid:
            existing.cozi_uid = ev.uid
        await db.flush()
        return True

    db.add(
        Meal(
            date=ev.start_dt.date(),
            meal_type=MealType.dinner,
            name=ev.title,
            description=ev.description,
            recipe_url="",
            cook_member_id=cook_id,
            cozi_uid=ev.uid or None,
        )
    )
    await db.flush()
    return False


async def _import_series(ev: _ParsedEvent, db: AsyncSession, default_series_count: int) -> bool:
    """Import or update a recurring series. Returns True if an existing record was updated."""
    existing = await _series_by_cozi_uid(db, ev.uid) if ev.uid else None
    if not existing:
        existing = await _series_fuzzy_match(db, ev)

    if ev.is_multiday_allday:
        recurrence_type = RecurrenceType.daily
        interval = 1
        monthly_pattern = None
        series_start = ev.start_dt.date()
        series_end = ev.end_dt.date()
        if ev.end_dt.hour == 0 and ev.end_dt.minute == 0:
            series_end = series_end - timedelta(days=1)
        count = None
    else:
        recurrence_type = RecurrenceType(ev.advice.recurrence_type)
        interval = ev.advice.interval
        monthly_pattern = ev.advice.monthly_pattern
        series_start = ev.start_dt.date()
        count = _extract_rrule_count(ev.rrule)
        series_end = None if count else _extract_rrule_until_date(ev.rrule)
        if not count and not series_end:
            count = default_series_count
        if series_end and series_end <= series_start:
            series_end = None
            count = count or default_series_count

    was_update = bool(existing)

    if existing:
        existing.title = ev.title
        existing.description = ev.description
        existing.location = ev.location
        existing.all_day = ev.all_day
        existing.recurrence_type = recurrence_type
        existing.series_start = series_start
        existing.series_end = series_end or series_start
        existing.count = count
        existing.start_time_of_day = ev.start_dt.time()
        existing.end_time_of_day = ev.end_dt.time()
        existing.interval = interval
        existing.monthly_pattern = monthly_pattern
        if ev.uid:
            existing.cozi_uid = ev.uid
        await db.flush()
        # Regenerate non-exception occurrences
        await db.execute(
            sa_delete(AgendaEvent).where(
                and_(AgendaEvent.series_id == existing.id, ~AgendaEvent.is_exception)
            )
        )
        series = existing
    else:
        series = RecurrenceSeries(
            title=ev.title,
            description=ev.description,
            location=ev.location,
            all_day=ev.all_day,
            recurrence_type=recurrence_type,
            series_start=series_start,
            series_end=series_end or series_start,
            start_time_of_day=ev.start_dt.time(),
            end_time_of_day=ev.end_dt.time(),
            interval=interval,
            count=count,
            monthly_pattern=monthly_pattern,
            rrule=None,
            cozi_uid=ev.uid or None,
        )
        db.add(series)
        await db.flush()
        await set_junction_members(
            db, recurrence_series_members, "series_id", series.id, ev.mapped_member_ids
        )

    occurrence_dates = generate_occurrence_dates(
        recurrence_type=recurrence_type,
        series_start=series.series_start,
        series_end=series.series_end,
        interval=interval,
        count=count,
        monthly_pattern=monthly_pattern,
        rrule_string=None,
    )

    new_events = [
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
    db.add_all(new_events)
    await db.flush()

    if ev.mapped_member_ids:
        for ge in new_events:
            await set_junction_members(
                db, agenda_event_members, "event_id", ge.id, ev.mapped_member_ids
            )

    return was_update


async def _import_event(ev: _ParsedEvent, db: AsyncSession) -> bool:
    """Import or update a single event. Returns True if an existing record was updated."""
    existing = await _event_by_cozi_uid(db, ev.uid) if ev.uid else None
    if not existing:
        existing = await _event_fuzzy_match(db, ev)

    was_update = bool(existing)

    if existing:
        existing.title = ev.title
        existing.description = ev.description
        existing.location = ev.location
        existing.start_time = ev.start_dt
        existing.end_time = ev.end_dt
        existing.all_day = ev.all_day
        if ev.uid:
            existing.cozi_uid = ev.uid
        await db.flush()
        await set_junction_members(
            db, agenda_event_members, "event_id", existing.id, ev.mapped_member_ids
        )
    else:
        event = AgendaEvent(
            title=ev.title,
            description=ev.description,
            location=ev.location,
            start_time=ev.start_dt,
            end_time=ev.end_dt,
            all_day=ev.all_day,
            cozi_uid=ev.uid or None,
        )
        db.add(event)
        await db.flush()
        await set_junction_members(
            db, agenda_event_members, "event_id", event.id, ev.mapped_member_ids
        )

    return was_update
