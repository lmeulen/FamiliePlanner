"""Pydantic schemas for FamilyMember."""

from pydantic import BaseModel, Field


class FamilyMemberBase(BaseModel):
    name: str = Field(min_length=1, max_length=50)
    color: str = "#4ECDC4"
    avatar: str = Field(default="👤", min_length=1, max_length=4)


class FamilyMemberCreate(FamilyMemberBase):
    pass


class FamilyMemberUpdate(FamilyMemberBase):
    pass


class FamilyMemberOut(FamilyMemberBase):
    id: int

    model_config = {"from_attributes": True}
