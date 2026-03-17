"""Grocery list Pydantic schemas."""

from datetime import datetime

from pydantic import BaseModel, ConfigDict


class GroceryCategoryOut(BaseModel):
    """Grocery category response."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    icon: str
    sort_order: int
    color: str


class GroceryCategoryCreate(BaseModel):
    """Create grocery category."""

    name: str
    icon: str
    color: str = "#9EA7C4"


class GroceryCategoryReorder(BaseModel):
    """Schema for reordering categories."""

    id: int
    sort_order: int


class GroceryItemCreate(BaseModel):
    """Create grocery item with smart parsing."""

    raw_input: str  # e.g., "2 kg tomaten"
    category_id: int | None = None  # Optional, will use learning if not provided


class GroceryItemOut(BaseModel):
    """Grocery item response."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    product_name: str
    display_name: str
    quantity: str | None
    unit: str | None
    category_id: int
    checked: bool
    sort_order: int
    created_at: datetime
    checked_at: datetime | None


class GroceryItemUpdate(BaseModel):
    """Update grocery item (check/uncheck or change category)."""

    category_id: int | None = None
    checked: bool | None = None


class GroceryLearningSuggestion(BaseModel):
    """Category suggestion based on learning history."""

    product_name: str
    suggested_category_id: int
    confidence: int  # usage_count
