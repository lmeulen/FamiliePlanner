"""Grocery list models."""

from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class GroceryCategory(Base):
    """Grocery category for organizing shopping list items."""

    __tablename__ = "grocery_categories"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    icon: Mapped[str] = mapped_column(String(10), nullable=False)
    sort_order: Mapped[int] = mapped_column(Integer, nullable=False)
    color: Mapped[str] = mapped_column(String(7), default="#9EA7C4", server_default="#9EA7C4")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=func.now(), server_default=func.now())


class GroceryItem(Base):
    """Individual grocery item in the shopping list."""

    __tablename__ = "grocery_items"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    product_name: Mapped[str] = mapped_column(String(200), nullable=False, index=True)
    display_name: Mapped[str] = mapped_column(String(200), nullable=False)
    quantity: Mapped[str | None] = mapped_column(String(50), nullable=True)
    unit: Mapped[str | None] = mapped_column(String(20), nullable=True)
    category_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("grocery_categories.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    checked: Mapped[bool] = mapped_column(Boolean, default=False, server_default="0", index=True)
    sort_order: Mapped[int] = mapped_column(Integer, default=0, server_default="0")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=func.now(), server_default=func.now())
    checked_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)


class GroceryProductLearning(Base):
    """Learning table to remember product-category associations."""

    __tablename__ = "grocery_product_learning"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    product_name: Mapped[str] = mapped_column(String(200), nullable=False, unique=True, index=True)
    category_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("grocery_categories.id", ondelete="CASCADE"), nullable=False
    )
    usage_count: Mapped[int] = mapped_column(Integer, default=1, server_default="1")
    last_used: Mapped[datetime] = mapped_column(DateTime, default=func.now(), server_default=func.now())
