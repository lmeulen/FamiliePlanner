"""CRUD router for Meal planner."""

from datetime import date, timedelta

from fastapi import APIRouter, Depends, HTTPException, Query
from loguru import logger
from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.enums import MealType
from app.metrics import meals_created_total
from app.models.meals import Meal
from app.schemas.meals import MealCreate, MealOut, MealUpdate

router = APIRouter(prefix="/api/meals", tags=["meals"])


@router.get("/", response_model=list[MealOut])
async def list_meals(
    start: date | None = Query(None),
    end: date | None = Query(None),
    meal_type: MealType | None = Query(None),
    db: AsyncSession = Depends(get_db),
):
    stmt = select(Meal)
    conditions = []
    if start:
        conditions.append(Meal.date >= start)
    if end:
        conditions.append(Meal.date <= end)
    if meal_type:
        conditions.append(Meal.meal_type == meal_type)
    if conditions:
        stmt = stmt.where(and_(*conditions))
    stmt = stmt.order_by(Meal.date, Meal.meal_type)
    result = await db.execute(stmt)
    return result.scalars().all()


@router.get("/today", response_model=list[MealOut])
async def today_meals(db: AsyncSession = Depends(get_db)):
    today = date.today()
    stmt = select(Meal).where(Meal.date == today).order_by(Meal.meal_type)
    result = await db.execute(stmt)
    return result.scalars().all()


@router.get("/week", response_model=list[MealOut])
async def week_meals(db: AsyncSession = Depends(get_db)):
    today = date.today()
    end = today + timedelta(days=7)
    stmt = select(Meal).where(and_(Meal.date >= today, Meal.date <= end)).order_by(Meal.date, Meal.meal_type)
    result = await db.execute(stmt)
    return result.scalars().all()


@router.post("/", response_model=MealOut, status_code=201)
async def create_meal(payload: MealCreate, db: AsyncSession = Depends(get_db)):
    logger.debug("meals.meal.create_request payload_date={} payload_dict={}", payload.date, payload.model_dump())
    meal = Meal(**payload.model_dump())
    db.add(meal)
    await db.commit()
    await db.refresh(meal)
    logger.info("meals.meal.created id={} name='{}' date={} saved_date={}", meal.id, meal.name, payload.date, meal.date)
    meals_created_total.inc()
    return meal


@router.get("/{meal_id}", response_model=MealOut)
async def get_meal(meal_id: int, db: AsyncSession = Depends(get_db)):
    meal = await db.get(Meal, meal_id)
    if not meal:
        logger.warning("meals.meal.not_found id={}", meal_id)
        raise HTTPException(404, "Meal not found")
    return meal


@router.put("/{meal_id}", response_model=MealOut)
async def update_meal(meal_id: int, payload: MealUpdate, db: AsyncSession = Depends(get_db)):
    meal = await db.get(Meal, meal_id)
    if not meal:
        logger.warning("meals.meal.not_found id={}", meal_id)
        raise HTTPException(404, "Meal not found")
    for k, v in payload.model_dump(exclude_unset=True).items():
        setattr(meal, k, v)
    await db.commit()
    await db.refresh(meal)
    logger.info("meals.meal.updated id={} name='{}'", meal.id, meal.name)
    return meal


@router.delete("/all", status_code=204)
async def clear_all_meals(db: AsyncSession = Depends(get_db)):
    """Delete all meals (for database cleanup)."""
    from fastapi.responses import Response as FastAPIResponse
    from sqlalchemy import delete as sa_delete

    await db.execute(sa_delete(Meal))
    await db.commit()
    logger.warning("meals.all_cleared - All meals deleted")
    return FastAPIResponse(status_code=204)


@router.delete("/{meal_id}", status_code=204)
async def delete_meal(meal_id: int, db: AsyncSession = Depends(get_db)):
    meal = await db.get(Meal, meal_id)
    if not meal:
        logger.warning("meals.meal.not_found id={}", meal_id)
        raise HTTPException(404, "Meal not found")
    await db.delete(meal)
    await db.commit()
    logger.info("meals.meal.deleted id={}", meal_id)
