"""CRUD router for FamilyMember."""

from fastapi import APIRouter, Depends, Response
from loguru import logger
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.family import FamilyMember
from app.schemas.family import FamilyMemberCreate, FamilyMemberOut, FamilyMemberUpdate
from app.utils.crud import delete_model, get_or_404, update_model

router = APIRouter(prefix="/api/family", tags=["family"])


@router.get("/", response_model=list[FamilyMemberOut])
async def list_members(response: Response, db: AsyncSession = Depends(get_db)):
    # No HTTP caching - rely on client-side cache instead
    # Browser cache can't be invalidated when updates occur
    response.headers["Cache-Control"] = "no-cache"
    result = await db.execute(select(FamilyMember).order_by(FamilyMember.id))
    return result.scalars().all()


@router.post("/", response_model=FamilyMemberOut, status_code=201)
async def create_member(payload: FamilyMemberCreate, db: AsyncSession = Depends(get_db)):
    member = FamilyMember(**payload.model_dump())
    db.add(member)
    await db.commit()
    await db.refresh(member)
    logger.info("family.member.created id={} name='{}'", member.id, member.name)
    return member


@router.get("/{member_id}", response_model=FamilyMemberOut)
async def get_member(member_id: int, db: AsyncSession = Depends(get_db)):
    return await get_or_404(db, FamilyMember, member_id, "Family member not found")


@router.put("/{member_id}", response_model=FamilyMemberOut)
async def update_member(member_id: int, payload: FamilyMemberUpdate, db: AsyncSession = Depends(get_db)):
    member = await get_or_404(db, FamilyMember, member_id, "Family member not found")
    await update_model(db, member, payload.model_dump(exclude_unset=True))
    logger.info("family.member.updated id={} name='{}'", member.id, member.name)
    return member


@router.delete("/all", status_code=204)
async def clear_all_members(db: AsyncSession = Depends(get_db)):
    """Delete all family members (for database cleanup).

    WARNING: This will cascade to remove member associations from events, tasks, and meals.
    The items themselves are not deleted, only the member associations are cleared.
    """
    from fastapi.responses import Response as FastAPIResponse
    from sqlalchemy import delete as sa_delete

    await db.execute(sa_delete(FamilyMember))
    await db.commit()
    logger.warning("family.all_cleared - All family members deleted")
    return FastAPIResponse(status_code=204)


@router.delete("/{member_id}", status_code=204)
async def delete_member(member_id: int, db: AsyncSession = Depends(get_db)):
    await delete_model(db, FamilyMember, member_id, "Family member not found")
    logger.info("family.member.deleted id={}", member_id)
