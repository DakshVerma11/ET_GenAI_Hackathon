"""
NSE Insider Trading Fetcher
Endpoint: /api/corporates/insider-trading

SEBI mandates disclosure of insider trades within 2 trading days.
Promoter/director purchases are strong signals — these are people who
know the company better than anyone else.

Key signal patterns:
1. Single large buy (>₹50L) by a director/promoter
2. Cluster buy — multiple insiders buying in the same week
3. CEO/MD buying — highest conviction insider signal
4. Post-result buying — insiders buying after results release
"""
import logging
from datetime import datetime, date, timedelta
from typing import Optional, Dict

from fetchers_base import BaseFetcher, NSESession
from settings import settings
from typing import Dict

logger = logging.getLogger(__name__)

# SEBI categories that constitute "insider" for signal purposes
SIGNAL_CATEGORIES = {
    "Promoter",
    "Promoter Group",
    "Director",
    "Key Managerial Personnel",
    "Designated Person",
    "Chairman",
    "Managing Director",
    "Chief Executive Officer",
    "Chief Financial Officer",
    "Chief Operating Officer",
}


class InsiderTradingFetcher(BaseFetcher):
    source = "insider"
    fetch_interval = settings.fetch_interval_insider

    async def fetch(self) -> list:
        session = await self._get_nse_session()
        today = date.today()
        from_date = (today - timedelta(days=7)).strftime("%d-%m-%Y")
        to_date = today.strftime("%d-%m-%Y")

        data = await session.get_json(
            "/corporates/insider-trading",
            params={
                "from_date": from_date,
                "to_date": to_date,
                "type": "all",
            },
        )

        items = data if isinstance(data, list) else data.get("data", [])
        logger.info(f"InsiderTradingFetcher: fetched {len(items)} insider trades")
        return items

    def _parse_item(self, item: dict) -> tuple[Optional[str], Optional[datetime], dict]:
        ticker = (item.get("symbol") or item.get("Symbol") or "").strip().upper()
        if not ticker:
            return None, None, {}

        # Only process buy transactions (sells are less informative)
        transaction_type = (item.get("transactionType", item.get("acquisition_mode", "")) or "").upper()
        if "SELL" in transaction_type:
            return None, None, {}

        # Category filter
        category = item.get("personCategory", item.get("category", "")).strip()
        if category and not any(cat in category for cat in SIGNAL_CATEGORIES):
            return None, None, {}

        # Value filter (skip trivial trades under ₹5L = 0.05 Cr)
        try:
            qty = float(item.get("noOfSharesAcquired", item.get("secAcq", 0)) or 0)
            price = float(item.get("acquiredPrice", item.get("secVal", 0)) or 0)
            if price == 0:
                value_cr = 0.0
            else:
                value_cr = (qty * price) / 1e7
        except (ValueError, TypeError):
            qty, price, value_cr = 0.0, 0.0, 0.0

        if value_cr < 0.05:
            return None, None, {}

        date_str = item.get("date", item.get("acqfrmDt", ""))
        try:
            event_date = datetime.strptime(date_str, "%d-%b-%Y")
        except (ValueError, TypeError):
            event_date = datetime.utcnow()

        person_name = item.get("personName", item.get("acqName", "")).strip()

        # Determine if this is a senior executive (higher conviction)
        is_senior = any(
            role in category.upper()
            for role in ["MANAGING DIRECTOR", "CEO", "CHAIRMAN", "CFO"]
        )

        canonical = {
            "ticker": ticker,
            "company": item.get("company", item.get("companyName", "")),
            "person_name": person_name,
            "person_category": category,
            "transaction_type": transaction_type,
            "quantity": qty,
            "price": price,
            "value_cr": round(value_cr, 2),
            "date": date_str,
            "is_senior_executive": is_senior,
            "exchange": "NSE",
            # Pre-compute conviction multiplier
            "conviction_weight": 1.5 if is_senior else (1.2 if "PROMOTER" in category.upper() else 1.0),
        }

        return ticker, event_date, canonical

    async def run(self) -> Dict:
        """Execute the insider trading fetch cycle."""
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
                await self._record_run(db, "insider", events_fetched, events_new, 0)

                return {
                    "events_fetched": events_fetched,
                    "events_new": events_new,
                    "signals_generated": 0,
                    "error": None,
                }

            except Exception as e:
                logger.exception(f"InsiderTradingFetcher error: {e}")
                await self._record_run(db, "insider", 0, 0, 0, str(e))
                return {
                    "events_fetched": 0,
                    "events_new": 0,
                    "signals_generated": 0,
                    "error": str(e),
                }