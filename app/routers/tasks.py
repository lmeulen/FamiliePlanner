"""CRUD router for TaskList and Task."""
from datetime import date
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.tasks import Task, TaskList
from app.schemas.tasks import (
    TaskCreate, TaskListCreate, TaskListOut, TaskListUpdate,
    TaskOut, TaskUpdate,
)

router = APIRouter(prefix="/api/tasks", tags=["tasks"])

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
    return tl


@router.put("/lists/{list_id}", response_model=TaskListOut)
async def update_task_list(
    list_id: int, payload: TaskListUpdate, db: AsyncSession = Depends(get_db)
):
    tl = await db.get(TaskList, list_id)
    if not tl:
        raise HTTPException(404, "Task list not found")
    for k, v in payload.model_dump(exclude_unset=True).items():
        setattr(tl, k, v)
    await db.commit()
    await db.refresh(tl)
    return tl


@router.delete("/lists/{list_id}", status_code=204)
async def delete_task_list(list_id: int, db: AsyncSession = Depends(get_db)):
    tl = await db.get(TaskList, list_id)
    if not tl:
        raise HTTPException(404, "Task list not found")
    await db.delete(tl)
    await db.commit()


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
    return task


@router.get("/{task_id}", response_model=TaskOut)
async def get_task(task_id: int, db: AsyncSession = Depends(get_db)):
    task = await db.get(Task, task_id)
    if not task:
        raise HTTPException(404, "Task not found")
    return task


@router.put("/{task_id}", response_model=TaskOut)
async def update_task(
    task_id: int, payload: TaskUpdate, db: AsyncSession = Depends(get_db)
):
    task = await db.get(Task, task_id)
    if not task:
        raise HTTPException(404, "Task not found")
    for k, v in payload.model_dump(exclude_unset=True).items():
        setattr(task, k, v)
    await db.commit()
    await db.refresh(task)
    return task


@router.patch("/{task_id}/toggle", response_model=TaskOut)
async def toggle_task(task_id: int, db: AsyncSession = Depends(get_db)):
    task = await db.get(Task, task_id)
    if not task:
        raise HTTPException(404, "Task not found")
    task.done = not task.done
    await db.commit()
    await db.refresh(task)
    return task


@router.delete("/{task_id}", status_code=204)
async def delete_task(task_id: int, db: AsyncSession = Depends(get_db)):
    task = await db.get(Task, task_id)
    if not task:
        raise HTTPException(404, "Task not found")
    await db.delete(task)
    await db.commit()
