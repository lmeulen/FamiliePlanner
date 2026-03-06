"""Meal planner model."""

from datetime import date, datetime

from sqlalchemy import Date, DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy import Enum as SAEnum
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base
from app.enums import MealType


class Meal(Base):
    __tablename__ = "meals"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    date: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    meal_type: Mapped[MealType] = mapped_column(SAEnum(MealType), default=MealType.dinner)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str] = mapped_column(Text, default="")
    recipe_url: Mapped[str] = mapped_column(String(500), default="")
    cook_member_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("family_members.id", ondelete="SET NULL"), nullable=True, default=None, index=True
    )
    created_at: Mapped[datetime] = mapped_column(DateTime, default=func.now(), server_default=func.now())
