"""
NSE Bulk & Block Deals Fetcher
Endpoints:
  Bulk deals:  /api/corporates/bulk-deals
  Block deals: /api/corporates/block-deals

Bulk deal  = trade > 0.5% of total shares in a single session (disclosed EOD)
Block deal = negotiated trade of min 5 lakh shares or ₹10Cr (disclosed same day)

Both are strong signals — large players don't accidentally cross these thresholds.
"""
import logging
from datetime import datetime, date
from typing import Optional, Dict

from fetchers_base import BaseFetcher, NSESession
from settings import settings

logger = logging.getLogger(__name__)


class BulkDealsFetcher(BaseFetcher):
    source = "bulk"
    fetch_interval = settings.fetch_interval_bulk

    async def fetch(self) -> list:
        session = await self._get_nse_session()
        today = date.today().strftime("%d-%m-%Y")

        bulk_data = await session.get_json(
            "/corporates/bulk-deals",
            params={"from_date": today, "to_date": today},
        )
        block_data = await session.get_json(
            "/corporates/block-deals",
            params={"from_date": today, "to_date": today},
        )

        bulk_items = (bulk_data if isinstance(bulk_data, list) else bulk_data.get("data", []))
        block_items = (block_data if isinstance(block_data, list) else block_data.get("data", []))

        # Tag each item with its deal type
        for item in bulk_items:
            item["_deal_kind"] = "bulk"
        for item in block_items:
            item["_deal_kind"] = "block"

        all_items = bulk_items + block_items
        logger.info(f"BulkDealsFetcher: {len(bulk_items)} bulk + {len(block_items)} block = {len(all_items)} total")
        return all_items

    def _parse_item(self, item: dict) -> tuple[Optional[str], Optional[datetime], dict]:
        ticker = (item.get("Symbol") or item.get("symbol") or "").strip().upper()
        if not ticker:
            return None, None, {}

        # Convert trade value to crores for threshold check
        try:
            qty = float(item.get("Quantity Traded", item.get("quantity", 0)) or 0)
            price = float(item.get("Trade Price /Wted. Avg. Price", item.get("price", 0)) or 0)
            value_cr = (qty * price) / 1e7
        except (ValueError, TypeError):
            value_cr = 0.0

        # Skip tiny deals
        if value_cr < 1.0:
            return None, None, {}

        date_str = item.get("Date", item.get("date", ""))
        try:
            event_date = datetime.strptime(date_str, "%d-%b-%Y")
        except (ValueError, TypeError):
            event_date = datetime.utcnow()

        # Determine buyer type for insider signal detection
        client_name = item.get("Client Name", item.get("client", "")).strip()
        buy_sell = item.get("Buy/Sell", item.get("type", "")).strip().upper()

        canonical = {
            "ticker": ticker,
            "company": item.get("Name of the Scrip", item.get("company", "")),
            "deal_kind": item.get("_deal_kind", "bulk"),
            "client_name": client_name,
            "buy_sell": buy_sell,
            "quantity": qty,
            "price": price,
            "value_cr": round(value_cr, 2),
            "date": date_str,
            "exchange": "NSE",
            # Flag if client name looks like a promoter/institutional entity
            "looks_like_promoter": _is_likely_promoter(client_name),
            "looks_like_fii": _is_likely_fii(client_name),
        }

        return ticker, event_date, canonical

    async def run(self) -> Dict:
        """Execute the bulk deals fetch cycle."""
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
                await self._record_run(db, "bulk", events_fetched, events_new, 0)

                return {
                    "events_fetched": events_fetched,
                    "events_new": events_new,
                    "signals_generated": 0,
                    "error": None,
                }

            except Exception as e:
                logger.exception(f"BulkDealsFetcher error: {e}")
                await self._record_run(db, "bulk", 0, 0, 0, str(e))
                return {
                    "events_fetched": 0,
                    "events_new": 0,
                    "signals_generated": 0,
                    "error": str(e),
                }


def _is_likely_promoter(name: str) -> bool:
    """Heuristic: does the entity name suggest promoter/family group ownership?"""
    if not name:
        return False
    name_upper = name.upper()
    promoter_keywords = [
        "PROMOTER", "HOLDING", "ENTERPRISES LTD", "PVT LTD", "PRIVATE LIMITED",
        "FAMILY TRUST", "SONS", "BROTHERS", "GROUP", "VENTURES",
        # Common promoter entity suffixes in India
        "INVESTMENTS", "CAPITAL",
    ]
    return any(kw in name_upper for kw in promoter_keywords)


def _is_likely_fii(name: str) -> bool:
    """Heuristic: does the entity name suggest a foreign institutional investor?"""
    if not name:
        return False
    name_upper = name.upper()
    fii_keywords = [
        "MAURITIUS", "SINGAPORE", "CAYMAN", "FII", "FOREIGN",
        "GOLDMAN", "MORGAN STANLEY", "BLACKROCK", "VANGUARD", "FIDELITY",
        "NOMURA", "SOCIETE GENERALE", "BNP PARIB", "DEUTSCHE",
        "SMALLCAP WORLD", "EMERGING MARKETS",
    ]
    return any(kw in name_upper for kw in fii_keywords)