"""
Dependency injection for FastAPI routes.
Provides database sessions for endpoints.
"""
from typing import AsyncGenerator
from sqlalchemy.ext.asyncio import AsyncSession
from init_db import get_engine, get_session_factory

_engine = None
_session_factory = None


def _get_factory():
    """Lazy initialization of session factory."""
    global _engine, _session_factory
    if _session_factory is None:
        _engine = get_engine()
        _session_factory = get_session_factory(_engine)
    return _session_factory


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """FastAPI dependency to get a database session."""
    factory = _get_factory()
    async with factory() as session:
        yield session
