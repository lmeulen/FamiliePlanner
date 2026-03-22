"""Common CRUD helper functions to reduce router duplication."""

from typing import Any, TypeVar

from fastapi import HTTPException
from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import Base

ModelType = TypeVar("ModelType", bound=Base)


async def get_or_404(
    db: AsyncSession,
    model: type[ModelType],
    id_value: Any,
    error_msg: str | None = None,
) -> ModelType:
    """
    Get model instance by ID or raise 404.

    Args:
        db: Database session
        model: SQLAlchemy model class
        id_value: Primary key value
        error_msg: Custom error message (defaults to "{ModelName} not found")

    Returns:
        Model instance

    Raises:
        HTTPException: 404 if not found
    """
    item = await db.get(model, id_value)
    if not item:
        msg = error_msg or f"{model.__name__} not found"
        logger.warning(f"{model.__name__.lower()}.not_found id={id_value}")
        raise HTTPException(404, msg)
    return item


async def update_model(
    db: AsyncSession,
    model_instance: ModelType,
    payload: dict[str, Any],
    exclude_unset: bool = True,
) -> ModelType:
    """
    Update model instance with payload data.

    Args:
        db: Database session
        model_instance: Model instance to update
        payload: Dict of field updates (typically from .model_dump())
        exclude_unset: Only update fields that were explicitly set

    Returns:
        Updated and refreshed model instance
    """
    for key, value in payload.items():
        setattr(model_instance, key, value)
    await db.commit()
    await db.refresh(model_instance)
    return model_instance


async def delete_model(
    db: AsyncSession,
    model: type[ModelType],
    id_value: Any,
    error_msg: str | None = None,
) -> None:
    """
    Delete model instance by ID.

    Args:
        db: Database session
        model: SQLAlchemy model class
        id_value: Primary key value
        error_msg: Custom error message if not found

    Raises:
        HTTPException: 404 if not found
    """
    item = await get_or_404(db, model, id_value, error_msg)
    await db.delete(item)
    await db.commit()
