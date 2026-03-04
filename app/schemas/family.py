"""Pydantic schemas for FamilyMember."""
from pydantic import BaseModel


class FamilyMemberBase(BaseModel):
    name: str
    color: str = "#4ECDC4"
    avatar: str = "👤"


class FamilyMemberCreate(FamilyMemberBase):
    pass


class FamilyMemberUpdate(FamilyMemberBase):
    pass


class FamilyMemberOut(FamilyMemberBase):
    id: int

    model_config = {"from_attributes": True}
