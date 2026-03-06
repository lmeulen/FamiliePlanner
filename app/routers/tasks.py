"""CRUD router for TaskList, TaskRecurrenceSeries and Task."""

from datetime import date, timedelta

from fastapi import APIRouter, Depends, HTTPException, Query
from loguru import logger
from sqlalchemy import and_, select
from sqlalchemy import delete as sa_delete
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.database import get_db
from app.models.settings import AppSetting
from app.models.tasks import Task, TaskList, TaskRecurrenceSeries, task_members, task_recurrence_series_members
from app.schemas.tasks import (
    OverduePositionOut,
    TaskCreate,
    TaskListCreate,
    TaskListOut,
    TaskListReorderItem,
    TaskListUpdate,
    TaskOut,
    TaskRecurrenceSeriesCreate,
    TaskRecurrenceSeriesOut,
    TaskRecurrenceSeriesUpdate,
    TaskUpdate,
)
from app.utils.db import set_junction_members
from app.utils.recurrence import generate_occurrence_dates

router = APIRouter(prefix="/api/tasks", tags=["tasks"])


def _make_tasks_for_series(series: TaskRecurrenceSeries) -> list[Task]:
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
        Task(
            title=series.title,
            description=series.description,
            list_id=series.list_id,
            due_date=d,
            done=False,
            series_id=series.id,
            is_exception=False,
        )
        for d in occurrence_dates
    ]


# ---- Task Lists ----


@router.get("/lists", response_model=list[TaskListOut])
async def list_task_lists(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(TaskList).order_by(TaskList.sort_order, TaskList.id))
    return result.scalars().all()


@router.post("/lists", response_model=TaskListOut, status_code=201)
async def create_task_list(payload: TaskListCreate, db: AsyncSession = Depends(get_db)):
    # Assign sort_order after existing lists if not specified
    if payload.sort_order == 0:
        res = await db.execute(select(TaskList).order_by(TaskList.sort_order.desc()))
        last = res.scalars().first()
        payload = payload.model_copy(update={"sort_order": (last.sort_order + 10) if last else 10})
    tl = TaskList(**payload.model_dump())
    db.add(tl)
    await db.commit()
    await db.refresh(tl)
    logger.info("tasks.list.created id={} name='{}'", tl.id, tl.name)
    return tl


@router.put("/lists/reorder", status_code=204)
async def reorder_task_lists(items: list[TaskListReorderItem], db: AsyncSession = Depends(get_db)):
    """Bulk-update sort_order for task lists."""
    for item in items:
        tl = await db.get(TaskList, item.id)
        if tl:
            tl.sort_order = item.sort_order
    await db.commit()
    logger.info("tasks.lists.reordered count={}", len(items))


@router.get("/overdue-position", response_model=OverduePositionOut)
async def get_overdue_position(db: AsyncSession = Depends(get_db)):
    setting = await db.get(AppSetting, "overdue_sort_order")
    return {"sort_order": int(setting.value) if setting else 9999}


@router.put("/overdue-position", response_model=OverduePositionOut)
async def set_overdue_position(payload: OverduePositionOut, db: AsyncSession = Depends(get_db)):
    setting = await db.get(AppSetting, "overdue_sort_order")
    if setting:
        setting.value = str(payload.sort_order)
    else:
        db.add(AppSetting(key="overdue_sort_order", value=str(payload.sort_order)))
    await db.commit()
    logger.info("tasks.overdue_position.updated sort_order={}", payload.sort_order)
    return {"sort_order": payload.sort_order}


@router.put("/lists/{list_id}", response_model=TaskListOut)
async def update_task_list(list_id: int, payload: TaskListUpdate, db: AsyncSession = Depends(get_db)):
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
    data = payload.model_dump(exclude={"member_ids"})

    # Calculate series_end if count is provided
    if payload.count and not payload.series_end:
        # Generate occurrence dates to determine actual end date
        temp_dates = generate_occurrence_dates(
            recurrence_type=payload.recurrence_type,
            series_start=payload.series_start,
            series_end=None,
            interval=payload.interval,
            count=payload.count,
            monthly_pattern=payload.monthly_pattern,
            rrule_string=payload.rrule,
        )
        if temp_dates:
            data["series_end"] = temp_dates[-1]
        else:
            # Fallback: use series_start + 1 year
            data["series_end"] = payload.series_start + timedelta(days=365)

    series = TaskRecurrenceSeries(**data)
    db.add(series)
    await db.flush()
    await set_junction_members(db, task_recurrence_series_members, "series_id", series.id, payload.member_ids)
    occurrences = _make_tasks_for_series(series)
    db.add_all(occurrences)
    await db.flush()
    if payload.member_ids:
        for t in occurrences:
            await set_junction_members(db, task_members, "task_id", t.id, payload.member_ids)
    await db.commit()
    result = await db.execute(select(TaskRecurrenceSeries).where(TaskRecurrenceSeries.id == series.id))
    series = result.scalar_one()
    logger.info("tasks.series.created id={} title='{}' occurrences={}", series.id, series.title, len(occurrences))
    return series


@router.get("/series/{series_id}", response_model=TaskRecurrenceSeriesOut)
async def get_task_series(series_id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(TaskRecurrenceSeries).where(TaskRecurrenceSeries.id == series_id))
    series = result.scalar_one_or_none()
    if not series:
        logger.warning("tasks.series.not_found id={}", series_id)
        raise HTTPException(404, "Reeks niet gevonden")
    return series


@router.put("/series/{series_id}", response_model=TaskRecurrenceSeriesOut)
async def update_task_series(series_id: int, payload: TaskRecurrenceSeriesUpdate, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(TaskRecurrenceSeries).where(TaskRecurrenceSeries.id == series_id))
    series = result.scalar_one_or_none()
    if not series:
        logger.warning("tasks.series.not_found id={}", series_id)
        raise HTTPException(404, "Reeks niet gevonden")

    # Calculate series_end if count is provided
    update_data = payload.model_dump(exclude={"member_ids"}, exclude_unset=True)
    if payload.count and not payload.series_end:
        # Generate occurrence dates to determine actual end date
        temp_dates = generate_occurrence_dates(
            recurrence_type=payload.recurrence_type,
            series_start=series.series_start,
            series_end=None,
            interval=payload.interval,
            count=payload.count,
            monthly_pattern=payload.monthly_pattern,
            rrule_string=payload.rrule,
        )
        if temp_dates:
            update_data["series_end"] = temp_dates[-1]
        else:
            # Fallback: use series_start + 1 year
            update_data["series_end"] = series.series_start + timedelta(days=365)

    for k, v in update_data.items():
        setattr(series, k, v)
    await set_junction_members(db, task_recurrence_series_members, "series_id", series.id, payload.member_ids)
    # Regenerate all non-exception occurrences
    await db.execute(sa_delete(Task).where(and_(Task.series_id == series_id, Task.is_exception == False)))  # noqa: E712
    new_tasks = _make_tasks_for_series(series)
    db.add_all(new_tasks)
    await db.flush()
    if payload.member_ids:
        for t in new_tasks:
            await set_junction_members(db, task_members, "task_id", t.id, payload.member_ids)
    await db.commit()
    db.expire(series)
    result = await db.execute(select(TaskRecurrenceSeries).where(TaskRecurrenceSeries.id == series_id))
    series = result.scalar_one()
    logger.info("tasks.series.updated id={} title='{}' regenerated={}", series.id, series.title, len(new_tasks))
    return series


@router.delete("/series/{series_id}", status_code=204)
async def delete_task_series(series_id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(TaskRecurrenceSeries).where(TaskRecurrenceSeries.id == series_id))
    series = result.scalar_one_or_none()
    if not series:
        logger.warning("tasks.series.not_found id={}", series_id)
        raise HTTPException(404, "Reeks niet gevonden")
    title = series.title
    await db.execute(sa_delete(Task).where(Task.series_id == series_id))
    await db.delete(series)
    await db.commit()
    logger.info("tasks.series.deleted id={} title='{}'", series_id, title)


# ---- Tasks ----


@router.get("/", response_model=list[TaskOut])
async def list_tasks(
    list_id: int | None = Query(None),
    member_id: int | None = Query(None),
    done: bool | None = Query(None),
    due_date: date | None = Query(None),
    db: AsyncSession = Depends(get_db),
):
    stmt = select(Task).options(selectinload(Task.members))
    conditions = []
    if list_id is not None:
        conditions.append(Task.list_id == list_id)
    if member_id is not None:
        stmt = stmt.join(task_members, Task.id == task_members.c.task_id).where(task_members.c.member_id == member_id)
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
        .options(selectinload(Task.members))
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
        .options(selectinload(Task.members))
        .where(and_(Task.due_date < today, Task.done == False))  # noqa: E712
        .order_by(Task.due_date.asc(), Task.created_at)
    )
    result = await db.execute(stmt)
    return result.scalars().all()


@router.post("/", response_model=TaskOut, status_code=201)
async def create_task(payload: TaskCreate, db: AsyncSession = Depends(get_db)):
    task = Task(**payload.model_dump(exclude={"member_ids"}))
    db.add(task)
    await db.flush()
    await set_junction_members(db, task_members, "task_id", task.id, payload.member_ids)
    await db.commit()
    result = await db.execute(select(Task).options(selectinload(Task.members)).where(Task.id == task.id))
    task = result.scalar_one()
    logger.info("tasks.task.created id={} title='{}'", task.id, task.title)
    return task


@router.get("/{task_id}", response_model=TaskOut)
async def get_task(task_id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Task).options(selectinload(Task.members)).where(Task.id == task_id))
    task = result.scalar_one_or_none()
    if not task:
        logger.warning("tasks.task.not_found id={}", task_id)
        raise HTTPException(404, "Task not found")
    return task


@router.put("/{task_id}", response_model=TaskOut)
async def update_task(task_id: int, payload: TaskUpdate, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Task).options(selectinload(Task.members)).where(Task.id == task_id))
    task = result.scalar_one_or_none()
    if not task:
        logger.warning("tasks.task.not_found id={}", task_id)
        raise HTTPException(404, "Task not found")
    logger.debug("tasks.task.update id={} member_ids={}", task_id, payload.member_ids)
    for k, v in payload.model_dump(exclude={"member_ids"}, exclude_unset=True).items():
        setattr(task, k, v)
    await set_junction_members(db, task_members, "task_id", task.id, payload.member_ids)
    if task.series_id:
        task.is_exception = True  # mark as individually edited
    await db.commit()
    db.expire(task)
    result = await db.execute(select(Task).options(selectinload(Task.members)).where(Task.id == task_id))
    task = result.scalar_one()
    logger.info("tasks.task.updated id={} title='{}' member_ids={}", task.id, task.title, task.member_ids)
    return task


@router.patch("/{task_id}/toggle", response_model=TaskOut)
async def toggle_task(task_id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Task).options(selectinload(Task.members)).where(Task.id == task_id))
    task = result.scalar_one_or_none()
    if not task:
        logger.warning("tasks.task.not_found id={}", task_id)
        raise HTTPException(404, "Task not found")
    task.done = not task.done
    await db.commit()
    result = await db.execute(select(Task).options(selectinload(Task.members)).where(Task.id == task_id))
    task = result.scalar_one()
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
