"""CRUD router for TaskList, TaskRecurrenceSeries and Task."""
import calendar as cal_mod
from datetime import date, timedelta
from fastapi import APIRouter, Depends, HTTPException, Query
from loguru import logger
from sqlalchemy import select, and_, delete as sa_delete
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.enums import RecurrenceType
from app.models.tasks import Task, TaskList, TaskRecurrenceSeries
from app.schemas.tasks import (
    TaskCreate, TaskListCreate, TaskListOut, TaskListUpdate,
    TaskOut, TaskUpdate,
    TaskRecurrenceSeriesCreate, TaskRecurrenceSeriesOut, TaskRecurrenceSeriesUpdate,
)

router = APIRouter(prefix="/api/tasks", tags=["tasks"])


# ── Occurrence generator ──────────────────────────────────────────

def generate_task_occurrence_dates(series: TaskRecurrenceSeries) -> list[date]:
    """Return every due_date for a task series (max 365 tasks)."""
    results: list[date] = []
    current: date = series.series_start
    end: date = series.series_end
    MAX = 365

    while current <= end and len(results) < MAX:
        if series.recurrence_type == RecurrenceType.weekdays:
            if current.weekday() < 5:
                results.append(current)
            current += timedelta(days=1)
        elif series.recurrence_type == RecurrenceType.monthly:
            results.append(current)
            mo = current.month + 1
            yr = current.year
            if mo > 12:
                mo, yr = 1, yr + 1
            day = min(series.series_start.day, cal_mod.monthrange(yr, mo)[1])
            current = date(yr, mo, day)
        else:
            results.append(current)
            delta = {
                RecurrenceType.daily:           timedelta(days=1),
                RecurrenceType.every_other_day: timedelta(days=2),
                RecurrenceType.weekly:          timedelta(weeks=1),
                RecurrenceType.biweekly:        timedelta(weeks=2),
            }[series.recurrence_type]
            current += delta

    return results


def _make_tasks_for_series(series: TaskRecurrenceSeries) -> list[Task]:
    return [
        Task(
            title=series.title,
            description=series.description,
            list_id=series.list_id,
            member_id=series.member_id,
            due_date=d,
            done=False,
            series_id=series.id,
            is_exception=False,
        )
        for d in generate_task_occurrence_dates(series)
    ]


# ---- Task Lists ----

@router.get("/lists", response_model=list[TaskListOut])
async def list_task_lists(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(TaskList).order_by(TaskList.id))
    return result.scalars().all()


@router.post("/lists", response_model=TaskListOut, status_code=201)
async def create_task_list(payload: TaskListCreate, db: AsyncSession = Depends(get_db)):
    tl = TaskList(**payload.model_dump())
    db.add(tl)
    await db.commit()
    await db.refresh(tl)
    logger.info("tasks.list.created id={} name='{}'", tl.id, tl.name)
    return tl


@router.put("/lists/{list_id}", response_model=TaskListOut)
async def update_task_list(
    list_id: int, payload: TaskListUpdate, db: AsyncSession = Depends(get_db)
):
    tl = await db.get(TaskList, list_id)
    if not tl:
        logger.warning("tasks.list.not_found id={}", list_id)
        raise HTTPException(404, "Task list not found")
    for k, v in payload.model_dump(exclude_unset=True).items():
        setattr(tl, k, v)
    await db.commit()
    await db.refresh(tl)
    logger.info("tasks.list.updated id={} name='{}'", tl.id, tl.name)
    return tl


@router.delete("/lists/{list_id}", status_code=204)
async def delete_task_list(list_id: int, db: AsyncSession = Depends(get_db)):
    tl = await db.get(TaskList, list_id)
    if not tl:
        logger.warning("tasks.list.not_found id={}", list_id)
        raise HTTPException(404, "Task list not found")
    await db.delete(tl)
    await db.commit()
    logger.info("tasks.list.deleted id={}", list_id)


# ---- Task Recurrence Series ----

@router.post("/series", response_model=TaskRecurrenceSeriesOut, status_code=201)
async def create_task_series(payload: TaskRecurrenceSeriesCreate, db: AsyncSession = Depends(get_db)):
    series = TaskRecurrenceSeries(**payload.model_dump())
    db.add(series)
    await db.flush()
    occurrences = _make_tasks_for_series(series)
    db.add_all(occurrences)
    await db.commit()
    await db.refresh(series)
    logger.info("tasks.series.created id={} title='{}' occurrences={}", series.id, series.title, len(occurrences))
    return series


@router.get("/series/{series_id}", response_model=TaskRecurrenceSeriesOut)
async def get_task_series(series_id: int, db: AsyncSession = Depends(get_db)):
    series = await db.get(TaskRecurrenceSeries, series_id)
    if not series:
        logger.warning("tasks.series.not_found id={}", series_id)
        raise HTTPException(404, "Reeks niet gevonden")
    return series


@router.put("/series/{series_id}", response_model=TaskRecurrenceSeriesOut)
async def update_task_series(
    series_id: int, payload: TaskRecurrenceSeriesUpdate, db: AsyncSession = Depends(get_db)
):
    series = await db.get(TaskRecurrenceSeries, series_id)
    if not series:
        logger.warning("tasks.series.not_found id={}", series_id)
        raise HTTPException(404, "Reeks niet gevonden")
    for k, v in payload.model_dump(exclude_unset=True).items():
        setattr(series, k, v)
    # Regenerate all non-exception occurrences
    await db.execute(
        sa_delete(Task).where(
            and_(Task.series_id == series_id, Task.is_exception == False)  # noqa: E712
        )
    )
    new_tasks = _make_tasks_for_series(series)
    db.add_all(new_tasks)
    await db.commit()
    await db.refresh(series)
    logger.info("tasks.series.updated id={} title='{}' regenerated={}", series.id, series.title, len(new_tasks))
    return series


@router.delete("/series/{series_id}", status_code=204)
async def delete_task_series(series_id: int, db: AsyncSession = Depends(get_db)):
    series = await db.get(TaskRecurrenceSeries, series_id)
    if not series:
        logger.warning("tasks.series.not_found id={}", series_id)
        raise HTTPException(404, "Reeks niet gevonden")
    await db.execute(sa_delete(Task).where(Task.series_id == series_id))
    await db.delete(series)
    await db.commit()
    logger.info("tasks.series.deleted id={} title='{}'", series_id, series.title)


# ---- Tasks ----

@router.get("/", response_model=list[TaskOut])
async def list_tasks(
    list_id: int | None = Query(None),
    member_id: int | None = Query(None),
    done: bool | None = Query(None),
    due_date: date | None = Query(None),
    db: AsyncSession = Depends(get_db),
):
    stmt = select(Task)
    conditions = []
    if list_id is not None:
        conditions.append(Task.list_id == list_id)
    if member_id is not None:
        conditions.append(Task.member_id == member_id)
    if done is not None:
        conditions.append(Task.done == done)
    if due_date is not None:
        conditions.append(Task.due_date == due_date)
    if conditions:
        stmt = stmt.where(and_(*conditions))
    stmt = stmt.order_by(Task.due_date.asc().nullslast(), Task.created_at)
    result = await db.execute(stmt)
    return result.scalars().all()


@router.get("/today", response_model=list[TaskOut])
async def today_tasks(db: AsyncSession = Depends(get_db)):
    today = date.today()
    stmt = (
        select(Task)
        .where(and_(Task.due_date == today, Task.done == False))  # noqa: E712
        .order_by(Task.created_at)
    )
    result = await db.execute(stmt)
    return result.scalars().all()


@router.get("/overdue", response_model=list[TaskOut])
async def overdue_tasks(db: AsyncSession = Depends(get_db)):
    today = date.today()
    stmt = (
        select(Task)
        .where(and_(Task.due_date < today, Task.done == False))  # noqa: E712
        .order_by(Task.due_date.asc(), Task.created_at)
    )
    result = await db.execute(stmt)
    return result.scalars().all()


@router.post("/", response_model=TaskOut, status_code=201)
async def create_task(payload: TaskCreate, db: AsyncSession = Depends(get_db)):
    task = Task(**payload.model_dump())
    db.add(task)
    await db.commit()
    await db.refresh(task)
    logger.info("tasks.task.created id={} title='{}'", task.id, task.title)
    return task


@router.get("/{task_id}", response_model=TaskOut)
async def get_task(task_id: int, db: AsyncSession = Depends(get_db)):
    task = await db.get(Task, task_id)
    if not task:
        logger.warning("tasks.task.not_found id={}", task_id)
        raise HTTPException(404, "Task not found")
    return task


@router.put("/{task_id}", response_model=TaskOut)
async def update_task(
    task_id: int, payload: TaskUpdate, db: AsyncSession = Depends(get_db)
):
    task = await db.get(Task, task_id)
    if not task:
        logger.warning("tasks.task.not_found id={}", task_id)
        raise HTTPException(404, "Task not found")
    for k, v in payload.model_dump(exclude_unset=True).items():
        setattr(task, k, v)
    if task.series_id:
        task.is_exception = True   # mark as individually edited
    await db.commit()
    await db.refresh(task)
    logger.info("tasks.task.updated id={} title='{}'", task.id, task.title)
    return task


@router.patch("/{task_id}/toggle", response_model=TaskOut)
async def toggle_task(task_id: int, db: AsyncSession = Depends(get_db)):
    task = await db.get(Task, task_id)
    if not task:
        logger.warning("tasks.task.not_found id={}", task_id)
        raise HTTPException(404, "Task not found")
    task.done = not task.done
    await db.commit()
    await db.refresh(task)
    logger.info("tasks.task.toggled id={} done={}", task.id, task.done)
    return task


@router.delete("/{task_id}", status_code=204)
async def delete_task(task_id: int, db: AsyncSession = Depends(get_db)):
    task = await db.get(Task, task_id)
    if not task:
        logger.warning("tasks.task.not_found id={}", task_id)
        raise HTTPException(404, "Task not found")
    await db.delete(task)
    await db.commit()
    logger.info("tasks.task.deleted id={}", task_id)
