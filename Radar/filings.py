"""
NSE Corporate Filings Fetcher
Endpoint: /api/corporates/filings?index=equities&from_date=...&to_date=...

Returns board meeting outcomes, capex announcements, concall transcripts,
regulatory filings, AGM notices, etc.
"""
import logging
from datetime import datetime, date, timedelta
from typing import Optional, Dict

from fetchers_base import BaseFetcher, NSESession
from settings import settings

logger = logging.getLogger(__name__)


class FilingsFetcher(BaseFetcher):
    source = "filings"
    fetch_interval = settings.fetch_interval_filings

    # Filing types we care about — ignore routine housekeeping filings
    SIGNAL_FILING_TYPES = {
        "Board Meeting",
        "Financial Results",
        "Analyst/Investor Meet",
        "Press Release",
        "Change in Management",
        "Acquisitions/Mergers",
        "Buyback",
        "Dividend",
        "Open Offer",
        "Allotment of Shares",
        "Qualified Institutions Placement",
        "Preferential Issue",
        "Rights Issue",
        "Trading Window",          # useful as leading indicator of results
        "Outcome of Board Meeting",
        "Shareholding Pattern",
    }

    async def fetch(self) -> list:
        session = await self._get_nse_session()
        today = date.today()
        from_date = (today - timedelta(days=1)).strftime("%d-%m-%Y")
        to_date = today.strftime("%d-%m-%Y")

        data = await session.get_json(
            "/corporates/filings",
            params={
                "index": "equities",
                "from_date": from_date,
                "to_date": to_date,
            },
        )

        items = data if isinstance(data, list) else data.get("data", [])
        logger.info(f"FilingsFetcher: fetched {len(items)} raw filings")
        return items

    def _parse_item(self, item: dict) -> tuple[Optional[str], Optional[datetime], dict]:
        ticker = (item.get("symbol") or item.get("Symbol") or "").strip().upper()
        if not ticker:
            return None, None, {}

        filing_type = item.get("purpose", item.get("bm_purpose", ""))
        if filing_type and not any(t in filing_type for t in self.SIGNAL_FILING_TYPES):
            return None, None, {}

        date_str = item.get("date", item.get("bm_date", ""))
        try:
            event_date = datetime.strptime(date_str, "%d-%m-%Y")
        except (ValueError, TypeError):
            event_date = datetime.utcnow()

        canonical = {
            "ticker": ticker,
            "company": item.get("company", item.get("sm_name", "")),
            "filing_type": filing_type,
            "description": item.get("description", item.get("bm_desc", "")),
            "date": date_str,
            "attachment": item.get("attchmnt", ""),
            "exchange": "NSE",
        }

        return ticker, event_date, canonical

    async def run(self) -> Dict:
        """Execute the filing fetch cy cle."""
        from typing import Dict
        async with self.session_factory() as db:
            try:
                items = await self.fetch()
                events_fetched = len(items)
                events_new = 0

                for item in items:
                    ticker, event_date, canonical = self._parse_item(item)
                    if ticker:
                        is_new = await self._dedup_and_store(
                            db, self.source, ticker, event_date, canonical
                        )
                        if is_new:
                            events_new += 1

                await db.commit()
                await self._record_run(db, "filings", events_fetched, events_new, 0)

                return {
                    "events_fetched": events_fetched,
                    "events_new": events_new,
                    "signals_generated": 0,
                    "error": None,
                }

            except Exception as e:
                logger.exception(f"FilingsFetcher error: {e}")
                await self._record_run(db, "filings", 0, 0, 0, str(e))
                return {
                    "events_fetched": 0,
                    "events_new": 0,
                    "signals_generated": 0,
                    "error": str(e),
                }