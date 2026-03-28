"""Grocery list CRUD router."""

from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from loguru import logger
from sqlalchemy import delete as sql_delete
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.grocery import GroceryCategory, GroceryItem, GroceryProductLearning
from app.schemas.grocery import (
    GroceryCategoryCreate,
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


@router.post("/categories", response_model=GroceryCategoryOut, status_code=201)
async def create_category(payload: GroceryCategoryCreate, db: AsyncSession = Depends(get_db)):
    """Create new grocery category."""
    # Get max sort_order and add 10
    result = await db.execute(select(GroceryCategory.sort_order).order_by(GroceryCategory.sort_order.desc()).limit(1))
    max_sort = result.scalar_one_or_none() or 0

    category = GroceryCategory(
        name=payload.name,
        icon=payload.icon,
        color=payload.color,
        sort_order=max_sort + 10,
    )
    db.add(category)
    await db.commit()
    await db.refresh(category)
    logger.info("grocery.category.created id={} name='{}'", category.id, category.name)
    return category


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


@router.delete("/categories/{category_id}", status_code=204)
async def delete_category(category_id: int, db: AsyncSession = Depends(get_db)):
    """Delete category and move all items to 'Overig' (last category by sort_order)."""
    category = await db.get(GroceryCategory, category_id)
    if not category:
        raise HTTPException(404, "Category not found")

    # Get "Overig" category (last by sort_order)
    result = await db.execute(select(GroceryCategory).order_by(GroceryCategory.sort_order.desc()).limit(1))
    overig_category = result.scalar_one()

    # Prevent deleting the last category
    if overig_category.id == category_id:
        result = await db.execute(select(GroceryCategory))
        all_categories = result.scalars().all()
        if len(all_categories) == 1:
            raise HTTPException(400, "Cannot delete the last category")
        # If deleting "Overig", pick the second-to-last category
        result = await db.execute(
            select(GroceryCategory)
            .where(GroceryCategory.id != category_id)
            .order_by(GroceryCategory.sort_order.desc())
            .limit(1)
        )
        overig_category = result.scalar_one()

    # Move all items from this category to "Overig"
    await db.execute(
        update(GroceryItem).where(GroceryItem.category_id == category_id).values(category_id=overig_category.id)
    )

    # Move all learning entries to "Overig"
    await db.execute(
        update(GroceryProductLearning)
        .where(GroceryProductLearning.category_id == category_id)
        .values(category_id=overig_category.id)
    )

    await db.delete(category)
    await db.commit()
    logger.info(
        "grocery.category.deleted id={} name='{}' (items moved to category_id={})",
        category_id,
        category.name,
        overig_category.id,
    )


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
        item.checked_at = datetime.now(timezone.utc) if payload.checked else None

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


@router.delete("/all", status_code=204)
async def clear_all_groceries(db: AsyncSession = Depends(get_db)):
    """Delete all grocery items and learning data (for database cleanup)."""
    from fastapi.responses import Response as FastAPIResponse
    from sqlalchemy import delete as sa_delete

    # Delete all grocery items
    await db.execute(sa_delete(GroceryItem))
    # Delete all learning data
    await db.execute(sa_delete(GroceryProductLearning))
    await db.commit()
    logger.warning("grocery.all_cleared - All grocery items and learning data deleted")
    return FastAPIResponse(status_code=204)


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
    result = await db.execute(select(GroceryProductLearning).where(GroceryProductLearning.product_name == product_name))
    learning = result.scalar_one_or_none()

    if learning:
        learning.category_id = category_id
        learning.usage_count += 1
        learning.last_used = datetime.now(timezone.utc)
    else:
        learning = GroceryProductLearning(product_name=product_name, category_id=category_id, usage_count=1)
        db.add(learning)

    await db.commit()
