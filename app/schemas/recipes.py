"""Pydantic schemas for Mealie recipe integration."""

from datetime import datetime

from pydantic import BaseModel, Field, field_validator


class RecipeIngredient(BaseModel):
    """Single ingredient with quantity, unit, and food item."""

    quantity: float | None = None
    unit: str | dict | None = Field(None)  # Mealie returns dict with "name" field
    food: str | dict | None = Field(None)  # Mealie returns dict with "name" field
    display: str = Field(max_length=500)  # Full display text
    note: str = Field(default="", max_length=500)

    @field_validator("unit", "food", mode="before")
    @classmethod
    def extract_name_from_dict(cls, v):
        """Extract name from dict if Mealie returns dict format."""
        if isinstance(v, dict):
            return v.get("name", "")
        return v


class RecipeInstruction(BaseModel):
    """Single instruction step."""

    title: str = Field(default="", max_length=200)
    text: str = Field(max_length=5000)  # Markdown supported


class RecipeStub(BaseModel):
    """Minimal recipe response after creation."""

    id: str
    slug: str
    name: str


class RecipeCreate(BaseModel):
    """Create new recipe (only name required)."""

    name: str = Field(min_length=1, max_length=200)


class RecipeUpdate(BaseModel):
    """Update recipe with full details."""

    name: str = Field(min_length=1, max_length=200)
    description: str = Field(default="", max_length=2000)
    recipeIngredient: list[RecipeIngredient] = Field(default_factory=list)
    recipeInstructions: list[RecipeInstruction] = Field(default_factory=list)
    prepTime: str | None = None  # ISO 8601 duration (PT30M)
    cookTime: str | None = None
    totalTime: str | None = None
    recipeYield: str | None = Field(None, max_length=100)  # "4 servings"
    recipeCategory: list[str | dict] = Field(default_factory=list)  # Mealie returns dicts
    tags: list[str | dict] = Field(default_factory=list)  # Mealie returns dicts
    tools: list[str] = Field(default_factory=list)
    rating: int | float | None = Field(None, ge=1, le=5)  # Mealie returns float
    orgURL: str = Field(default="", max_length=1000)

    @field_validator("recipeCategory", "tags", mode="before")
    @classmethod
    def extract_names_from_list(cls, v):
        """Extract names from list of dicts if Mealie returns dict format."""
        if not v:
            return []
        result = []
        for item in v:
            if isinstance(item, dict):
                result.append(item.get("name", ""))
            else:
                result.append(item)
        return result


class RecipeOut(BaseModel):
    """Full recipe response from Mealie."""

    id: str
    slug: str
    name: str
    description: str = ""
    image: str | None = None
    recipeIngredient: list[RecipeIngredient] = Field(default_factory=list)
    recipeInstructions: list[RecipeInstruction] = Field(default_factory=list)
    prepTime: str | None = None
    cookTime: str | None = None
    totalTime: str | None = None
    recipeYield: str | None = None
    recipeCategory: list[str | dict] = Field(default_factory=list)  # Mealie returns dicts
    tags: list[str | dict] = Field(default_factory=list)  # Mealie returns dicts
    tools: list[str] = Field(default_factory=list)
    rating: int | float | None = None  # Mealie returns float
    orgURL: str = ""
    dateAdded: datetime | None = None
    dateUpdated: datetime | None = None
    lastMade: datetime | None = None

    @field_validator("recipeCategory", "tags", mode="before")
    @classmethod
    def extract_names_from_list(cls, v):
        """Extract names from list of dicts if Mealie returns dict format."""
        if not v:
            return []
        result = []
        for item in v:
            if isinstance(item, dict):
                result.append(item.get("name", ""))
            else:
                result.append(item)
        return result


class RecipeListItem(BaseModel):
    """Recipe summary for list view."""

    id: str
    slug: str
    name: str
    description: str = ""
    image: str | None = None
    recipeCategory: list[str | dict] = Field(default_factory=list)  # Mealie returns dicts
    tags: list[str | dict] = Field(default_factory=list)  # Mealie returns dicts
    rating: int | float | None = None  # Mealie returns float
    dateAdded: datetime | None = None

    @field_validator("recipeCategory", "tags", mode="before")
    @classmethod
    def extract_names_from_list(cls, v):
        """Extract names from list of dicts if Mealie returns dict format."""
        if not v:
            return []
        result = []
        for item in v:
            if isinstance(item, dict):
                result.append(item.get("name", ""))
            else:
                result.append(item)
        return result


class RecipeListResponse(BaseModel):
    """Paginated recipe list response."""

    page: int
    per_page: int
    total: int
    total_pages: int
    items: list[RecipeListItem]
