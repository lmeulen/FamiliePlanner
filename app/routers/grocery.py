"""Grocery list CRUD router."""

from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from loguru import logger
from sqlalchemy import delete as sql_delete
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.grocery import GroceryCategory, GroceryItem, GroceryProductLearning
from app.schemas.grocery import (
    GroceryCategoryOut,
    GroceryCategoryReorder,
    GroceryItemCreate,
    GroceryItemOut,
    GroceryItemUpdate,
    GroceryLearningSuggestion,
)
from app.utils.grocery_parser import display_product_name, parse_grocery_input

router = APIRouter(prefix="/api/grocery", tags=["grocery"])


# ── Categories ────────────────────────────────────────────────


@router.get("/categories", response_model=list[GroceryCategoryOut])
async def list_categories(db: AsyncSession = Depends(get_db)):
    """Get all grocery categories ordered by sort_order."""
    result = await db.execute(select(GroceryCategory).order_by(GroceryCategory.sort_order))
    return result.scalars().all()


@router.put("/categories/reorder")
async def reorder_categories(items: list[GroceryCategoryReorder], db: AsyncSession = Depends(get_db)):
    """Update category sort order."""
    for item in items:
        await db.execute(
            update(GroceryCategory).where(GroceryCategory.id == item.id).values(sort_order=item.sort_order)
        )
    await db.commit()
    logger.info("grocery.categories.reordered count={}", len(items))
    return {"message": "Categories reordered"}


# ── Items ─────────────────────────────────────────────────────


@router.get("/items", response_model=list[GroceryItemOut])
async def list_items(db: AsyncSession = Depends(get_db)):
    """Get all grocery items, ordered by checked status, then category sort_order."""
    result = await db.execute(
        select(GroceryItem)
        .join(GroceryCategory)
        .order_by(GroceryItem.checked, GroceryCategory.sort_order, GroceryItem.sort_order)
    )
    return result.scalars().all()


@router.post("/items", response_model=GroceryItemOut, status_code=201)
async def create_item(payload: GroceryItemCreate, db: AsyncSession = Depends(get_db)):
    """
    Create grocery item with smart parsing and category learning.

    Input: "2 kg tomaten" → parses quantity, unit, product name.
    Suggests category based on learning history if not provided.
    """
    # Parse input
    quantity, unit, product_name = parse_grocery_input(payload.raw_input)
    display_name = display_product_name(product_name)

    # Determine category
    category_id = payload.category_id

    if not category_id:
        # Check learning table for suggestion
        learning = await db.execute(
            select(GroceryProductLearning)
            .where(GroceryProductLearning.product_name == product_name)
            .order_by(GroceryProductLearning.usage_count.desc())
            .limit(1)
        )
        learned = learning.scalar_one_or_none()

        if learned:
            category_id = learned.category_id
        else:
            # Default to "Overig" (last category by sort_order)
            result = await db.execute(select(GroceryCategory.id).order_by(GroceryCategory.sort_order.desc()).limit(1))
            category_id = result.scalar_one()

    # Create item
    item = GroceryItem(
        product_name=product_name,
        display_name=display_name,
        quantity=quantity,
        unit=unit,
        category_id=category_id,
        checked=False,
    )
    db.add(item)
    await db.commit()
    await db.refresh(item)

    # Update learning
    await update_learning(db, product_name, category_id)

    logger.info("grocery.item.created id={} product='{}' category={}", item.id, product_name, category_id)
    return item


@router.patch("/items/{item_id}", response_model=GroceryItemOut)
async def update_item(item_id: int, payload: GroceryItemUpdate, db: AsyncSession = Depends(get_db)):
    """Update item (check/uncheck or change category)."""
    item = await db.get(GroceryItem, item_id)
    if not item:
        raise HTTPException(404, "Item not found")

    old_category = item.category_id

    if payload.category_id is not None:
        item.category_id = payload.category_id
        # Update learning when category changed manually
        if old_category != payload.category_id:
            await update_learning(db, item.product_name, payload.category_id)

    if payload.checked is not None:
        item.checked = payload.checked
        item.checked_at = datetime.utcnow() if payload.checked else None

    await db.commit()
    await db.refresh(item)
    logger.info("grocery.item.updated id={} checked={}", item_id, item.checked)
    return item


@router.delete("/items/done", status_code=204)
async def clear_done_items(db: AsyncSession = Depends(get_db)):
    """Delete all checked items."""
    result = await db.execute(sql_delete(GroceryItem).where(GroceryItem.checked == True))  # noqa: E712
    await db.commit()
    count = result.rowcount
    logger.info("grocery.items.cleared_done count={}", count)


@router.delete("/items/{item_id}", status_code=204)
async def delete_item(item_id: int, db: AsyncSession = Depends(get_db)):
    """Delete single grocery item."""
    item = await db.get(GroceryItem, item_id)
    if not item:
        raise HTTPException(404, "Item not found")

    await db.delete(item)
    await db.commit()
    logger.info("grocery.item.deleted id={}", item_id)


# ── Learning ──────────────────────────────────────────────────


@router.get("/suggest/{product_name}", response_model=GroceryLearningSuggestion | None)
async def suggest_category(product_name: str, db: AsyncSession = Depends(get_db)):
    """Get category suggestion for a product based on learning history."""
    normalized = product_name.lower().strip()

    result = await db.execute(
        select(GroceryProductLearning)
        .where(GroceryProductLearning.product_name == normalized)
        .order_by(GroceryProductLearning.usage_count.desc())
        .limit(1)
    )
    learned = result.scalar_one_or_none()

    if not learned:
        return None

    return GroceryLearningSuggestion(
        product_name=normalized, suggested_category_id=learned.category_id, confidence=learned.usage_count
    )


async def update_learning(db: AsyncSession, product_name: str, category_id: int):
    """Update product-category learning."""
    result = await db.execute(
        select(GroceryProductLearning).where(GroceryProductLearning.product_name == product_name)
    )
    learning = result.scalar_one_or_none()

    if learning:
        learning.category_id = category_id
        learning.usage_count += 1
        learning.last_used = datetime.utcnow()
    else:
        learning = GroceryProductLearning(product_name=product_name, category_id=category_id, usage_count=1)
        db.add(learning)

    await db.commit()
