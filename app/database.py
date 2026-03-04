"""
Async SQLite database setup using SQLAlchemy 2.x + aiosqlite.
All models import Base from here; call init_db() on startup.
"""
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase

from app.config import DATABASE_URL

engine = create_async_engine(DATABASE_URL, echo=False)
AsyncSessionLocal = async_sessionmaker(engine, expire_on_commit=False)


class Base(DeclarativeBase):
    pass


async def get_db():
    """FastAPI dependency that yields an async DB session."""
    async with AsyncSessionLocal() as session:
        yield session


async def init_db():
    """Create all tables on application startup."""
    # Import models so SQLAlchemy can register them before create_all
    import app.models.family   # noqa: F401
    import app.models.agenda   # noqa: F401
    import app.models.tasks    # noqa: F401
    import app.models.meals    # noqa: F401

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
