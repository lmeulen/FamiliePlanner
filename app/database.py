"""
Async SQLite database setup using SQLAlchemy 2.x + aiosqlite.
All models import Base from here; call init_db() on startup to run migrations.
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
    """Run Alembic migrations to bring the database schema up to date."""
    import asyncio
    from alembic import command
    from alembic.config import Config

    alembic_cfg = Config("alembic.ini")
    # Run synchronous Alembic command in a thread so we don't block the event loop
    loop = asyncio.get_event_loop()
    await loop.run_in_executor(None, lambda: command.upgrade(alembic_cfg, "head"))

