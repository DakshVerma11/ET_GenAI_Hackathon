"""
Base fetcher — handles NSE session cookies, rate limiting, retry, and dedup.

NSE India requires:
  1. A GET to the homepage first to get session cookies
  2. Subsequent API calls with those cookies + the right headers
  3. Respectful rate limiting (2–5 sec between calls)
"""
import asyncio
import hashlib
import json
import logging
from abc import ABC, abstractmethod
from datetime import datetime
from typing import Any, Optional, Dict

import aiohttp
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from models import RawEvent, PipelineRun
from settings import settings

logger = logging.getLogger(__name__)

NSE_HEADERS = {
    "User-Agent": settings.nse_user_agent,
    "Accept": "*/*",
    "Accept-Language": "en-US,en;q=0.9",
    "Accept-Encoding": "gzip, deflate, br",
    "Referer": "https://www.nseindia.com/",
    "Connection": "keep-alive",
    "sec-fetch-dest": "empty",
    "sec-fetch-mode": "cors",
    "sec-fetch-site": "same-origin",
}


class NSESession:
    """
    Manages a persistent aiohttp session with NSE cookies.
    NSE requires visiting the homepage before API calls will work.
    """
    _instance: Optional["NSESession"] = None
    _session: Optional[aiohttp.ClientSession] = None
    _cookies_initialized = False

    @classmethod
    async def get(cls) -> "NSESession":
        if cls._instance is None:
            cls._instance = cls()
        if not cls._cookies_initialized:
            await cls._instance._init_cookies()
        return cls._instance

    async def _init_cookies(self):
        if self._session is None or self._session.closed:
            self._session = aiohttp.ClientSession(headers=NSE_HEADERS)
        try:
            async with self._session.get(
                settings.nse_base_url, timeout=aiohttp.ClientTimeout(total=15)
            ) as resp:
                _ = await resp.text()
                self._cookies_initialized = True
                logger.info("NSE session initialized (cookies set)")
                await asyncio.sleep(1.5)
        except Exception as e:
            logger.warning(f"NSE cookie init failed: {e} - will retry on next fetch")

    async def get_json(self, path: str, params: dict = None) -> dict:
        """Fetch JSON from NSE API with retry and cookie refresh."""
        url = f"{settings.nse_api_base}{path}"
        for attempt in range(3):
            try:
                async with self._session.get(
                    url,
                    params=params,
                    timeout=aiohttp.ClientTimeout(total=20),
                ) as resp:
                    if resp.status == 401 or resp.status == 403:
                        logger.warning(f"NSE session expired, refreshing cookies...")
                        self._cookies_initialized = False
                        await self._init_cookies()
                        continue
                    if resp.status != 200:
                        logger.warning(f"NSE API {path} returned {resp.status}")
                        return {}
                    return await resp.json(content_type=None)
            except aiohttp.ClientError as e:
                logger.warning(f"NSE fetch attempt {attempt+1} failed: {e}")
                await asyncio.sleep(2 ** attempt)
        return {}

    async def close(self):
        if self._session and not self._session.closed:
            await self._session.close()


class BaseFetcher(ABC):
    """
    Base class for all data fetchers.
    Handles deduplication, session management, rate limiting.
    """

    def __init__(self, session_factory):
        self.session_factory = session_factory
        self.nse_session = None

    async def _get_nse_session(self):
        if self.nse_session is None:
            self.nse_session = await NSESession.get()
        return self.nse_session

    @staticmethod
    def _compute_content_hash(data: Any) -> str:
        """SHA256 hash of event data for deduplication."""
        content = json.dumps(data, sort_keys=True, default=str)
        return hashlib.sha256(content.encode()).hexdigest()

    async def _dedup_and_store(
        self,
        db: AsyncSession,
        source: str,
        ticker: str,
        event_date: datetime,
        raw_data: Dict,
    ) -> bool:
        """
        Store a RawEvent if not already seen (using content_hash).
        Returns True if newly inserted, False if duplicate.
        """
        content_hash = self._compute_content_hash(raw_data)

        # Check if already exists
        result = await db.execute(
            select(RawEvent).where(RawEvent.content_hash == content_hash)
        )
        if result.scalars().first():
            logger.debug(f"Duplicate event skipped: {source} / {ticker}")
            return False

        # Insert new event
        event = RawEvent(
            source=source,
            ticker=ticker,
            event_date=event_date,
            raw_json=raw_data,
            content_hash=content_hash,
            processed=False,
        )
        db.add(event)
        await db.flush()
        return True

    async def _record_run(
        self,
        db: AsyncSession,
        fetcher_name: str,
        events_fetched: int,
        events_new: int,
        signals_generated: int,
        error: str = None,
    ):
        """Log this fetch cycle to PipelineRun."""
        run = PipelineRun(
            fetcher=fetcher_name,
            events_fetched=events_fetched,
            events_new=events_new,
            signals_generated=signals_generated,
            error=error,
            success=error is None,
        )
        db.add(run)
        await db.commit()

    @abstractmethod
    async def run(self) -> Dict:
        """
        Execute the fetch. Must return:
        {
            "events_fetched": int,
            "events_new": int,
            "signals_generated": int,
            "error": str or None,
        }
        """
        pass

    Abstract base for all NSE data fetchers.
    Handles: deduplication via content hash, PipelineRun logging, error handling.
    """

    source: str = "unknown"
    fetch_interval: int = 300

    def __init__(self, session_factory):
        self.session_factory = session_factory

    def _content_hash(self, data: Any) -> str:
        """SHA-256 of the raw JSON — used as dedup key."""
        serialized = json.dumps(data, sort_keys=True, default=str)
        return hashlib.sha256(serialized.encode()).hexdigest()

    async def _is_duplicate(self, db: AsyncSession, content_hash: str) -> bool:
        result = await db.execute(
            select(RawEvent).where(RawEvent.content_hash == content_hash).limit(1)
        )
        return result.scalar_one_or_none() is not None

    async def _store_raw(
        self,
        db: AsyncSession,
        ticker: str,
        event_date: datetime,
        raw_json: dict,
        content_hash: str,
    ) -> RawEvent:
        event = RawEvent(
            source=self.source,
            ticker=ticker,
            event_date=event_date,
            raw_json=raw_json,
            content_hash=content_hash,
        )
        db.add(event)
        await db.flush()
        return event

    async def run(self) -> dict:
        """
        Entry point called by the scheduler.
        Returns stats dict: {events_fetched, events_new, signals_generated, error}
        """
        run = PipelineRun(fetcher=self.source, started_at=datetime.utcnow())
        stats = {"events_fetched": 0, "events_new": 0, "signals_generated": 0, "error": None}

        async with self.session_factory() as db:
            try:
                raw_items = await self.fetch()
                stats["events_fetched"] = len(raw_items)

                new_events = []
                for item in raw_items:
                    ticker, event_date, raw_json = self._parse_item(item)
                    if not ticker:
                        continue
                    h = self._content_hash(raw_json)
                    if await self._is_duplicate(db, h):
                        continue
                    event = await self._store_raw(db, ticker, event_date, raw_json, h)
                    new_events.append(event)
                    stats["events_new"] += 1

                await db.commit()

                # Signal generation happens after commit so IDs are available
                if new_events:
                    from app.signals.generator import SignalGenerator
                    generator = SignalGenerator(self.session_factory)
                    for event in new_events:
                        sig_count = await generator.process_event(event)
                        stats["signals_generated"] += sig_count

                run.events_fetched = stats["events_fetched"]
                run.events_new = stats["events_new"]
                run.signals_generated = stats["signals_generated"]
                run.success = True

            except Exception as e:
                logger.exception(f"{self.source} fetcher error: {e}")
                stats["error"] = str(e)
                run.error = str(e)
                run.success = False
                await db.rollback()
            finally:
                run.finished_at = datetime.utcnow()
                db.add(run)
                await db.commit()

        return stats

    @abstractmethod
    async def fetch(self) -> list[dict]:
        """Fetch raw items from the data source. Returns list of raw dicts."""
        ...

    @abstractmethod
    def _parse_item(self, item: dict) -> tuple[str, datetime, dict]:
        """
        Extract (ticker, event_date, canonical_json) from a raw item.
        Return (None, None, None) to skip the item.
    """"""