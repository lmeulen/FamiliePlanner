"""One-way sync of FamiliePlanner agenda events into a Google Calendar.

Outbound only: Google is a read-only mirror and nothing is ever imported back.
Pushes go through an outbox queue so a failing API call can never break a
request. Every pushed event carries its FamiliePlanner id twice: in
``extendedProperties.private`` (queryable) and as a visible description footer.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from datetime import date, datetime, timedelta
from typing import Any

from loguru import logger
from sqlalchemy import and_, select
from sqlalchemy import delete as sa_delete
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.agenda import AgendaEvent, RecurrenceSeries
from app.models.family import FamilyMember
from app.models.google_sync import GoogleSyncLink, GoogleSyncQueue
from app.models.settings import AppSetting
from app.services.google_calendar import (
    GoogleCalendarClient,
    GoogleCalendarNotConfigured,
    credentials_available,
    credentials_path,
    is_rate_limited,
)
from app.utils.google_colors import DEFAULT_COLOR_ID, assign_member_colors
from app.utils.recurrence import build_rrule_string
from app.utils.timezone import UTC, app_timezone_name, now_local, to_aware, today_local

ENTITY_EVENT = "event"
ENTITY_SERIES = "series"
ENTITY_INSTANCE = "instance_override"

OP_UPSERT = "upsert"
OP_DELETE = "delete"

MAX_ATTEMPTS = 10
BATCH_SIZE = 50
PAST_WINDOW_DAYS = 30
FUTURE_WINDOW_DAYS = 365


# ── Configuration ───────────────────────────────────────────────────────────


@dataclass
class GoogleSyncConfig:
    enabled: bool = False
    calendar_id: str = ""
    member_colors: dict[str, str] = field(default_factory=dict)
    title_avatars: bool = True
    default_color_id: str = DEFAULT_COLOR_ID
    timezone: str = "Europe/Amsterdam"
    app_base_url: str = ""

    @property
    def usable(self) -> bool:
        return self.enabled and bool(self.calendar_id) and credentials_available()

    def blocking_reason(self) -> str | None:
        """Human-readable reason why sync cannot run, or None when it can."""
        if not self.calendar_id:
            return "Er is nog geen Google Calendar ID opgeslagen. Vul het in en klik eerst op Opslaan."
        if not credentials_available():
            return (
                f"Service-account sleutel niet gevonden op {credentials_path()}. "
                "Plaats het JSON-bestand daar of zet GOOGLE_SERVICE_ACCOUNT_FILE."
            )
        if not self.enabled:
            return "Google sync staat uit. Zet de schakelaar aan en klik op Opslaan."
        return None


async def _get_setting(db: AsyncSession, key: str, default: str = "") -> str:
    row = await db.get(AppSetting, key)
    return row.value if row else default


async def get_google_config(db: AsyncSession) -> GoogleSyncConfig:
    raw_colors = await _get_setting(db, "google_sync_member_colors", "{}")
    try:
        member_colors = {str(k): str(v) for k, v in json.loads(raw_colors or "{}").items()}
    except (ValueError, AttributeError):
        member_colors = {}

    return GoogleSyncConfig(
        enabled=(await _get_setting(db, "google_sync_enabled", "false")).lower() in ("1", "true"),
        calendar_id=await _get_setting(db, "google_calendar_id", ""),
        member_colors=member_colors,
        title_avatars=(await _get_setting(db, "google_sync_title_avatars", "true")).lower() in ("1", "true"),
        default_color_id=await _get_setting(db, "google_sync_default_color", DEFAULT_COLOR_ID),
        timezone=app_timezone_name(),
        app_base_url=(await _get_setting(db, "app_base_url", "")).rstrip("/"),
    )


async def ensure_member_colors(db: AsyncSession) -> dict[str, str]:
    """Assign a stable Google colour per family member, keeping existing choices."""
    result = await db.execute(select(FamilyMember).order_by(FamilyMember.id))
    members = list(result.scalars().all())

    config = await get_google_config(db)
    mapping = dict(config.member_colors)

    missing = [(m.id, m.color) for m in members if str(m.id) not in mapping]
    if missing:
        # assign_member_colors already guarantees distinct ids among the members it is given.
        mapping.update(assign_member_colors(missing))
        await _set_setting(db, "google_sync_member_colors", json.dumps(mapping))

    return mapping


async def _set_setting(db: AsyncSession, key: str, value: str) -> None:
    row = await db.get(AppSetting, key)
    if row:
        row.value = value
    else:
        db.add(AppSetting(key=key, value=value))
    await db.commit()


# ── Payload building (pure) ─────────────────────────────────────────────────


def _members_of(members: list[FamilyMember]) -> list[FamilyMember]:
    return sorted(members or [], key=lambda m: m.id)


def _title_for(title: str, members: list[FamilyMember], config: GoogleSyncConfig) -> str:
    if not config.title_avatars or not members:
        return title
    avatars = "".join(m.avatar for m in members if m.avatar)
    return f"{avatars} {title}".strip() if avatars else title


def _color_for(members: list[FamilyMember], config: GoogleSyncConfig) -> str:
    if not members:
        return config.default_color_id
    # Primary member = lowest id, so the colour is stable as membership changes.
    return config.member_colors.get(str(members[0].id), config.default_color_id)


def _description_for(
    description: str,
    members: list[FamilyMember],
    entity_key: str,
    config: GoogleSyncConfig,
    deep_link_path: str = "",
) -> str:
    lines = [description.strip()] if description and description.strip() else []
    lines.append("")
    lines.append("—")

    names = ", ".join(m.name for m in members)
    lines.append(f"FamiliePlanner · {names}" if names else "FamiliePlanner")

    if config.app_base_url and deep_link_path:
        lines.append(f"{config.app_base_url}{deep_link_path}")

    lines.append(f"fp-id: {entity_key}")
    return "\n".join(lines)


def _timed(dt: datetime, config: GoogleSyncConfig) -> dict:
    """Naive stored values are app-local wall clock; send them verbatim with a TZID."""
    return {"dateTime": dt.strftime("%Y-%m-%dT%H:%M:%S"), "timeZone": config.timezone}


def _all_day(start: date, end: date) -> tuple[dict, dict]:
    """Google all-day events use date-only fields with an exclusive end date."""
    return {"date": start.isoformat()}, {"date": (end + timedelta(days=1)).isoformat()}


def _extended_properties(entity_key: str, entity_type: str, members: list[FamilyMember]) -> dict:
    return {
        "private": {
            "fp_managed": "1",
            "fp_id": entity_key,
            "fp_type": entity_type,
            "fp_members": ",".join(str(m.id) for m in members),
        }
    }


def build_event_payload(event: AgendaEvent, config: GoogleSyncConfig) -> dict:
    """Google event body for a standalone (non-series) FamiliePlanner event."""
    members = _members_of(event.members)
    entity_key = event_key(event.id)

    if event.all_day:
        start, end = _all_day(event.start_time.date(), event.end_time.date())
    else:
        start, end = _timed(event.start_time, config), _timed(event.end_time, config)

    return {
        "summary": _title_for(event.title, members, config),
        "description": _description_for(
            event.description or "", members, entity_key, config, f"/agenda?event={event.id}"
        ),
        "location": event.location or "",
        "start": start,
        "end": end,
        "colorId": _color_for(members, config),
        "transparency": "transparent",
        "guestsCanModify": False,
        "reminders": {"useDefault": False, "overrides": []},
        "extendedProperties": _extended_properties(entity_key, ENTITY_EVENT, members),
    }


def build_series_payload(series: RecurrenceSeries, base_event: AgendaEvent, config: GoogleSyncConfig) -> dict:
    """Google recurring event body: one API object for the whole series."""
    members = _members_of(series.members)
    entity_key = series_key(series.id)

    if series.all_day:
        start, end = _all_day(base_event.start_time.date(), base_event.end_time.date())
    else:
        start = _timed(base_event.start_time, config)
        end = _timed(base_event.end_time, config)

    until_utc = None
    if series.series_end:
        end_date = series.series_end.date() if isinstance(series.series_end, datetime) else series.series_end
        until_utc = to_aware(datetime.combine(end_date, datetime.max.time().replace(microsecond=0))).astimezone(UTC)

    rrule = build_rrule_string(
        recurrence_type=series.recurrence_type,
        interval=series.interval or 1,
        monthly_pattern=series.monthly_pattern,
        count=series.count,
        until_utc=until_utc,
    )

    return {
        "summary": _title_for(series.title, members, config),
        "description": _description_for(series.description or "", members, entity_key, config, "/agenda"),
        "location": series.location or "",
        "start": start,
        "end": end,
        "recurrence": [rrule],
        "colorId": _color_for(members, config),
        "transparency": "transparent",
        "guestsCanModify": False,
        "reminders": {"useDefault": False, "overrides": []},
        "extendedProperties": _extended_properties(entity_key, ENTITY_SERIES, members),
    }


def build_instance_payload(event: AgendaEvent, config: GoogleSyncConfig) -> dict:
    """Patch body for a single modified occurrence of a recurring series."""
    members = _members_of(event.members)
    entity_key = instance_key(event.series_id or 0, event.start_time.date())

    if event.all_day:
        start, end = _all_day(event.start_time.date(), event.end_time.date())
    else:
        start, end = _timed(event.start_time, config), _timed(event.end_time, config)

    return {
        "summary": _title_for(event.title, members, config),
        "description": _description_for(
            event.description or "", members, entity_key, config, f"/agenda?event={event.id}"
        ),
        "location": event.location or "",
        "start": start,
        "end": end,
        "colorId": _color_for(members, config),
        "extendedProperties": _extended_properties(entity_key, ENTITY_INSTANCE, members),
    }


def content_hash(payload: dict) -> str:
    return hashlib.sha256(json.dumps(payload, sort_keys=True, ensure_ascii=False).encode("utf-8")).hexdigest()


# ── Entity keys ─────────────────────────────────────────────────────────────


def event_key(event_id: int) -> str:
    return f"event:{event_id}"


def series_key(series_id: int) -> str:
    return f"series:{series_id}"


def instance_key(series_id: int, occurrence: date) -> str:
    return f"series:{series_id}:{occurrence.isoformat()}"


# ── Queue ───────────────────────────────────────────────────────────────────


async def enqueue(db: AsyncSession, entity_type: str, entity_key: str, operation: str) -> None:
    """Queue one push. Repeated edits of the same entity collapse into one job."""
    result = await db.execute(
        select(GoogleSyncQueue).where(
            and_(GoogleSyncQueue.entity_type == entity_type, GoogleSyncQueue.entity_key == entity_key)
        )
    )
    row = result.scalar_one_or_none()

    if row:
        row.operation = operation
        row.attempts = 0
        row.next_attempt_at = None
        row.last_error = None
    else:
        db.add(
            GoogleSyncQueue(
                entity_type=entity_type,
                entity_key=entity_key,
                operation=operation,
                attempts=0,
                next_attempt_at=None,
            )
        )


async def enqueue_event(db: AsyncSession, event: AgendaEvent, operation: str = OP_UPSERT) -> None:
    """Queue a standalone event, or the modified occurrence of a series."""
    if event.series_id and event.is_exception:
        await enqueue(db, ENTITY_INSTANCE, instance_key(event.series_id, event.start_time.date()), operation)
    elif not event.series_id:
        await enqueue(db, ENTITY_EVENT, event_key(event.id), operation)


async def enqueue_series(db: AsyncSession, series_id: int, operation: str = OP_UPSERT) -> None:
    await enqueue(db, ENTITY_SERIES, series_key(series_id), operation)


async def queue_depth(db: AsyncSession) -> int:
    result = await db.execute(select(GoogleSyncQueue))
    return len(list(result.scalars().all()))


# ── Processing ──────────────────────────────────────────────────────────────


@dataclass
class SyncResult:
    processed: int = 0
    created: int = 0
    updated: int = 0
    deleted: int = 0
    unchanged: int = 0
    failed: int = 0
    skipped: int = 0


async def _get_link(db: AsyncSession, entity_type: str, entity_key: str) -> GoogleSyncLink | None:
    result = await db.execute(
        select(GoogleSyncLink).where(
            and_(GoogleSyncLink.entity_type == entity_type, GoogleSyncLink.entity_key == entity_key)
        )
    )
    return result.scalar_one_or_none()


async def _load_event(db: AsyncSession, event_id: int) -> AgendaEvent | None:
    result = await db.execute(
        select(AgendaEvent).options(selectinload(AgendaEvent.members)).where(AgendaEvent.id == event_id)
    )
    return result.scalar_one_or_none()


async def _load_series(db: AsyncSession, series_id: int) -> RecurrenceSeries | None:
    result = await db.execute(
        select(RecurrenceSeries).options(selectinload(RecurrenceSeries.members)).where(RecurrenceSeries.id == series_id)
    )
    return result.scalar_one_or_none()


async def _series_base_event(db: AsyncSession, series_id: int) -> AgendaEvent | None:
    result = await db.execute(
        select(AgendaEvent)
        .options(selectinload(AgendaEvent.members))
        .where(AgendaEvent.series_id == series_id)
        .order_by(AgendaEvent.start_time)
        .limit(1)
    )
    return result.scalar_one_or_none()


async def _exception_event(db: AsyncSession, series_id: int, occurrence: date) -> AgendaEvent | None:
    day_start = datetime.combine(occurrence, datetime.min.time())
    day_end = datetime.combine(occurrence, datetime.max.time())
    result = await db.execute(
        select(AgendaEvent)
        .options(selectinload(AgendaEvent.members))
        .where(
            and_(
                AgendaEvent.series_id == series_id,
                AgendaEvent.start_time >= day_start,
                AgendaEvent.start_time <= day_end,
            )
        )
        .limit(1)
    )
    return result.scalar_one_or_none()


async def _upsert(
    db: AsyncSession,
    client: GoogleCalendarClient,
    config: GoogleSyncConfig,
    entity_type: str,
    entity_key: str,
    payload: dict,
    result: SyncResult,
) -> None:
    link = await _get_link(db, entity_type, entity_key)
    new_hash = content_hash(payload)

    if link and link.google_calendar_id == config.calendar_id and link.content_hash == new_hash:
        result.unchanged += 1
        return

    if link and link.google_calendar_id == config.calendar_id:
        google_event = await client.patch(link.google_event_id, payload)
        result.updated += 1
    else:
        google_event = await client.insert(payload)
        result.created += 1
        if link:
            await db.delete(link)
            link = None

    if link is None:
        link = GoogleSyncLink(entity_type=entity_type, entity_key=entity_key)
        db.add(link)

    link.google_event_id = google_event["id"]
    link.google_calendar_id = config.calendar_id
    link.content_hash = new_hash
    link.last_synced_at = now_local()
    link.last_error = None


async def _upsert_instance(
    db: AsyncSession,
    client: GoogleCalendarClient,
    config: GoogleSyncConfig,
    entity_key: str,
    series_id: int,
    occurrence: date,
    result: SyncResult,
) -> None:
    """Patch one occurrence of a Google recurring event."""
    parent = await _get_link(db, ENTITY_SERIES, series_key(series_id))
    if parent is None:
        # Parent not pushed yet; queue it and retry this instance afterwards.
        await enqueue_series(db, series_id)
        result.skipped += 1
        return

    event = await _exception_event(db, series_id, occurrence)
    time_min = to_aware(datetime.combine(occurrence, datetime.min.time())).astimezone(UTC).isoformat()
    time_max = to_aware(datetime.combine(occurrence + timedelta(days=1), datetime.min.time())).astimezone(UTC)
    instances = await client.instances(parent.google_event_id, time_min, time_max.isoformat())

    if not instances:
        result.skipped += 1
        return

    instance = instances[0]

    if event is None:
        # Occurrence was deleted locally: cancel just this instance.
        await client.delete(instance["id"])
        result.deleted += 1
        link = await _get_link(db, ENTITY_INSTANCE, entity_key)
        if link:
            await db.delete(link)
        return

    payload = build_instance_payload(event, config)
    new_hash = content_hash(payload)
    link = await _get_link(db, ENTITY_INSTANCE, entity_key)

    if link and link.google_calendar_id == config.calendar_id and link.content_hash == new_hash:
        result.unchanged += 1
        return

    await client.patch(instance["id"], payload)
    result.updated += 1

    if link is None:
        link = GoogleSyncLink(entity_type=ENTITY_INSTANCE, entity_key=entity_key)
        db.add(link)

    link.google_event_id = instance["id"]
    link.google_calendar_id = config.calendar_id
    link.content_hash = new_hash
    link.recurring_event_id = parent.google_event_id
    link.original_start = occurrence.isoformat()
    link.last_synced_at = now_local()
    link.last_error = None


async def _delete(
    db: AsyncSession,
    client: GoogleCalendarClient,
    entity_type: str,
    entity_key: str,
    result: SyncResult,
) -> None:
    link = await _get_link(db, entity_type, entity_key)
    if link is None:
        result.skipped += 1
        return

    await client.delete(link.google_event_id)
    await db.delete(link)
    result.deleted += 1


async def _process_job(
    db: AsyncSession,
    client: GoogleCalendarClient,
    config: GoogleSyncConfig,
    job: GoogleSyncQueue,
    result: SyncResult,
) -> None:
    if job.operation == OP_DELETE:
        await _delete(db, client, job.entity_type, job.entity_key, result)
        return

    if job.entity_type == ENTITY_EVENT:
        event_id = int(job.entity_key.split(":")[1])
        event = await _load_event(db, event_id)
        if event is None or event.series_id is not None:
            await _delete(db, client, ENTITY_EVENT, job.entity_key, result)
            return
        await _upsert(db, client, config, ENTITY_EVENT, job.entity_key, build_event_payload(event, config), result)
        return

    if job.entity_type == ENTITY_SERIES:
        series_id = int(job.entity_key.split(":")[1])
        series = await _load_series(db, series_id)
        base_event = await _series_base_event(db, series_id) if series else None
        if series is None or base_event is None:
            await _delete(db, client, ENTITY_SERIES, job.entity_key, result)
            return
        payload = build_series_payload(series, base_event, config)
        await _upsert(db, client, config, ENTITY_SERIES, job.entity_key, payload, result)
        return

    if job.entity_type == ENTITY_INSTANCE:
        _, series_id_raw, occurrence_raw = job.entity_key.split(":")
        await _upsert_instance(
            db, client, config, job.entity_key, int(series_id_raw), date.fromisoformat(occurrence_raw), result
        )
        return

    result.skipped += 1


async def process_queue(db: AsyncSession, client: GoogleCalendarClient | None = None) -> SyncResult:
    """Drain due queue jobs. Failures are retried with exponential backoff."""
    result = SyncResult()
    config = await get_google_config(db)
    if not config.usable:
        return result

    if await _is_manual_purge_cleared(db):
        logger.info("Google sync queue suppressed for a short window after a manual calendar purge.")
        return result

    client = client or GoogleCalendarClient(config.calendar_id)
    now = now_local()

    jobs_result = await db.execute(
        select(GoogleSyncQueue)
        .where(
            (GoogleSyncQueue.next_attempt_at.is_(None)) | (GoogleSyncQueue.next_attempt_at <= now),
        )
        .order_by(GoogleSyncQueue.id)
        .limit(BATCH_SIZE)
    )
    jobs = list(jobs_result.scalars().all())

    for job in jobs:
        try:
            await _process_job(db, client, config, job, result)
            await db.delete(job)
            result.processed += 1
        except GoogleCalendarNotConfigured:
            raise
        except Exception as exc:  # noqa: BLE001 - one bad job must not stall the queue
            job.attempts += 1
            job.last_error = f"{type(exc).__name__}: {exc}"[:500]
            backoff_minutes = min(2**job.attempts, 360)
            job.next_attempt_at = now + timedelta(minutes=backoff_minutes)
            result.failed += 1

            if job.attempts >= MAX_ATTEMPTS:
                logger.error(
                    "Google sync job parked after repeated failures. Inspect the calendar configuration.",
                    entity_type=job.entity_type,
                    entity_key=job.entity_key,
                    attempts=job.attempts,
                    error=job.last_error,
                )
            else:
                logger.warning(
                    "Google sync job failed and will be retried.",
                    entity_type=job.entity_type,
                    entity_key=job.entity_key,
                    attempts=job.attempts,
                    retry_in_minutes=backoff_minutes,
                    rate_limited=is_rate_limited(exc),
                )

    await db.commit()
    return result


# ── Backfill & reconciliation ───────────────────────────────────────────────


async def enqueue_all(db: AsyncSession, past_days: int = PAST_WINDOW_DAYS) -> int:
    """Queue every event and series inside the sync window."""
    today = today_local()
    window_start = datetime.combine(today - timedelta(days=past_days), datetime.min.time())
    window_end = datetime.combine(today + timedelta(days=FUTURE_WINDOW_DAYS), datetime.max.time())

    result = await db.execute(
        select(AgendaEvent).where(and_(AgendaEvent.start_time >= window_start, AgendaEvent.start_time <= window_end))
    )
    events = list(result.scalars().all())

    queued = 0
    seen_series: set[int] = set()

    for event in events:
        if event.series_id is None:
            await enqueue(db, ENTITY_EVENT, event_key(event.id), OP_UPSERT)
            queued += 1
        elif event.is_exception:
            await enqueue(db, ENTITY_INSTANCE, instance_key(event.series_id, event.start_time.date()), OP_UPSERT)
            queued += 1
        elif event.series_id not in seen_series:
            seen_series.add(event.series_id)
            await enqueue(db, ENTITY_SERIES, series_key(event.series_id), OP_UPSERT)
            queued += 1

    await db.commit()
    return queued


async def reconcile(db: AsyncSession, client: GoogleCalendarClient | None = None, dry_run: bool = False) -> dict:
    """Re-push drifted events and delete Google events whose source is gone.

    Only events carrying our own ``fp_id`` property on the configured calendar
    are ever considered for deletion.
    """
    config = await get_google_config(db)
    if not config.usable:
        return {"status": "disabled"}

    client = client or GoogleCalendarClient(config.calendar_id)

    queued = await enqueue_all(db)

    remote = await client.list_synced()
    links_result = await db.execute(
        select(GoogleSyncLink).where(GoogleSyncLink.google_calendar_id == config.calendar_id)
    )
    known_ids = {link.google_event_id for link in links_result.scalars().all()}

    orphans = [
        item
        for item in remote
        if item.get("id") not in known_ids and item.get("extendedProperties", {}).get("private", {}).get("fp_id")
    ]

    removed = 0
    for item in orphans:
        if not dry_run:
            await client.delete(item["id"])
        removed += 1

    logger.info(
        "Google Calendar reconciliation completed.",
        queued=queued,
        remote_events=len(remote),
        orphans_removed=removed,
        dry_run=dry_run,
    )

    return {
        "status": "ok",
        "queued": queued,
        "remote_events": len(remote),
        "orphans_removed": removed,
        "dry_run": dry_run,
    }


async def purge_calendar(db: AsyncSession, client: GoogleCalendarClient | None = None) -> int:
    """Remove every event from the configured Google calendar.

    This intentionally includes events not created by FamiliePlanner.
    """
    config = await get_google_config(db)
    if not config.calendar_id or not credentials_available():
        raise GoogleCalendarNotConfigured("Google Calendar is niet geconfigureerd.")

    client = client or GoogleCalendarClient(config.calendar_id)

    removed = 0
    for item in await client.list_all_events():
        await client.delete(item["id"])
        removed += 1

    await db.execute(sa_delete(GoogleSyncLink).where(GoogleSyncLink.google_calendar_id == config.calendar_id))
    await db.execute(sa_delete(GoogleSyncQueue))
    await _set_setting(db, "google_sync_last_purge_at", now_local().isoformat())
    await db.commit()

    logger.warning("All events removed from the configured Google Calendar.", removed=removed)
    return removed


async def _last_purge_marker(db: AsyncSession) -> datetime | None:
    value = await _get_setting(db, "google_sync_last_purge_at", "")
    if not value:
        return None
    try:
        return datetime.fromisoformat(value)
    except ValueError:
        logger.warning("Google sync purge marker is invalid and will be ignored.", value=value)
        return None


async def _is_manual_purge_cleared(db: AsyncSession) -> bool:
    marker = await _last_purge_marker(db)
    if marker is None:
        return False
    return (now_local() - marker) < timedelta(minutes=5)


async def _drop_replay_after_purge(db: AsyncSession) -> None:
    """Prevent queued sync jobs from replaying stale Google state after a manual purge."""
    if not await _is_manual_purge_cleared(db):
        return

    await db.execute(sa_delete(GoogleSyncQueue))
    await db.commit()

    logger.warning("Google sync queue was cleared after a manual purge to avoid replaying deleted events.")


async def sync_status(db: AsyncSession) -> dict[str, Any]:
    config = await get_google_config(db)

    pending = await db.execute(select(GoogleSyncQueue).order_by(GoogleSyncQueue.id))
    pending_jobs = list(pending.scalars().all())

    links = await db.execute(select(GoogleSyncLink))
    link_rows = list(links.scalars().all())

    last_synced = max((link.last_synced_at for link in link_rows if link.last_synced_at), default=None)
    errors = [
        {"entity": f"{j.entity_type}:{j.entity_key}", "attempts": j.attempts, "error": j.last_error}
        for j in pending_jobs
        if j.last_error
    ]

    return {
        "enabled": config.enabled,
        "configured": bool(config.calendar_id),
        "credentials_available": credentials_available(),
        "usable": config.usable,
        "blocking_reason": config.blocking_reason(),
        "calendar_id": config.calendar_id,
        "timezone": config.timezone,
        "synced_events": len(link_rows),
        "pending_jobs": len(pending_jobs),
        "last_synced_at": last_synced.isoformat() if last_synced else None,
        "errors": errors[:10],
    }
