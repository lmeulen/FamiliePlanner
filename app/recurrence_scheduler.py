"""Background job to regenerate infinite recurrence series occurrences."""

import asyncio
from datetime import date, datetime, timedelta
from typing import cast

from loguru import logger
from sqlalchemy import delete, select

from app.database import AsyncSessionLocal
from app.models.agenda import AgendaEvent, RecurrenceSeries
from app.models.tasks import Task, TaskRecurrenceSeries
from app.routers.agenda import _make_events_for_series
from app.routers.tasks import _make_tasks_for_series


async def _regenerate_infinite_series() -> None:
    """
    Regenerate occurrences for infinite series that need more future dates.

    Logic:
    - Select series where ``series_end`` and ``count`` are both ``NULL``.
    - Inspect latest non-exception occurrence for each series.
    - If no future items exist or fewer than 30 days remain, delete only future
        non-exception items from today onward and regenerate via rolling window.

    Notes:
    - Rolling window generation lives in ``generate_occurrence_dates()`` and uses
        an upper bound of ``today + 365 days``.
    - ``is_exception=True`` occurrences are preserved during regeneration.
    - This job is scheduled daily by ``run_recurrence_scheduler()``.
    """
    async with AsyncSessionLocal() as db:
        today = date.today()
        regenerate_threshold = today + timedelta(days=30)  # Regenerate if < 30 days left

        # Find infinite agenda series
        result = await db.execute(
            select(RecurrenceSeries).where(RecurrenceSeries.series_end.is_(None), RecurrenceSeries.count.is_(None))
        )
        infinite_agenda_series: list[RecurrenceSeries] = list(result.scalars().all())

        for series in infinite_agenda_series:
            # Check latest non-exception event
            max_future = await db.execute(
                select(AgendaEvent.start_time)
                .where(AgendaEvent.series_id == series.id, ~AgendaEvent.is_exception)
                .order_by(AgendaEvent.start_time.desc())
                .limit(1)
            )
            max_date = max_future.scalar_one_or_none()

            if max_date is None or max_date.date() < regenerate_threshold:
                # Delete future non-exception events and regenerate
                await db.execute(
                    delete(AgendaEvent).where(
                        AgendaEvent.series_id == series.id,
                        AgendaEvent.start_time >= datetime.combine(today, datetime.min.time()),
                        ~AgendaEvent.is_exception,
                    )
                )
                new_events = _make_events_for_series(series)
                db.add_all(new_events)
                logger.info(
                    "Regenerated agenda occurrences for infinite recurrence series.",
                    series_id=series.id,
                    regenerated_count=len(new_events),
                )

        # Find infinite task series
        task_result = await db.execute(
            select(TaskRecurrenceSeries).where(
                TaskRecurrenceSeries.series_end.is_(None), TaskRecurrenceSeries.count.is_(None)
            )
        )
        infinite_task_series = cast(list[TaskRecurrenceSeries], list(task_result.scalars().all()))

        for task_series in infinite_task_series:
            max_future = await db.execute(
                select(Task.due_date)
                .where(Task.series_id == task_series.id, ~Task.is_exception)
                .order_by(Task.due_date.desc())
                .limit(1)
            )
            max_date = max_future.scalar_one_or_none()

            if max_date is None or max_date < regenerate_threshold:
                await db.execute(
                    delete(Task).where(
                        Task.series_id == task_series.id,
                        Task.due_date >= today,
                        ~Task.is_exception,
                    )
                )
                new_tasks = _make_tasks_for_series(task_series)
                db.add_all(new_tasks)
                logger.info(
                    "Regenerated task occurrences for infinite recurrence series.",
                    task_series_id=task_series.id,
                    regenerated_count=len(new_tasks),
                )

        await db.commit()


async def run_recurrence_scheduler(stop_event: asyncio.Event) -> None:
    """Run daily at 01:00 to regenerate infinite series."""
    logger.info("Recurrence scheduler started; next run is daily at 01:00.")

    while not stop_event.is_set():
        now = datetime.now()
        # Next run: tomorrow at 01:00
        next_run = datetime.combine(now.date() + timedelta(days=1), datetime.min.time()) + timedelta(hours=1)
        wait_seconds = (next_run - now).total_seconds()

        try:
            await asyncio.wait_for(stop_event.wait(), timeout=wait_seconds)
            break  # Stop event was set
        except TimeoutError:
            try:
                await _regenerate_infinite_series()
                logger.info("Recurrence scheduler cycle completed successfully.")
            except Exception:
                logger.exception(
                    "Recurrence regeneration job failed; some infinite series may be outdated until next successful run.",
                    scheduler="recurrence",
                    next_attempt="next scheduled cycle",
                )

    logger.info("Recurrence scheduler stopped.")
