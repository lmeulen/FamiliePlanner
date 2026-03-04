"""CRUD router for FamilyMember."""
from fastapi import APIRouter, Depends, HTTPException
from loguru import logger
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.family import FamilyMember
from app.schemas.family import FamilyMemberCreate, FamilyMemberOut, FamilyMemberUpdate

router = APIRouter(prefix="/api/family", tags=["family"])


@router.get("/", response_model=list[FamilyMemberOut])
async def list_members(db: AsyncSession = Depends(get_db)):
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
    member = await db.get(FamilyMember, member_id)
    if not member:
        logger.warning("family.member.not_found id={}", member_id)
        raise HTTPException(404, "Family member not found")
    return member


@router.put("/{member_id}", response_model=FamilyMemberOut)
async def update_member(
    member_id: int, payload: FamilyMemberUpdate, db: AsyncSession = Depends(get_db)
):
    member = await db.get(FamilyMember, member_id)
    if not member:
        logger.warning("family.member.not_found id={}", member_id)
        raise HTTPException(404, "Family member not found")
    for key, value in payload.model_dump(exclude_unset=True).items():
        setattr(member, key, value)
    await db.commit()
    await db.refresh(member)
    logger.info("family.member.updated id={} name='{}'", member.id, member.name)
    return member


@router.delete("/{member_id}", status_code=204)
async def delete_member(member_id: int, db: AsyncSession = Depends(get_db)):
    member = await db.get(FamilyMember, member_id)
    if not member:
        logger.warning("family.member.not_found id={}", member_id)
        raise HTTPException(404, "Family member not found")
    await db.delete(member)
    await db.commit()
    logger.info("family.member.deleted id={}", member_id)
