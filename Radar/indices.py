"""
NSE Indices + Quote Fetcher
Provides price context for signal scoring:
- Current price at time of signal
- Volume z-score vs 20-day average
- Sector index performance (for sentiment context)

Endpoints:
  All indices: /api/allIndices
  Quote:       /api/quote-equity?symbol=RELIANCE
  Chart data:  /api/chart-databyindex?index=RELIANCE&indices=true
"""
import logging
from datetime import datetime
from typing import Optional, Dict

from fetchers_base import BaseFetcher, NSESession
from settings import settings

logger = logging.getLogger(__name__)

# NSE sector index mapping
SECTOR_INDEX_MAP = {
    "NIFTY BANK": "Banks",
    "NIFTY IT": "IT",
    "NIFTY INFRA": "Infra",
    "NIFTY PHARMA": "Pharma",
    "NIFTY FMCG": "FMCG",
    "NIFTY AUTO": "Auto",
    "NIFTY PSU BANK": "PSU Banks",
    "NIFTY ENERGY": "Energy",
    "NIFTY METAL": "Metal",
    "NIFTY REALTY": "Realty",
    "NIFTY MEDIA": "Media",
    "NIFTY FINANCIAL SERVICES": "Financials",
}


class IndicesFetcher(BaseFetcher):
    """
    Fetches all NSE indices every minute.
    Stored for sector heatmap and signal context enrichment.
    """
    source = "indices"
    fetch_interval = settings.fetch_interval_indices

    async def fetch(self) -> list:
        session = await self._get_nse_session()
        data = await session.get_json("/allIndices")
        items = data.get("data", []) if isinstance(data, dict) else []
        logger.debug(f"IndicesFetcher: {len(items)} indices")
        return items

    def _parse_item(self, item: dict) -> tuple[Optional[str], Optional[datetime], dict]:
        index_name = item.get("index", "").strip()
        if not index_name:
            return None, None, {}

        canonical = {
            "index_name": index_name,
            "sector": SECTOR_INDEX_MAP.get(index_name, ""),
            "last": item.get("last", 0),
            "change": item.get("change", 0),
            "pct_change": item.get("percentChange", 0),
            "advances": item.get("advances", 0),
            "declines": item.get("declines", 0),
            "timestamp": datetime.utcnow().isoformat(),
        }

        return index_name, datetime.utcnow(), canonical

    async def run(self) -> Dict:
        """Execute the indices fetch cycle."""
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
                await self._record_run(db, "indices", events_fetched, events_new, 0)

                return {
                    "events_fetched": events_fetched,
                    "events_new": events_new,
                    "signals_generated": 0,
                    "error": None,
                }

            except Exception as e:
                logger.exception(f"IndicesFetcher error: {e}")
                await self._record_run(db, "indices", 0, 0, 0, str(e))
                return {
                    "events_fetched": 0,
                    "events_new": 0,
                    "signals_generated": 0,
                    "error": str(e),
                }


async def get_quote(ticker: str) -> dict:
    """
    Fetch real-time quote for a single ticker.
    Returns price, volume, 52w high/low, delivery %.
    Used by the signal scorer to enrich signals with price context.
    """
    session = await NSESession.get()
    data = await session.get_json("/quote-equity", params={"symbol": ticker})

    if not data:
        return {}

    price_info = data.get("priceInfo", {})
    trade_info = data.get("tradeInfo", {})
    security_info = data.get("securityInfo", {})

    return {
        "ticker": ticker,
        "last_price": price_info.get("lastPrice", 0),
        "change_pct": price_info.get("pChange", 0),
        "week_52_high": price_info.get("weekHighLow", {}).get("max", 0),
        "week_52_low": price_info.get("weekHighLow", {}).get("min", 0),
        "total_traded_volume": trade_info.get("totalTradedVolume", 0),
        "total_traded_value": trade_info.get("totalTradedValue", 0),
        "delivery_qty": trade_info.get("deliveryQuantity", 0),
        "delivery_pct": trade_info.get("deliveryToTradedQuantity", 0),
        "market_cap_cr": security_info.get("issuedCap", 0),
        "isin": security_info.get("isin", ""),
    }


async def get_sector_performance() -> dict[str, dict]:
    """
    Returns sector-level performance dict for heatmap.
    {sector_name: {change_pct, advances, declines}}
    """
    session = await NSESession.get()
    data = await session.get_json("/allIndices")
    items = data.get("data", []) if isinstance(data, dict) else []

    result = {}
    for item in items:
        index_name = item.get("index", "")
        sector = SECTOR_INDEX_MAP.get(index_name)
        if sector:
            result[sector] = {
                "change_pct": item.get("percentChange", 0),
                "advances": item.get("advances", 0),
                "declines": item.get("declines", 0),
                "last": item.get("last", 0),
            }
    return result