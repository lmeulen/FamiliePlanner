"""Pydantic schemas for Meal."""
from datetime import date, datetime
from pydantic import BaseModel, Field, HttpUrl, field_validator
from app.enums import MealType


class MealBase(BaseModel):
    date: date
    meal_type: MealType = MealType.dinner
    name: str = Field(min_length=1, max_length=200)
    description: str = Field(default="", max_length=1000)
    recipe_url: str = Field(default="", max_length=500)
    cook_member_id: int | None = None

    @field_validator("recipe_url")
    @classmethod
    def validate_recipe_url(cls, v: str) -> str:
        if v and not (v.startswith("http://") or v.startswith("https://")):
            raise ValueError("Recept URL moet beginnen met http:// of https://")
        return v


class MealCreate(MealBase):
    pass


class MealUpdate(MealBase):
    pass


class MealOut(MealBase):
    id: int
    created_at: datetime

    model_config = {"from_attributes": True}
