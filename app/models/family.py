"""Family member model."""
from sqlalchemy import String, Integer
from sqlalchemy.orm import Mapped, mapped_column
from app.database import Base


class FamilyMember(Base):
    __tablename__ = "family_members"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String(50), nullable=False)
    color: Mapped[str] = mapped_column(String(7), default="#4ECDC4")   # hex colour
    avatar: Mapped[str] = mapped_column(String(10), default="👤")       # emoji
