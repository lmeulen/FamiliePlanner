"""Analyze a Cozi ICS feed and propose a mapping to FamiliePlanner.

This script does NOT import anything. It only reads ICS data and prints:
- feed statistics
- recurrence mapping advice
- example payloads for FamiliePlanner endpoints

Usage:
    python -m tools.cozi_import_advisor
    python -m tools.cozi_import_advisor --url "https://.../feed.ics"
    python -m tools.cozi_import_advisor --today
"""

from __future__ import annotations

import argparse
import asyncio
import re
from collections import Counter
from dataclasses import dataclass
from datetime import date, datetime, time
from typing import Any

import httpx
from icalendar import Calendar
from sqlalchemy import select

from app.config import COZI_ICS_URL
from app.database import AsyncSessionLocal
from app.models.family import FamilyMember


@dataclass
class MappingAdvice:
    recurrence_type: str | None
    interval: int
    monthly_pattern: str | None
    supported: bool
    reason: str


@dataclass
class FamilyMemberRecord:
    id: int
    name: str


@dataclass
class MealCandidate:
    uid: str
    title: str
    start: datetime
    end: datetime
    reason: str


def _to_int(value: Any, default: int = 1) -> int:
    try:
        if isinstance(value, list):
            return int(value[0])
        return int(value)
    except Exception:
        return default


def _normalize_rrule(event: Any) -> dict[str, list[Any]]:
    rrule = event.get("RRULE")
    if not rrule:
        return {}

    normalized: dict[str, list[Any]] = {}
    for key, value in rrule.items():
        key_str = str(key).upper()
        if isinstance(value, list):
            normalized[key_str] = value
        else:
            normalized[key_str] = [value]
    return normalized


def _rrule_to_string(rrule: dict[str, list[Any]]) -> str:
    if not rrule:
        return "(geen RRULE)"

    parts: list[str] = []
    for key in sorted(rrule.keys()):
        values = ",".join(str(v) for v in rrule[key])
        parts.append(f"{key}={values}")
    return ";".join(parts)


def _to_list(value: Any) -> list[Any]:
    if value is None:
        return []
    if isinstance(value, list):
        return value
    return [value]


def _extract_person_name(property_value: Any) -> str | None:
    if property_value is None:
        return None

    params = getattr(property_value, "params", None)
    if params and "CN" in params:
        cn = str(params["CN"]).strip()
        if cn:
            return cn

    raw = str(property_value).strip()
    if not raw:
        return None

    if raw.lower().startswith("mailto:"):
        raw = raw[7:]

    if "@" in raw:
        raw = raw.split("@", 1)[0]

    return raw.strip() or None


def _normalize_name(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "", value.casefold())


def _tokenize_name(value: str) -> list[str]:
    return [part for part in re.split(r"[^a-zA-Z0-9]+", value.casefold()) if part]


def _map_name_to_member_ids(name: str, family_members: list[FamilyMemberRecord]) -> list[int]:
    normalized = _normalize_name(name)
    if not normalized:
        return []

    exact_ids = [member.id for member in family_members if _normalize_name(member.name) == normalized]
    if exact_ids:
        return exact_ids

    # Group aliases (except 'all') map to all family members only when no exact match exists.
    group_aliases = {"iedereen", "everyone", "heelgezin", "gezin"}
    if normalized in group_aliases:
        return [member.id for member in family_members]

    # Fallback: match on first token (e.g. "Leo" against "Leo van Dijk")
    fallback_ids: list[int] = []
    for member in family_members:
        tokens = _tokenize_name(member.name)
        if tokens and tokens[0] == name.casefold().strip():
            fallback_ids.append(member.id)
    if fallback_ids:
        return fallback_ids

    return []


def _build_found_name_mapping(
    found_names: set[str],
    family_members: list[FamilyMemberRecord],
) -> dict[str, list[int]]:
    return {name: _map_name_to_member_ids(name, family_members) for name in sorted(found_names)}


async def _load_family_members() -> list[FamilyMemberRecord]:
    try:
        async with AsyncSessionLocal() as db:
            result = await db.execute(select(FamilyMember).order_by(FamilyMember.id))
            rows = result.scalars().all()
            return [FamilyMemberRecord(id=row.id, name=row.name) for row in rows]
    except Exception:
        return []


def _extract_members_from_summary(summary: str) -> tuple[list[str], str]:
    """Extract member names from SUMMARY prefix 'Name1/Name2: Title'."""
    raw = summary.strip()
    match = re.match(r"^([^:]+):\s*(.*)$", raw)
    if not match:
        return [], raw

    prefix = match.group(1).strip()
    title = match.group(2).strip()

    # Only treat as member-prefix when slash-separated or explicit group token appears.
    if "/" not in prefix and prefix.lower() not in {"all", "iedereen", "everyone"}:
        return [], raw

    members = [part.strip() for part in prefix.split("/") if part.strip()]
    if not members:
        return [], raw

    cleaned_title = title or raw
    return members, cleaned_title


def _extract_start_end(event: Any) -> tuple[datetime, datetime, bool]:
    dtstart = event.decoded("DTSTART")
    dtend = event.get("DTEND")

    if isinstance(dtstart, date) and not isinstance(dtstart, datetime):
        start_dt = datetime.combine(dtstart, time.min)
        if dtend:
            decoded_end = event.decoded("DTEND")
            if isinstance(decoded_end, date) and not isinstance(decoded_end, datetime):
                end_date_exclusive = decoded_end
                end_dt = datetime.combine(end_date_exclusive, time.min)
            else:
                end_dt = decoded_end
        else:
            end_dt = start_dt
        return start_dt, end_dt, True

    start_dt = dtstart
    if dtend:
        end_dt = event.decoded("DTEND")
    else:
        end_dt = start_dt
    return start_dt, end_dt, False


def _map_rrule_to_familieplanner(rrule: dict[str, list[Any]]) -> MappingAdvice:
    if not rrule:
        return MappingAdvice(None, 1, None, True, "Single event")

    freq = str(rrule.get("FREQ", [""])[0]).upper()
    interval = _to_int(rrule.get("INTERVAL", [1])[0], default=1)
    byday_values = [str(v).upper() for v in rrule.get("BYDAY", [])]

    if freq == "DAILY":
        if interval == 2:
            return MappingAdvice("every_other_day", 1, None, True, "Daily with interval 2")
        return MappingAdvice("daily", interval, None, True, "Daily recurrence")

    if freq == "WEEKLY":
        weekdays = {"MO", "TU", "WE", "TH", "FR"}
        if interval == 1 and set(byday_values) == weekdays:
            return MappingAdvice("weekdays", 1, None, True, "Weekdays pattern")
        if interval == 2 and not byday_values:
            return MappingAdvice("biweekly", 1, None, True, "Biweekly recurrence")
        return MappingAdvice("weekly", interval, None, True, "Weekly recurrence")

    if freq == "MONTHLY":
        monthly_pattern = None
        if byday_values:
            token = byday_values[0]
            ord_map = {
                "1": "first",
                "2": "second",
                "3": "third",
                "4": "fourth",
                "-1": "last",
            }
            day_map = {
                "MO": "monday",
                "TU": "tuesday",
                "WE": "wednesday",
                "TH": "thursday",
                "FR": "friday",
                "SA": "saturday",
                "SU": "sunday",
            }

            prefix = ""
            day = token
            if len(token) > 2:
                prefix = token[:-2]
                day = token[-2:]
            if prefix in ord_map and day in day_map:
                monthly_pattern = f"{ord_map[prefix]}_{day_map[day]}"

        return MappingAdvice("monthly", interval, monthly_pattern, True, "Monthly recurrence")

    if freq == "YEARLY":
        return MappingAdvice("yearly", interval, None, True, "Yearly recurrence")

    return MappingAdvice(None, interval, None, False, f"Unsupported FREQ '{freq}'")


def _detect_meal_candidate(event: Any, title: str) -> tuple[bool, str, datetime | None, datetime | None]:
    try:
        start_dt, end_dt, all_day = _extract_start_end(event)
    except Exception:
        return False, "invalid date/time", None, None

    if all_day:
        return False, "all-day event", None, None

    start_dt = start_dt.replace(tzinfo=None) if start_dt.tzinfo else start_dt
    end_dt = end_dt.replace(tzinfo=None) if end_dt.tzinfo else end_dt
    _ = title
    is_exact_dinner_slot = (
        start_dt.hour == 18
        and start_dt.minute == 0
        and start_dt.second == 0
        and end_dt.hour == 20
        and end_dt.minute == 0
        and end_dt.second == 0
        and start_dt.date() == end_dt.date()
    )

    if is_exact_dinner_slot:
        return True, "exact tijdslot 18:00-20:00", start_dt, end_dt

    return False, "niet exact 18:00-20:00", start_dt, end_dt


def _build_event_preview(
    event: Any,
    advice: MappingAdvice,
    name_to_member_ids: dict[str, list[int]],
) -> dict[str, Any]:
    start_dt, end_dt, all_day = _extract_start_end(event)
    summary_raw = str(event.get("SUMMARY", "")).strip() or "(zonder titel)"
    summary_members, summary_title = _extract_members_from_summary(summary_raw)
    mapped_member_ids = sorted(
        {member_id for name in summary_members for member_id in name_to_member_ids.get(name, [])}
    )
    description = str(event.get("DESCRIPTION", "") or "")
    location = str(event.get("LOCATION", "") or "")
    original_ics = event.to_ical().decode("utf-8", errors="replace")

    event_payload = {
        "title": summary_title,
        "description": description,
        "location": location,
        "start_time": start_dt.isoformat(),
        "end_time": end_dt.isoformat(),
        "all_day": all_day,
        "member_ids": mapped_member_ids,
        "color": "#4ECDC4",
    }

    series_payload = None
    if advice.recurrence_type:
        series_payload = {
            "title": summary_title,
            "description": description,
            "location": location,
            "all_day": all_day,
            "member_ids": mapped_member_ids,
            "color": "#4ECDC4",
            "recurrence_type": advice.recurrence_type,
            "series_start": start_dt.date().isoformat(),
            "series_end": None,
            "start_time_of_day": start_dt.time().isoformat(timespec="seconds"),
            "end_time_of_day": end_dt.time().isoformat(timespec="seconds"),
            "interval": advice.interval,
            "count": None,
            "monthly_pattern": advice.monthly_pattern,
            "rrule": None,
        }

    return {
        "uid": str(event.get("UID", "")),
        "summary_members": summary_members,
        "mapped_member_ids": mapped_member_ids,
        "original_ics": original_ics,
        "event_payload": event_payload,
        "series_payload": series_payload,
    }


def _print_recommendations(
    total_events: int,
    recurring_events: int,
    unsupported_recurring: int,
    recurrence_counter: Counter[str],
    raw_rrule_counter: Counter[str],
    rrule_mapping_counter: dict[str, Counter[str]],
    family_member_counter: Counter[str],
    found_name_mapping: dict[str, list[int]],
    family_members: list[FamilyMemberRecord],
    unmapped_field_counter: Counter[str],
    meal_candidates: list[MealCandidate],
    previews: list[dict[str, Any]],
) -> None:
    print("=" * 72)
    print("Cozi → FamiliePlanner importadvies (analyse, GEEN import)")
    print("=" * 72)
    print(f"Totaal VEVENT items: {total_events}")
    print(f"Herhalende events (RRULE): {recurring_events}")
    print(f"Niet-ondersteunde herhalingen: {unsupported_recurring}")
    print()

    print("Recurrence-mapping gevonden in feed:")
    if recurrence_counter:
        for key, count in recurrence_counter.most_common():
            print(f"- {key}: {count}")
    else:
        print("- Geen herhalingen gevonden")
    print()

    print("RRULE -> FamiliePlanner herhalingspatroon mapping:")
    if rrule_mapping_counter:
        for pattern, _ in raw_rrule_counter.most_common():
            mappings = rrule_mapping_counter.get(pattern, Counter())
            mapping_parts = [f"{mapping} ({mapping_count}x)" for mapping, mapping_count in mappings.most_common()]
            mapping_text = ", ".join(mapping_parts) if mapping_parts else "onbekend"
            print(f"- {pattern} -> {mapping_text}")
    else:
        print("- Geen RRULE mappings gevonden")
    print()

    print("Gezinsleden (gevonden in ICS metadata + SUMMARY prefix):")
    if family_member_counter:
        for member_name, count in family_member_counter.most_common():
            print(f"- {member_name}: {count}x")
    else:
        print("- Geen namen gevonden via ATTENDEE/ORGANIZER/SUMMARY")
    print()

    print("Mapping gevonden gezinsleden -> FamiliePlanner member_ids:")
    if found_name_mapping:
        if family_members:
            members_index = {member.id: member.name for member in family_members}
            for found_name, member_ids in found_name_mapping.items():
                if member_ids:
                    mapped_names = ", ".join(
                        f"{member_id} ({members_index.get(member_id, '?')})" for member_id in member_ids
                    )
                    print(f"- {found_name} -> [{mapped_names}]")
                else:
                    print(f"- {found_name} -> [geen match]")
        else:
            print("- Geen familieleden uit database geladen; mapping niet mogelijk")
    else:
        print("- Geen gevonden namen om te mappen")
    print()

    print("Aanbevolen veldmapping naar FamiliePlanner:")
    print("- SUMMARY      -> title (zonder '<gezinsleden>: ' prefix)")
    print("- DESCRIPTION  -> description")
    print("- LOCATION     -> location")
    print("- DTSTART      -> start_time / series_start + start_time_of_day")
    print("- DTEND        -> end_time / end_time_of_day")
    print("- All-day DATE -> all_day=True + start/end op 00:00")
    print("- RRULE        -> recurrence_type / interval / monthly_pattern")
    print("- UID          -> extern referentieveld in importlog (niet in model)")
    print("- COLOR        -> default '#4ECDC4' (Cozi ICS levert meestal geen kleur)")
    print("- SUMMARY prefix '<naam>/<naam>: ' -> mapped member_ids waar mogelijk")
    print("- Gezinsleden  -> member_ids handmatig of via eigen mappingtabel")
    print()

    print("Niet gemapte veldnamen uit ICS (VEVENT):")
    if unmapped_field_counter:
        for field_name, count in unmapped_field_counter.most_common():
            print(f"- {field_name}: {count}x")
    else:
        print("- Geen niet-gemapte veldnamen gevonden")
    print()

    print("Mogelijke Cozi Meal-items (te importeren als FamiliePlanner diner):")
    if meal_candidates:
        print(f"- Totaal herkend: {len(meal_candidates)}")
        for candidate in meal_candidates[:20]:
            meal_payload = {
                "date": candidate.start.date().isoformat(),
                "meal_type": "dinner",
                "name": candidate.title,
                "description": "",
                "recipe_url": "",
                "cook_member_id": None,
            }
            print(
                f"- {candidate.start.strftime('%Y-%m-%d %H:%M')} | {candidate.title} | "
                f"uid={candidate.uid} | {candidate.reason}"
            )
            print(f"  POST /api/meals payload: {meal_payload}")
    else:
        print("- Geen duidelijke meal-items herkend")
    print()

    if unsupported_recurring:
        print("Let op:")
        print("- Er zijn RRULE-patronen die niet 1-op-1 op RecurrenceType mappen.")
        print("- Advies: importeer die als losse events of gebruik raw rrule string.")
        print()

    print("Voorbeeldpayloads (eerste events):")
    for idx, preview in enumerate(previews, start=1):
        print(f"\n[{idx}]")
        print("UID:")
        print(preview["uid"])
        print("---------------")
        print("Originele ICS data:")
        print(preview["original_ics"])
        print("---------------")
        print("Voorgestelde POST payload(s):")
        print(f"POST /api/agenda/ payload: {preview['event_payload']}")
        if preview["series_payload"]:
            print(f"POST /api/agenda/series payload: {preview['series_payload']}")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Analyze Cozi ICS and print FamiliePlanner import mapping advice.")
    parser.add_argument("--url", default=COZI_ICS_URL, help="ICS URL to analyze (default: COZI_ICS_URL from .env)")
    parser.add_argument(
        "--today",
        action="store_true",
        help="Process only events with DTSTART on today's date.",
    )
    parser.add_argument(
        "--max-examples",
        type=int,
        default=5,
        help="Number of example payload previews to print",
    )
    return parser.parse_args()


async def run() -> None:
    args = parse_args()

    if not args.url:
        print("Error: No Cozi ICS URL configured.")
        print("Set COZI_ICS_URL in .env or use --url argument.")
        return

    async with httpx.AsyncClient(timeout=20) as client:
        response = await client.get(args.url)
        response.raise_for_status()
        ics_content = response.text

    calendar = Calendar.from_ical(ics_content)

    events = [component for component in calendar.walk() if component.name == "VEVENT"]
    if args.today:
        today = date.today()

        def _is_today(component: Any) -> bool:
            dtstart = component.decoded("DTSTART")
            if isinstance(dtstart, datetime):
                return dtstart.date() == today
            if isinstance(dtstart, date):
                return dtstart == today
            return False

        events = [component for component in events if _is_today(component)]

    recurrence_counter: Counter[str] = Counter()
    raw_rrule_counter: Counter[str] = Counter()
    rrule_mapping_counter: dict[str, Counter[str]] = {}
    family_member_counter: Counter[str] = Counter()
    unmapped_field_counter: Counter[str] = Counter()
    recurring_events = 0
    unsupported_recurring = 0
    previews: list[dict[str, Any]] = []
    found_names: set[str] = set()
    meal_candidates: list[MealCandidate] = []

    family_members = await _load_family_members()
    mapped_ics_fields = {
        "SUMMARY",
        "DESCRIPTION",
        "LOCATION",
        "DTSTART",
        "DTEND",
        "RRULE",
        "UID",
        "COLOR",
    }

    for event in events:
        for event_field in event.keys():
            field_name = str(event_field).upper()
            if field_name not in mapped_ics_fields:
                unmapped_field_counter[field_name] += 1

        rrule = _normalize_rrule(event)
        pattern = ""
        if rrule:
            pattern = _rrule_to_string(rrule)
            raw_rrule_counter[pattern] += 1

        for attendee in _to_list(event.get("ATTENDEE")):
            name = _extract_person_name(attendee)
            if name:
                family_member_counter[name] += 1
                found_names.add(name)

        organizer = event.get("ORGANIZER")
        organizer_name = _extract_person_name(organizer)
        if organizer_name:
            family_member_counter[organizer_name] += 1
            found_names.add(organizer_name)

        summary_raw = str(event.get("SUMMARY", "") or "")
        summary_members, _ = _extract_members_from_summary(summary_raw)
        for member_name in summary_members:
            family_member_counter[member_name] += 1
            found_names.add(member_name)

    found_name_mapping = _build_found_name_mapping(found_names, family_members)

    for event in events:
        rrule = _normalize_rrule(event)
        pattern = _rrule_to_string(rrule) if rrule else ""
        advice = _map_rrule_to_familieplanner(rrule)
        summary_raw = str(event.get("SUMMARY", "") or "")
        _, summary_title = _extract_members_from_summary(summary_raw)

        is_meal, reason, start_dt, end_dt = _detect_meal_candidate(event, summary_title)
        if is_meal and start_dt and end_dt:
            meal_candidates.append(
                MealCandidate(
                    uid=str(event.get("UID", "")),
                    title=summary_title,
                    start=start_dt,
                    end=end_dt,
                    reason=reason,
                )
            )

        if pattern:
            mapping_label = advice.recurrence_type if advice.recurrence_type else f"unsupported ({advice.reason})"
            rrule_mapping_counter.setdefault(pattern, Counter())[mapping_label] += 1

        if advice.recurrence_type:
            recurring_events += 1
            recurrence_counter[advice.recurrence_type] += 1
        elif rrule:
            recurring_events += 1
            unsupported_recurring += 1
            recurrence_counter[f"unsupported ({advice.reason})"] += 1

        if len(previews) < max(1, args.max_examples):
            previews.append(_build_event_preview(event, advice, found_name_mapping))

    _print_recommendations(
        total_events=len(events),
        recurring_events=recurring_events,
        unsupported_recurring=unsupported_recurring,
        recurrence_counter=recurrence_counter,
        raw_rrule_counter=raw_rrule_counter,
        rrule_mapping_counter=rrule_mapping_counter,
        family_member_counter=family_member_counter,
        found_name_mapping=found_name_mapping,
        family_members=family_members,
        unmapped_field_counter=unmapped_field_counter,
        meal_candidates=meal_candidates,
        previews=previews,
    )


def main() -> None:
    asyncio.run(run())


if __name__ == "__main__":
    main()
