"""Statistics and insights API router."""

from datetime import date, datetime, timedelta

from fastapi import APIRouter, Depends, Query, Response
from loguru import logger
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.agenda import AgendaEvent, RecurrenceSeries
from app.models.family import FamilyMember
from app.models.meals import Meal
from app.models.photos import Photo
from app.models.tasks import Task, TaskList, TaskRecurrenceSeries

router = APIRouter(prefix="/api/stats", tags=["stats"])


@router.get("/")
async def get_statistics(
    response: Response,
    period: str = Query("all", pattern="^(week|month|year|all)$"),
    db: AsyncSession = Depends(get_db),
):
    """
    Get comprehensive statistics across all modules.

    Periods:
    - week: last 7 days
    - month: last 30 days
    - year: last 365 days
    - all: all time
    """
    logger.info("stats.fetch period={}", period)

    # Cache for 5 minutes - statistics are expensive queries
    response.headers["Cache-Control"] = "private, max-age=300"

    # Calculate date range
    today = date.today()
    if period == "week":
        start_date = today - timedelta(days=7)
    elif period == "month":
        start_date = today - timedelta(days=30)
    elif period == "year":
        start_date = today - timedelta(days=365)
    else:  # all
        start_date = date(2000, 1, 1)

    # ── Database counts ───────────────────────────────────────────────
    family_count_result = await db.execute(select(func.count()).select_from(FamilyMember))
    family_count = family_count_result.scalar() or 0

    task_list_count_result = await db.execute(select(func.count()).select_from(TaskList))
    task_list_count = task_list_count_result.scalar() or 0

    task_count_result = await db.execute(select(func.count()).select_from(Task))
    task_count = task_count_result.scalar() or 0

    event_count_result = await db.execute(select(func.count()).select_from(AgendaEvent))
    event_count = event_count_result.scalar() or 0

    meal_count_result = await db.execute(select(func.count()).select_from(Meal))
    meal_count = meal_count_result.scalar() or 0

    photo_count_result = await db.execute(select(func.count()).select_from(Photo))
    photo_count = photo_count_result.scalar() or 0

    task_series_count_result = await db.execute(select(func.count()).select_from(TaskRecurrenceSeries))
    task_series_count = task_series_count_result.scalar() or 0

    event_series_count_result = await db.execute(select(func.count()).select_from(RecurrenceSeries))
    event_series_count = event_series_count_result.scalar() or 0

    # ── Task completion stats per member ──────────────────────────────
    # Get all completed tasks in period with member associations
    task_completion_query = (
        select(
            FamilyMember.id,
            FamilyMember.name,
            FamilyMember.avatar,
            func.count(Task.id).label("completed_tasks"),
        )
        .join(Task.members)
        .where(Task.done == True)  # noqa: E712
        .where(Task.created_at >= datetime.combine(start_date, datetime.min.time()))
        .group_by(FamilyMember.id, FamilyMember.name, FamilyMember.avatar)
        .order_by(func.count(Task.id).desc())
    )
    task_completion_result = await db.execute(task_completion_query)
    task_completions = [
        {"member_id": row.id, "name": row.name, "avatar": row.avatar, "count": row.completed_tasks}
        for row in task_completion_result.all()
    ]

    # ── Cooking frequency per member ──────────────────────────────────
    cooking_query = (
        select(
            FamilyMember.id,
            FamilyMember.name,
            FamilyMember.avatar,
            func.count(Meal.id).label("meal_count"),
        )
        .join(Meal, Meal.cook_member_id == FamilyMember.id)
        .where(Meal.date >= start_date)
        .group_by(FamilyMember.id, FamilyMember.name, FamilyMember.avatar)
        .order_by(func.count(Meal.id).desc())
    )
    cooking_result = await db.execute(cooking_query)
    cooking_stats = [
        {"member_id": row.id, "name": row.name, "avatar": row.avatar, "count": row.meal_count}
        for row in cooking_result.all()
    ]

    # ── Most common meals ─────────────────────────────────────────────
    meal_frequency_query = (
        select(Meal.name, func.count(Meal.id).label("count"))
        .where(Meal.date >= start_date)
        .group_by(Meal.name)
        .order_by(func.count(Meal.id).desc())
        .limit(10)
    )
    meal_frequency_result = await db.execute(meal_frequency_query)
    top_meals = [{"name": row.name, "count": row.count} for row in meal_frequency_result.all()]

    # ── Agenda activity (events per week) ─────────────────────────────
    # Calculate number of events in period
    event_count_period_result = await db.execute(
        select(func.count())
        .select_from(AgendaEvent)
        .where(AgendaEvent.start_time >= datetime.combine(start_date, datetime.min.time()))
    )
    events_in_period = event_count_period_result.scalar() or 0

    # Calculate weeks in period
    days_in_period = (today - start_date).days
    weeks_in_period = max(days_in_period / 7, 1)
    events_per_week = round(events_in_period / weeks_in_period, 1)

    # ── Task completion rate ──────────────────────────────────────────
    total_tasks_result = await db.execute(
        select(func.count())
        .select_from(Task)
        .where(Task.created_at >= datetime.combine(start_date, datetime.min.time()))
    )
    total_tasks_in_period = total_tasks_result.scalar() or 0

    completed_tasks_result = await db.execute(
        select(func.count())
        .select_from(Task)
        .where(Task.created_at >= datetime.combine(start_date, datetime.min.time()))
        .where(Task.done == True)  # noqa: E712
    )
    completed_tasks_in_period = completed_tasks_result.scalar() or 0

    completion_rate = round(
        (completed_tasks_in_period / total_tasks_in_period * 100) if total_tasks_in_period > 0 else 0, 1
    )

    logger.info(
        "stats.completed period={} task_completions={} cooking={} meals={} events_per_week={}",
        period,
        len(task_completions),
        len(cooking_stats),
        len(top_meals),
        events_per_week,
    )

    return {
        "period": period,
        "database_counts": {
            "family_members": family_count,
            "task_lists": task_list_count,
            "tasks": task_count,
            "task_series": task_series_count,
            "agenda_events": event_count,
            "event_series": event_series_count,
            "meals": meal_count,
            "photos": photo_count,
        },
        "task_completions": task_completions,
        "cooking_frequency": cooking_stats,
        "top_meals": top_meals,
        "agenda_activity": {"events_per_week": events_per_week, "total_events": events_in_period},
        "task_stats": {
            "total": total_tasks_in_period,
            "completed": completed_tasks_in_period,
            "completion_rate": completion_rate,
        },
    }
