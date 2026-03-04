"""CRUD router for Meal planner."""
from datetime import date, timedelta
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.meals import Meal, MealType
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
    stmt = (
        select(Meal)
        .where(Meal.date == today)
        .order_by(Meal.meal_type)
    )
    result = await db.execute(stmt)
    return result.scalars().all()


@router.get("/week", response_model=list[MealOut])
async def week_meals(db: AsyncSession = Depends(get_db)):
    today = date.today()
    end = today + timedelta(days=7)
    stmt = (
        select(Meal)
        .where(and_(Meal.date >= today, Meal.date <= end))
        .order_by(Meal.date, Meal.meal_type)
    )
    result = await db.execute(stmt)
    return result.scalars().all()


@router.post("/", response_model=MealOut, status_code=201)
async def create_meal(payload: MealCreate, db: AsyncSession = Depends(get_db)):
    meal = Meal(**payload.model_dump())
    db.add(meal)
    await db.commit()
    await db.refresh(meal)
    return meal


@router.get("/{meal_id}", response_model=MealOut)
async def get_meal(meal_id: int, db: AsyncSession = Depends(get_db)):
    meal = await db.get(Meal, meal_id)
    if not meal:
        raise HTTPException(404, "Meal not found")
    return meal


@router.put("/{meal_id}", response_model=MealOut)
async def update_meal(
    meal_id: int, payload: MealUpdate, db: AsyncSession = Depends(get_db)
):
    meal = await db.get(Meal, meal_id)
    if not meal:
        raise HTTPException(404, "Meal not found")
    for k, v in payload.model_dump().items():
        setattr(meal, k, v)
    await db.commit()
    await db.refresh(meal)
    return meal


@router.delete("/{meal_id}", status_code=204)
async def delete_meal(meal_id: int, db: AsyncSession = Depends(get_db)):
    meal = await db.get(Meal, meal_id)
    if not meal:
        raise HTTPException(404, "Meal not found")
    await db.delete(meal)
    await db.commit()
