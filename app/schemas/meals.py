"""Pydantic schemas for Meal."""
from datetime import date, datetime
from pydantic import BaseModel
from app.models.meals import MealType


class MealBase(BaseModel):
    date: date
    meal_type: MealType = MealType.dinner
    name: str
    description: str = ""
    recipe_url: str = ""
    cook_member_id: int | None = None


class MealCreate(MealBase):
    pass


class MealUpdate(MealBase):
    pass


class MealOut(MealBase):
    id: int
    created_at: datetime

    model_config = {"from_attributes": True}
