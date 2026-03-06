"""CRUD + query router for AgendaEvent and RecurrenceSeries."""

from datetime import date, datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import Response
from icalendar import Calendar
from icalendar import Event as ICalEvent
from loguru import logger
from sqlalchemy import and_, select
from sqlalchemy import delete as sa_delete
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.database import get_db
from app.enums import RecurrenceType
from app.models.agenda import AgendaEvent, RecurrenceSeries, agenda_event_members, recurrence_series_members
from app.schemas.agenda import (
    AgendaEventCreate,
    AgendaEventOut,
    AgendaEventUpdate,
    RecurrenceSeriesCreate,
    RecurrenceSeriesOut,
    RecurrenceSeriesUpdate,
)
from app.utils.db import set_junction_members
from app.utils.recurrence import generate_occurrence_dates

router = APIRouter(prefix="/api/agenda", tags=["agenda"])


def _make_events_for_series(series: RecurrenceSeries) -> list[AgendaEvent]:
    return [
        AgendaEvent(
            title=series.title,
            description=series.description,
            location=series.location,
            start_time=datetime.combine(d, series.start_time_of_day),
            end_time=datetime.combine(d, series.end_time_of_day),
            all_day=series.all_day,
            color=series.color,
            series_id=series.id,
            is_exception=False,
        )
        for d in generate_occurrence_dates(series.recurrence_type, series.series_start, series.series_end)
    ]


# ── Recurrence series endpoints ───────────────────────────────────


@router.post("/series", response_model=RecurrenceSeriesOut, status_code=201)
async def create_series(payload: RecurrenceSeriesCreate, db: AsyncSession = Depends(get_db)):
    data = payload.model_dump(exclude={"member_ids"})
    series = RecurrenceSeries(**data)
    db.add(series)
    await db.flush()
    await set_junction_members(db, recurrence_series_members, "series_id", series.id, payload.member_ids)
    occurrences = _make_events_for_series(series)
    db.add_all(occurrences)
    await db.flush()
    # Set same members on all generated occurrences
    if payload.member_ids:
        for ev in occurrences:
            await set_junction_members(db, agenda_event_members, "event_id", ev.id, payload.member_ids)
    await db.commit()
    result = await db.execute(select(RecurrenceSeries).where(RecurrenceSeries.id == series.id))
    series = result.scalar_one()
    logger.info("agenda.series.created id={} title='{}' occurrences={}", series.id, series.title, len(occurrences))
    return series


@router.get("/series/{series_id}", response_model=RecurrenceSeriesOut)
async def get_series(series_id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(RecurrenceSeries).where(RecurrenceSeries.id == series_id))
    series = result.scalar_one_or_none()
    if not series:
        logger.warning("agenda.series.not_found id={}", series_id)
        raise HTTPException(404, "Reeks niet gevonden")
    return series


@router.put("/series/{series_id}", response_model=RecurrenceSeriesOut)
async def update_series(series_id: int, payload: RecurrenceSeriesUpdate, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(RecurrenceSeries).where(RecurrenceSeries.id == series_id))
    series = result.scalar_one_or_none()
    if not series:
        logger.warning("agenda.series.not_found id={}", series_id)
        raise HTTPException(404, "Reeks niet gevonden")

    for k, v in payload.model_dump(exclude={"member_ids"}, exclude_unset=True).items():
        setattr(series, k, v)
    await set_junction_members(db, recurrence_series_members, "series_id", series.id, payload.member_ids)

    # Regenerate all non-exception occurrences
    await db.execute(
        sa_delete(AgendaEvent).where(
            and_(AgendaEvent.series_id == series_id, AgendaEvent.is_exception == False)  # noqa: E712
        )
    )
    new_events = _make_events_for_series(series)
    db.add_all(new_events)
    await db.flush()
    if payload.member_ids:
        for ev in new_events:
            await set_junction_members(db, agenda_event_members, "event_id", ev.id, payload.member_ids)
    await db.commit()
    db.expire(series)
    result = await db.execute(select(RecurrenceSeries).where(RecurrenceSeries.id == series_id))
    series = result.scalar_one()
    logger.info("agenda.series.updated id={} title='{}' regenerated={}", series.id, series.title, len(new_events))
    return series


@router.delete("/series/{series_id}", status_code=204)
async def delete_series(series_id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(RecurrenceSeries).where(RecurrenceSeries.id == series_id))
    series = result.scalar_one_or_none()
    if not series:
        logger.warning("agenda.series.not_found id={}", series_id)
        raise HTTPException(404, "Reeks niet gevonden")
    title = series.title
    await db.execute(sa_delete(AgendaEvent).where(AgendaEvent.series_id == series_id))
    await db.delete(series)
    await db.commit()
    logger.info("agenda.series.deleted id={} title='{}'", series_id, title)


# ── Agenda event endpoints ────────────────────────────────────────


@router.get("/", response_model=list[AgendaEventOut])
async def list_events(
    start: date | None = Query(None, description="Start date filter (YYYY-MM-DD)"),
    end: date | None = Query(None, description="End date filter (YYYY-MM-DD)"),
    member_id: int | None = Query(None),
    db: AsyncSession = Depends(get_db),
):
    stmt = select(AgendaEvent).options(selectinload(AgendaEvent.members))
    conditions = []
    if start:
        conditions.append(AgendaEvent.start_time >= datetime.combine(start, datetime.min.time()))
    if end:
        conditions.append(AgendaEvent.start_time <= datetime.combine(end, datetime.max.time()))
    if member_id is not None:
        stmt = stmt.join(agenda_event_members, AgendaEvent.id == agenda_event_members.c.event_id).where(
            agenda_event_members.c.member_id == member_id
        )
    if conditions:
        stmt = stmt.where(and_(*conditions))
    stmt = stmt.order_by(AgendaEvent.start_time)
    result = await db.execute(stmt)
    return result.scalars().all()


@router.get("/today", response_model=list[AgendaEventOut])
async def today_events(db: AsyncSession = Depends(get_db)):
    today = date.today()
    start_dt = datetime.combine(today, datetime.min.time())
    end_dt = datetime.combine(today, datetime.max.time())
    stmt = (
        select(AgendaEvent)
        .options(selectinload(AgendaEvent.members))
        .where(and_(AgendaEvent.start_time >= start_dt, AgendaEvent.start_time <= end_dt))
        .order_by(AgendaEvent.start_time)
    )
    result = await db.execute(stmt)
    return result.scalars().all()


@router.get("/week", response_model=list[AgendaEventOut])
async def week_events(db: AsyncSession = Depends(get_db)):
    today = date.today()
    start_dt = datetime.combine(today, datetime.min.time())
    end_dt = datetime.combine(today + timedelta(days=7), datetime.max.time())
    stmt = (
        select(AgendaEvent)
        .options(selectinload(AgendaEvent.members))
        .where(and_(AgendaEvent.start_time >= start_dt, AgendaEvent.start_time <= end_dt))
        .order_by(AgendaEvent.start_time)
    )
    result = await db.execute(stmt)
    return result.scalars().all()


@router.post("/", response_model=AgendaEventOut, status_code=201)
async def create_event(payload: AgendaEventCreate, db: AsyncSession = Depends(get_db)):
    event = AgendaEvent(**payload.model_dump(exclude={"member_ids"}))
    db.add(event)
    await db.flush()
    await set_junction_members(db, agenda_event_members, "event_id", event.id, payload.member_ids)
    await db.commit()
    result = await db.execute(
        select(AgendaEvent).options(selectinload(AgendaEvent.members)).where(AgendaEvent.id == event.id)
    )
    event = result.scalar_one()
    logger.info("agenda.event.created id={} title='{}'", event.id, event.title)
    return event


@router.get("/{event_id}", response_model=AgendaEventOut)
async def get_event(event_id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(AgendaEvent).options(selectinload(AgendaEvent.members)).where(AgendaEvent.id == event_id)
    )
    event = result.scalar_one_or_none()
    if not event:
        logger.warning("agenda.event.not_found id={}", event_id)
        raise HTTPException(404, "Event not found")
    return event


@router.get("/{event_id}/export", response_class=Response)
async def export_event_ics(event_id: int, db: AsyncSession = Depends(get_db)):
    """Export a single event as .ics file compatible with Google Calendar, Outlook, and Apple Calendar."""
    result = await db.execute(
        select(AgendaEvent).options(selectinload(AgendaEvent.members)).where(AgendaEvent.id == event_id)
    )
    event = result.scalar_one_or_none()
    if not event:
        logger.warning("agenda.event.not_found id={}", event_id)
        raise HTTPException(404, "Event not found")

    # Fetch series data if this is a recurring event
    series = None
    if event.series_id:
        series_result = await db.execute(select(RecurrenceSeries).where(RecurrenceSeries.id == event.series_id))
        series = series_result.scalar_one_or_none()

    # Create iCalendar
    cal = Calendar()
    cal.add("prodid", "-//FamiliePlanner//Agenda//NL")
    cal.add("version", "2.0")
    cal.add("calscale", "GREGORIAN")
    cal.add("method", "PUBLISH")

    # Create event
    ical_event = ICalEvent()
    ical_event.add("uid", f"familieplanner-event-{event.id}@familieplanner")
    ical_event.add("summary", event.title)

    if event.description:
        ical_event.add("description", event.description)

    if event.location:
        ical_event.add("location", event.location)

    # Add timestamps
    ical_event.add("dtstamp", datetime.now())
    ical_event.add("created", event.created_at)

    # Handle all-day events
    if event.all_day:
        # For all-day events, use DATE type (not DATETIME)
        event_date = event.start_time.date()
        ical_event.add("dtstart", event_date)
        # End date is exclusive in iCalendar for all-day events
        end_date = event.end_time.date() + timedelta(days=1)
        ical_event.add("dtend", end_date)
    else:
        ical_event.add("dtstart", event.start_time)
        ical_event.add("dtend", event.end_time)

    # Add recurrence rule if this is part of a series
    if series and not event.is_exception:
        rrule = _build_rrule(series)
        if rrule:
            ical_event.add("rrule", rrule)

    cal.add_component(ical_event)

    # Generate filename
    safe_title = "".join(c for c in event.title if c.isalnum() or c in (" ", "-", "_")).strip()
    safe_title = safe_title[:50]  # Limit length
    filename = f"{safe_title or 'event'}.ics"

    logger.info("agenda.event.exported id={} title='{}'", event.id, event.title)

    return Response(
        content=cal.to_ical(),
        media_type="text/calendar",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


def _build_rrule(series: RecurrenceSeries) -> dict:
    """Convert RecurrenceSeries to iCalendar RRULE dict."""
    rrule: dict = {"UNTIL": datetime.combine(series.series_end, datetime.max.time())}

    recurrence_map: dict[RecurrenceType, dict] = {
        RecurrenceType.daily: {"FREQ": "DAILY"},
        RecurrenceType.every_other_day: {"FREQ": "DAILY", "INTERVAL": 2},
        RecurrenceType.weekly: {"FREQ": "WEEKLY"},
        RecurrenceType.biweekly: {"FREQ": "WEEKLY", "INTERVAL": 2},
        RecurrenceType.weekdays: {"FREQ": "WEEKLY", "BYDAY": ["MO", "TU", "WE", "TH", "FR"]},
        RecurrenceType.monthly: {"FREQ": "MONTHLY"},
    }

    if series.recurrence_type in recurrence_map:
        rrule.update(recurrence_map[series.recurrence_type])

    return rrule


@router.put("/{event_id}", response_model=AgendaEventOut)
async def update_event(event_id: int, payload: AgendaEventUpdate, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(AgendaEvent).options(selectinload(AgendaEvent.members)).where(AgendaEvent.id == event_id)
    )
    event = result.scalar_one_or_none()
    if not event:
        logger.warning("agenda.event.not_found id={}", event_id)
        raise HTTPException(404, "Event not found")
    logger.debug("agenda.event.update id={} member_ids={}", event_id, payload.member_ids)
    for key, value in payload.model_dump(exclude={"member_ids"}, exclude_unset=True).items():
        setattr(event, key, value)
    await set_junction_members(db, agenda_event_members, "event_id", event.id, payload.member_ids)
    if event.series_id:
        event.is_exception = True  # mark as individually edited
    await db.commit()
    db.expire(event)
    result = await db.execute(
        select(AgendaEvent).options(selectinload(AgendaEvent.members)).where(AgendaEvent.id == event_id)
    )
    event = result.scalar_one()
    logger.info("agenda.event.updated id={} title='{}' member_ids={}", event.id, event.title, event.member_ids)
    return event


@router.delete("/{event_id}", status_code=204)
async def delete_event(event_id: int, db: AsyncSession = Depends(get_db)):
    event = await db.get(AgendaEvent, event_id)
    if not event:
        logger.warning("agenda.event.not_found id={}", event_id)
        raise HTTPException(404, "Event not found")
    await db.delete(event)
    await db.commit()
    logger.info("agenda.event.deleted id={}", event_id)
