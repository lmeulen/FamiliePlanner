"""CRUD router for Birthdays with agenda integration."""

from datetime import date, datetime, time
from fastapi import APIRouter, Depends, Query, Response
from loguru import logger
from sqlalchemy import delete as sql_delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.enums import RecurrenceType
from app.models.agenda import AgendaEvent, RecurrenceSeries
from app.models.birthdays import Birthday
from app.schemas.birthdays import BirthdayCreate, BirthdayOut, BirthdayUpdate
from app.utils.crud import delete_model, get_or_404, update_model
from app.utils.recurrence import generate_occurrence_dates

router = APIRouter(prefix="/api/birthdays", tags=["birthdays"])


async def _create_or_update_agenda_series(db: AsyncSession, birthday: Birthday) -> None:
    """Create or update yearly recurring agenda series for birthday."""
    if not birthday.show_in_agenda:
        # Remove series if exists
        if birthday.series_id:
            await db.execute(
                sql_delete(RecurrenceSeries).where(RecurrenceSeries.id == birthday.series_id)
            )
            birthday.series_id = None
        return

    # Determine emoji and title
    emoji = "🕯️" if birthday.year_type == "death_year" else "🎂"
    title = f"{emoji} {birthday.name}"

    # Calculate series start/end (50 years of occurrences)
    current_year = date.today().year
    series_start = date(current_year, birthday.month, birthday.day)
    series_end = date(current_year + 50, birthday.month, birthday.day)

    if birthday.series_id:
        # Update existing series
        series = await get_or_404(db, RecurrenceSeries, birthday.series_id, "Series not found")
        series.title = title
        series.series_start = series_start
        series.series_end = series_end

        # Regenerate occurrences (delete non-exception events)
        await db.execute(
            sql_delete(AgendaEvent).where(
                AgendaEvent.series_id == birthday.series_id, AgendaEvent.is_exception == False
            )
        )
    else:
        # Create new series
        series = RecurrenceSeries(
            title=title,
            description=f"Verjaardag: {birthday.name}",
            location="",
            recurrence_type=RecurrenceType.yearly,
            series_start=series_start,
            series_end=series_end,
            all_day=True,
            interval=1,
            start_time_of_day=time(0, 0),
            end_time_of_day=time(23, 59),
        )
        db.add(series)
        await db.flush()
        birthday.series_id = series.id

    # Generate yearly occurrences
    occurrence_dates = generate_occurrence_dates(
        recurrence_type=RecurrenceType.yearly,
        series_start=series_start,
        series_end=series_end,
        interval=1,
    )

    # Create agenda events with age in title if birth_year
    events = []
    for d in occurrence_dates:
        event_title = title
        if birthday.year_type == "birth_year" and birthday.year:
            age_at_event = d.year - birthday.year
            event_title = f"{emoji} {birthday.name} ({age_at_event})"

        events.append(
            AgendaEvent(
                title=event_title,
                description=f"Verjaardag: {birthday.name}",
                location="",
                start_time=datetime.combine(d, time(0, 0)),
                end_time=datetime.combine(d, time(23, 59)),
                all_day=True,
                series_id=series.id,
                is_exception=False,
            )
        )
    db.add_all(events)


@router.get("/", response_model=list[BirthdayOut])
async def list_birthdays(
    show_in_agenda: bool | None = Query(None),
    response: Response = None,
    db: AsyncSession = Depends(get_db),
):
    """List all birthdays, optionally filtered by show_in_agenda."""
    if response:
        response.headers["Cache-Control"] = "no-cache"
    stmt = select(Birthday).order_by(Birthday.month, Birthday.day)
    if show_in_agenda is not None:
        stmt = stmt.where(Birthday.show_in_agenda == show_in_agenda)
    result = await db.execute(stmt)
    return result.scalars().all()


@router.post("/", response_model=BirthdayOut, status_code=201)
async def create_birthday(payload: BirthdayCreate, db: AsyncSession = Depends(get_db)):
    """Create a new birthday."""
    birthday = Birthday(**payload.model_dump(exclude={"series_id"}))
    db.add(birthday)
    await db.flush()

    # Create agenda series if enabled
    await _create_or_update_agenda_series(db, birthday)

    await db.commit()
    await db.refresh(birthday)
    logger.info(
        "birthdays.created id={} name='{}' year_type={}", birthday.id, birthday.name, birthday.year_type
    )
    return birthday


@router.get("/{birthday_id}", response_model=BirthdayOut)
async def get_birthday(birthday_id: int, db: AsyncSession = Depends(get_db)):
    """Get a single birthday by ID."""
    return await get_or_404(db, Birthday, birthday_id, "Birthday not found")


@router.put("/{birthday_id}", response_model=BirthdayOut)
async def update_birthday(
    birthday_id: int, payload: BirthdayUpdate, db: AsyncSession = Depends(get_db)
):
    """Update a birthday."""
    birthday = await get_or_404(db, Birthday, birthday_id, "Birthday not found")
    await update_model(db, birthday, payload.model_dump(exclude_unset=True, exclude={"series_id"}))

    # Update or create/delete agenda series
    await _create_or_update_agenda_series(db, birthday)

    await db.commit()
    await db.refresh(birthday)
    logger.info(
        "birthdays.updated id={} name='{}' year_type={}", birthday.id, birthday.name, birthday.year_type
    )
    return birthday


@router.delete("/{birthday_id}", status_code=204)
async def delete_birthday(birthday_id: int, db: AsyncSession = Depends(get_db)):
    """Delete a birthday (cascade deletes agenda series)."""
    await delete_model(db, Birthday, birthday_id, "Birthday not found")
    logger.info("birthdays.deleted id={}", birthday_id)


@router.get("/upcoming/{days}", response_model=list[BirthdayOut])
async def upcoming_birthdays(days: int = 30, db: AsyncSession = Depends(get_db)):
    """Get birthdays occurring in the next N days."""
    result = await db.execute(select(Birthday).order_by(Birthday.month, Birthday.day))
    all_birthdays = result.scalars().all()

    # Filter to those within next N days
    upcoming = [b for b in all_birthdays if b.days_until_next <= days]
    # Sort by days until next
    upcoming.sort(key=lambda b: b.days_until_next)
    return upcoming
