"""Shared pytest fixtures: in-memory SQLite + async test client."""
import os

# Disable authentication for all tests
os.environ.setdefault("AUTH_DISABLED", "1")

import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.database import Base, get_db

TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"


@pytest_asyncio.fixture(scope="function")
async def db_engine():
    engine = create_async_engine(TEST_DATABASE_URL, echo=False)
    async with engine.begin() as conn:
        # Register all models
        import app.models.family  # noqa: F401
        import app.models.agenda  # noqa: F401
        import app.models.tasks   # noqa: F401
        import app.models.meals   # noqa: F401
        import app.models.settings  # noqa: F401
        await conn.run_sync(Base.metadata.create_all)
    yield engine
    await engine.dispose()


@pytest_asyncio.fixture(scope="function")
async def client(db_engine):
    """AsyncClient with a fresh in-memory DB per test."""
    # Import app after engine is set up to avoid triggering setup_logging early
    from app.main import app

    test_session_factory = async_sessionmaker(db_engine, expire_on_commit=False)

    async def override_get_db():
        async with test_session_factory() as session:
            yield session

    app.dependency_overrides[get_db] = override_get_db

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        yield ac

    app.dependency_overrides.clear()
