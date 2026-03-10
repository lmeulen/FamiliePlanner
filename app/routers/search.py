"""Global search endpoint across agenda, tasks, and meals."""

from fastapi import APIRouter, Depends, Query
from loguru import logger
from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.database import get_db
from app.models.agenda import AgendaEvent, agenda_event_members
from app.models.family import FamilyMember
from app.models.meals import Meal
from app.models.tasks import Task, TaskList, task_members

router = APIRouter(prefix="/api/search", tags=["search"])


@router.get("/")
async def search(
    q: str = Query(..., min_length=3, max_length=100, description="Search query (min 3 chars)"),
    db: AsyncSession = Depends(get_db),
):
    """
    Global search across agenda events, tasks, and meals.

    Returns max 7 results per category, sorted by relevance/date.
    Searches in: titles, descriptions, locations, member names, list names.
    """
    query = f"%{q}%"
    results: dict[str, list[dict]] = {"events": [], "tasks": [], "meals": []}

    # ── Search Agenda Events ──────────────────────────────────────
    # Search in: title, description, location, member names
    event_stmt = (
        select(AgendaEvent)
        .distinct()
        .options(selectinload(AgendaEvent.members))
        .outerjoin(agenda_event_members, AgendaEvent.id == agenda_event_members.c.event_id)
        .outerjoin(FamilyMember, agenda_event_members.c.member_id == FamilyMember.id)
        .where(
            or_(
                AgendaEvent.title.ilike(query),
                AgendaEvent.description.ilike(query),
                AgendaEvent.location.ilike(query),
                FamilyMember.name.ilike(query),
            )
        )
        .order_by(AgendaEvent.start_time.desc())
        .limit(7)
    )
    event_result = await db.execute(event_stmt)
    events = event_result.scalars().all()

    for event in events:
        results["events"].append(
            {
                "id": event.id,
                "title": event.title,
                "description": event.description,
                "location": event.location,
                "start_time": event.start_time.isoformat(),
                "end_time": event.end_time.isoformat(),
                "all_day": event.all_day,
                "member_ids": event.member_ids,
                "type": "event",
            }
        )

    # ── Search Tasks ───────────────────────────────────────────────
    # Search in: title, description, list name, member names
    task_stmt = (
        select(Task)
        .distinct()
        .options(selectinload(Task.members))
        .outerjoin(TaskList, Task.list_id == TaskList.id)
        .outerjoin(task_members, Task.id == task_members.c.task_id)
        .outerjoin(FamilyMember, task_members.c.member_id == FamilyMember.id)
        .where(
            or_(
                Task.title.ilike(query),
                Task.description.ilike(query),
                TaskList.name.ilike(query),
                FamilyMember.name.ilike(query),
            )
        )
        .order_by(Task.due_date.desc().nullslast(), Task.created_at.desc())
        .limit(7)
    )
    task_result = await db.execute(task_stmt)
    tasks = task_result.scalars().all()

    for task in tasks:
        results["tasks"].append(
            {
                "id": task.id,
                "title": task.title,
                "description": task.description,
                "done": task.done,
                "due_date": task.due_date.isoformat() if task.due_date else None,
                "list_id": task.list_id,
                "member_ids": task.member_ids,
                "type": "task",
            }
        )

    # ── Search Meals ───────────────────────────────────────────────
    # Search in: name, description, cook member name
    meal_stmt = (
        select(Meal)
        .distinct()
        .outerjoin(FamilyMember, Meal.cook_member_id == FamilyMember.id)
        .where(
            or_(
                Meal.name.ilike(query),
                Meal.description.ilike(query),
                FamilyMember.name.ilike(query),
            )
        )
        .order_by(Meal.date.desc())
        .limit(7)
    )
    meal_result = await db.execute(meal_stmt)
    meals = meal_result.scalars().all()

    for meal in meals:
        results["meals"].append(
            {
                "id": meal.id,
                "name": meal.name,
                "description": meal.description,
                "date": meal.date.isoformat(),
                "meal_type": meal.meal_type,
                "cook_member_id": meal.cook_member_id,
                "type": "meal",
            }
        )

    total = len(results["events"]) + len(results["tasks"]) + len(results["meals"])
    logger.info("search query='{}' results={}", q, total)

    return results
