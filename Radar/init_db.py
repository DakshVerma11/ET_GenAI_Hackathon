"""
Initialize the database — creates all tables and seeds default alert configs.
Run once: python init_db.py
"""
import asyncio
import logging
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from models import Base, AlertConfig
from settings import settings

logger = logging.getLogger(__name__)


async def init_db():
    """Create all tables and seed default alert configs."""
    engine = create_async_engine(
        settings.database_url,
        echo=False,
        poolclass=StaticPool,
        future=True,
    )

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    # Seed default alert triggers
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with async_session() as session:
        # Check if alerts already exist
        from sqlalchemy import select
        result = await session.execute(select(AlertConfig))
        if not result.scalars().first():
            default_alerts = [
                AlertConfig(
                    name="Insider trades > ₹50L",
                    trigger_type="insider",
                    threshold_value=0.5,
                    enabled=True
                ),
                AlertConfig(
                    name="Bulk/block deals > 1%",
                    trigger_type="bulk",
                    threshold_value=1.0,
                    enabled=True
                ),
                AlertConfig(
                    name="PAT beat > 20%",
                    trigger_type="result",
                    threshold_value=20.0,
                    enabled=True
                ),
                AlertConfig(
                    name="NLP tone shift > 2σ",
                    trigger_type="nlp",
                    threshold_value=2.0,
                    enabled=True
                ),
            ]
            session.add_all(default_alerts)
            await session.commit()
            logger.info("✓ Default alert configs created")

    await engine.dispose()
    logger.info(f"✓ Database initialized at: {settings.database_url}")


def get_engine():
    """Create the async SQLAlchemy engine."""
    return create_async_engine(
        settings.database_url,
        echo=False,
        poolclass=StaticPool,
        future=True,
    )


def get_session_factory(engine):
    """Create an async session factory."""
    return sessionmaker(
        engine,
        class_=AsyncSession,
        expire_on_commit=False,
        future=True,
    )


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    asyncio.run(init_db())