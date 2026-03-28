"""
Signal Scorer — 4-dimensional composite scoring model.

Dimensions:
  1. Volume Score   (0–100)  — unusual volume vs historical average
  2. Insider Score  (0–100)  — insider/promoter activity weight
  3. NLP Score      (0–100)  — from Claude API sentiment analysis
  4. Pattern Score  (0–100)  — cross-signal correlation

Composite = 0.25*vol + 0.30*insider + 0.30*nlp + 0.15*pattern

Priority bands:
  ≥ 75  → high
  ≥ 50  → med
  < 50  → low
"""
import logging
from datetime import datetime, timedelta
from typing import Optional

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func

from models import RawEvent, Signal
from nlp import NLPResult
from settings import settings

logger = logging.getLogger(__name__)


class SignalScorer:

    WEIGHTS = {
        "volume": 0.25,
        "insider": 0.30,
        "nlp": 0.30,
        "pattern": 0.15,
    }

    async def score(
        self,
        db: AsyncSession,
        source: str,
        ticker: str,
        raw_data: dict,
        nlp: NLPResult,
    ) -> dict:
        """
        Compute all 4 dimension scores and the composite.
        Returns a dict with all scores + priority + metadata.
        """
        vol_score = await self._volume_score(db, ticker, raw_data)
        insider_score = self._insider_score(source, raw_data, nlp)
        nlp_score = self._nlp_score(nlp)
        pattern_score = await self._pattern_score(db, ticker, source)

        composite = (
            vol_score * self.WEIGHTS["volume"]
            + insider_score * self.WEIGHTS["insider"]
            + nlp_score * self.WEIGHTS["nlp"]
            + pattern_score * self.WEIGHTS["pattern"]
        )
        composite = round(min(max(composite, 0), 100), 1)

        priority = "high" if composite >= 75 else ("med" if composite >= 50 else "low")

        return {
            "composite_score": composite,
            "score_volume": round(vol_score, 1),
            "score_insider": round(insider_score, 1),
            "score_nlp": round(nlp_score, 1),
            "score_pattern": round(pattern_score, 1),
            "priority": priority,
        }

    async def _volume_score(self, db: AsyncSession, ticker: str, raw_data: dict) -> float:
        """
        Score based on volume z-score.
        Falls back to moderate score if no quote data available.
        """
        # Try to get volume z-score from raw_data (enriched by fetcher)
        zscore = raw_data.get("volume_zscore")
        if zscore is not None:
            return self._zscore_to_score(float(zscore))

        # Check if we have value_cr in the data (bulk/insider trades)
        value_cr = raw_data.get("value_cr", 0)
        if value_cr > 0:
            # Larger trades = higher volume signal
            if value_cr >= 100:
                return 90.0
            elif value_cr >= 50:
                return 75.0
            elif value_cr >= 10:
                return 60.0
            elif value_cr >= 1:
                return 45.0

        return 40.0  # neutral fallback

    def _zscore_to_score(self, zscore: float) -> float:
        """Convert volume z-score to 0–100 score."""
        if zscore >= 3.0:
            return 95.0
        elif zscore >= 2.5:
            return 85.0
        elif zscore >= 2.0:
            return 75.0
        elif zscore >= 1.5:
            return 60.0
        elif zscore >= 1.0:
            return 50.0
        elif zscore >= 0:
            return 40.0
        else:
            return 25.0

    def _insider_score(self, source: str, raw_data: dict, nlp: NLPResult) -> float:
        """
        Score based on insider activity characteristics.
        Only applicable for insider/bulk sources; others get a neutral baseline.
        """
        if source == "insider":
            base = 50.0
            value_cr = raw_data.get("value_cr", 0)
            conviction_weight = raw_data.get("conviction_weight", 1.0)

            # Value scaling
            if value_cr >= 10:
                base = 85.0
            elif value_cr >= 5:
                base = 75.0
            elif value_cr >= 1:
                base = 65.0
            elif value_cr >= 0.5:
                base = 55.0

            return min(base * conviction_weight, 100.0)

        elif source == "bulk":
            value_cr = raw_data.get("value_cr", 0)
            is_promoter = raw_data.get("looks_like_promoter", False)
            buy_sell = raw_data.get("buy_sell", "")
            is_buy = "BUY" in buy_sell.upper()

            if not is_buy:
                return 25.0  # sell-side bulk is a negative signal

            base = 50.0
            if value_cr >= 100:
                base = 80.0
            elif value_cr >= 50:
                base = 70.0
            elif value_cr >= 10:
                base = 60.0

            if is_promoter:
                base = min(base * 1.2, 95.0)

            return base

        return 40.0  # neutral for non-insider sources

    def _nlp_score(self, nlp: NLPResult) -> float:
        """
        Convert NLP sentiment score + anomaly sigma to a combined NLP score.
        Anomaly sigma boosts the score — unusual language is often a signal.
        """
        base = nlp.sentiment_score

        # Anomaly boost: unusual NLP patterns are valuable regardless of direction
        sigma_boost = min(nlp.nlp_anomaly_sigma * 8, 20)
        return min(base + sigma_boost, 100.0)

    async def _pattern_score(self, db: AsyncSession, ticker: str, current_source: str) -> float:
        """
        Cross-signal correlation score.
        Higher score if multiple different data streams have fired for the same
        ticker in the last 7 days — convergence of signals = high conviction.
        """
        since = datetime.utcnow() - timedelta(days=7)
        result = await db.execute(
            select(func.count(func.distinct(RawEvent.source)))
            .where(RawEvent.ticker == ticker)
            .where(RawEvent.fetched_at >= since)
        )
        distinct_sources = result.scalar() or 0

        # Current source counts even if it's not in DB yet
        distinct_sources = max(distinct_sources, 1)

        if distinct_sources >= 4:
            return 90.0
        elif distinct_sources == 3:
            return 75.0
        elif distinct_sources == 2:
            return 60.0
        else:
            return 35.0

    async def compute_cluster_bonus(self, db: AsyncSession, ticker: str, source: str) -> float:
        """
        Detect cluster patterns — e.g. multiple insiders buying same week.
        Returns a bonus (0–20) to add on top of the composite score.
        """
        if source != "insider":
            return 0.0

        since = datetime.utcnow() - timedelta(days=7)
        result = await db.execute(
            select(func.count(RawEvent.id))
            .where(RawEvent.ticker == ticker)
            .where(RawEvent.source == "insider")
            .where(RawEvent.fetched_at >= since)
        )
        count = result.scalar() or 0

        if count >= 4:
            return 20.0  # Rare cluster — high bonus
        elif count >= 3:
            return 15.0
        elif count >= 2:
            return 8.0
        return 0.0