"""
Signal Generator — the output stage of the pipeline.

Takes a RawEvent, runs it through NLP + scoring, and creates a Signal
with its EvidenceItems and AnalysisPoints.

Also broadcasts new signals over WebSocket to connected frontend clients.
"""
import logging
from datetime import datetime
from typing import Optional

from sqlalchemy.ext.asyncio import AsyncSession

from models import Signal, EvidenceItem, AnalysisPoint, RawEvent
from nlp import score_event
from scorer import SignalScorer
from settings import settings

logger = logging.getLogger(__name__)

# Import WS broadcaster lazily to avoid circular imports
_broadcaster = None


def set_broadcaster(broadcaster):
    global _broadcaster
    _broadcaster = broadcaster


class SignalGenerator:

    def __init__(self, session_factory):
        self.session_factory = session_factory
        self.scorer = SignalScorer()

    async def process_event(self, event: RawEvent) -> int:
        """
        Process a single RawEvent → Signal.
        Returns 1 if a signal was generated, 0 otherwise.
        """
        async with self.session_factory() as db:
            try:
                # 1. NLP scoring via Claude API
                nlp = await score_event(event.source, event.ticker, event.raw_json)

                # 2. Dimensional scoring
                scores = await self.scorer.score(
                    db, event.source, event.ticker, event.raw_json, nlp
                )

                # 3. Cluster bonus
                cluster_bonus = await self.scorer.compute_cluster_bonus(
                    db, event.ticker, event.source
                )
                composite = min(scores["composite_score"] + cluster_bonus, 100.0)
                scores["composite_score"] = composite

                # 4. Filter — only emit signals above minimum threshold
                if composite < settings.signal_min_score:
                    logger.debug(
                        f"Signal for {event.ticker} below threshold "
                        f"({composite:.1f} < {settings.signal_min_score}) — skipped"
                    )
                    event.processed = True
                    await db.commit()
                    return 0

                # 5. Build Signal object
                signal = Signal(
                    ticker=event.ticker,
                    company_name=event.raw_json.get("company", ""),
                    signal_type=nlp.signal_type_override or event.source,
                    priority=scores["priority"],
                    title=nlp.headline,
                    headline=nlp.headline,
                    summary=nlp.summary,
                    generated_at=datetime.utcnow(),
                    composite_score=scores["composite_score"],
                    score_volume=scores["score_volume"],
                    score_insider=scores["score_insider"],
                    score_nlp=scores["score_nlp"],
                    score_pattern=scores["score_pattern"],
                    sentiment_label=nlp.sentiment_label,
                    sentiment_score=nlp.sentiment_score,
                    nlp_anomaly_sigma=nlp.nlp_anomaly_sigma,
                )
                db.add(signal)
                await db.flush()  # get signal.id

                # 6. Build evidence trail
                evidence = self._build_evidence(event, signal.id)
                db.add_all(evidence)

                # 7. Build analysis points
                for ap in nlp.analysis_points:
                    db.add(AnalysisPoint(
                        signal_id=signal.id,
                        label=ap.get("label", ""),
                        value=ap.get("value", ""),
                        sentiment=ap.get("sentiment", "neutral"),
                    ))

                event.processed = True
                await db.commit()

                # 8. Broadcast to WebSocket subscribers
                if _broadcaster:
                    await _broadcaster.broadcast(signal_to_dict(signal, evidence, nlp.analysis_points))

                logger.info(
                    f"Signal generated: {event.ticker} [{event.source}] "
                    f"score={composite:.1f} priority={scores['priority']}"
                )
                return 1

            except Exception as e:
                logger.exception(f"Signal generation failed for {event.ticker}: {e}")
                await db.rollback()
                return 0

    def _build_evidence(self, event: RawEvent, signal_id: int) -> list[EvidenceItem]:
        """Build evidence items from the raw event data."""
        data = event.raw_json
        items = []
        source = event.source
        timestamp = datetime.utcnow().strftime("%I:%M %p today")

        if source == "bulk":
            kind = data.get("deal_kind", "bulk").capitalize()
            qty = data.get("quantity", 0)
            price = data.get("price", 0)
            value_cr = data.get("value_cr", 0)
            client = data.get("client_name", "Unknown")
            buy_sell = data.get("buy_sell", "")
            items.append(EvidenceItem(
                signal_id=signal_id,
                raw_event_id=event.id,
                ev_type="bulk",
                icon_label="B",
                title=f"{kind} deal: {qty:,.0f} shares @ ₹{price:,.2f} — {client} ({buy_sell})",
                meta=f"NSE {kind} deal disclosure · ₹{value_cr:.2f} Cr · {timestamp}",
            ))

        elif source == "insider":
            person = data.get("person_name", "Insider")
            category = data.get("person_category", "")
            qty = data.get("quantity", 0)
            price = data.get("price", 0)
            value_cr = data.get("value_cr", 0)
            items.append(EvidenceItem(
                signal_id=signal_id,
                raw_event_id=event.id,
                ev_type="insider",
                icon_label="I",
                title=f"{person} ({category}): {qty:,.0f} shares @ ₹{price:,.2f} (₹{value_cr:.2f} Cr)",
                meta=f"SEBI insider disclosure · {data.get('date', timestamp)}",
            ))

        elif source == "filings":
            filing_type = data.get("filing_type", "Filing")
            description = data.get("description", "")[:120]
            items.append(EvidenceItem(
                signal_id=signal_id,
                raw_event_id=event.id,
                ev_type="filing",
                icon_label="F",
                title=f"{filing_type}: {description}",
                meta=f"NSE corporate filing · {data.get('date', timestamp)}",
            ))

        return items


def signal_to_dict(signal: Signal, evidence: list, analysis_points: list) -> dict:
    """Serialize a Signal for WebSocket broadcast / API response."""
    return {
        "id": signal.id,
        "ticker": signal.ticker,
        "company_name": signal.company_name,
        "signal_type": signal.signal_type,
        "priority": signal.priority,
        "title": signal.title,
        "headline": signal.headline,
        "summary": signal.summary,
        "generated_at": signal.generated_at.isoformat() if signal.generated_at else None,
        "composite_score": signal.composite_score,
        "score_volume": signal.score_volume,
        "score_insider": signal.score_insider,
        "score_nlp": signal.score_nlp,
        "score_pattern": signal.score_pattern,
        "sentiment_label": signal.sentiment_label,
        "sentiment_score": signal.sentiment_score,
        "nlp_anomaly_sigma": signal.nlp_anomaly_sigma,
        "evidence": [
            {
                "ev_type": e.ev_type if hasattr(e, "ev_type") else e.get("ev_type"),
                "icon_label": e.icon_label if hasattr(e, "icon_label") else e.get("icon_label"),
                "title": e.title if hasattr(e, "title") else e.get("title"),
                "meta": e.meta if hasattr(e, "meta") else e.get("meta"),
            }
            for e in evidence
        ],
        "analysis_points": [
            ap if isinstance(ap, dict) else {
                "label": ap.label,
                "value": ap.value,
                "sentiment": ap.sentiment,
            }
            for ap in analysis_points
        ],
    }