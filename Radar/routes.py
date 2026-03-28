"""
REST API routes for Opportunity Radar.

All responses are JSON. Pagination uses cursor-based (offset/limit).
"""
from datetime import datetime, timedelta
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, desc

from models import Signal, EvidenceItem, AnalysisPoint, SectorStats, AlertConfig, RawEvent, PipelineRun
from deps import get_db

router = APIRouter()


class AlertToggleRequest(BaseModel):
    enabled: bool


# ── Signals ────────────────────────────────────────────────────────────────────

@router.get("/signals")
async def list_signals(
    limit: int = Query(default=50, le=200),
    offset: int = Query(default=0),
    priority: Optional[str] = Query(default=None),
    signal_type: Optional[str] = Query(default=None),
    since_hours: int = Query(default=24),
    db: AsyncSession = Depends(get_db),
):
    """
    List recent signals, newest first.
    Filter by priority (high|med|low), signal_type, or time window.
    """
    since = datetime.utcnow() - timedelta(hours=since_hours)
    q = select(Signal).where(Signal.generated_at >= since).order_by(desc(Signal.generated_at))

    if priority:
        q = q.where(Signal.priority == priority)
    if signal_type:
        q = q.where(Signal.signal_type == signal_type)

    q = q.offset(offset).limit(limit)
    result = await db.execute(q)
    signals = result.scalars().all()

    return {
        "signals": [_serialize_signal(s) for s in signals],
        "count": len(signals),
        "offset": offset,
        "limit": limit,
    }


@router.get("/signals/{signal_id}")
async def get_signal(signal_id: int, db: AsyncSession = Depends(get_db)):
    """Full signal detail — includes evidence trail and analysis points."""
    signal = await db.get(Signal, signal_id)
    if not signal:
        raise HTTPException(status_code=404, detail="Signal not found")

    evidence_result = await db.execute(
        select(EvidenceItem).where(EvidenceItem.signal_id == signal_id)
    )
    evidence = evidence_result.scalars().all()

    analysis_result = await db.execute(
        select(AnalysisPoint).where(AnalysisPoint.signal_id == signal_id)
    )
    analysis = analysis_result.scalars().all()

    return {
        **_serialize_signal(signal),
        "evidence": [_serialize_evidence(e) for e in evidence],
        "analysis_points": [_serialize_analysis(a) for a in analysis],
    }


@router.get("/signals/ticker/{ticker}")
async def signals_for_ticker(
    ticker: str,
    limit: int = Query(default=20, le=100),
    db: AsyncSession = Depends(get_db),
):
    """All signals for a specific stock ticker."""
    result = await db.execute(
        select(Signal)
        .where(Signal.ticker == ticker.upper())
        .order_by(desc(Signal.generated_at))
        .limit(limit)
    )
    signals = result.scalars().all()
    return {"ticker": ticker.upper(), "signals": [_serialize_signal(s) for s in signals]}


@router.get("/sectors/heatmap")
async def sector_heatmap(db: AsyncSession = Depends(get_db)):
    """
    Sector-level signal density for the heatmap panel.
    Returns signal breakdown by type in last 24 hours.
    """
    since_24h = datetime.utcnow() - timedelta(hours=24)

    # Signal counts by type
    signal_count_result = await db.execute(
        select(Signal.signal_type, func.count(Signal.id).label("count"))
        .where(Signal.generated_at >= since_24h)
        .group_by(Signal.signal_type)
    )
    type_counts = {row[0]: row[1] for row in signal_count_result.all()}

    # High priority counts
    high_priority_result = await db.execute(
        select(func.count(Signal.id))
        .where(Signal.generated_at >= since_24h)
        .where(Signal.priority == "high")
    )
    high_priority = high_priority_result.scalar() or 0

    return {
        "sectors": type_counts,
        "high_priority_24h": high_priority,
        "updated_at": datetime.utcnow().isoformat(),
    }


@router.get("/stats")
async def pipeline_stats(db: AsyncSession = Depends(get_db)):
    """Pipeline health — signal counts, last run times, error rate."""
    since_24h = datetime.utcnow() - timedelta(hours=24)

    total_signals = await db.execute(
        select(func.count(Signal.id)).where(Signal.generated_at >= since_24h)
    )
    high_priority = await db.execute(
        select(func.count(Signal.id))
        .where(Signal.generated_at >= since_24h)
        .where(Signal.priority == "high")
    )
    last_runs = await db.execute(
        select(PipelineRun).order_by(desc(PipelineRun.started_at)).limit(10)
    )

    runs = last_runs.scalars().all()
    errors = sum(1 for r in runs if not r.success)

    return {
        "signals_24h": total_signals.scalar() or 0,
        "high_priority_24h": high_priority.scalar() or 0,
        "pipeline_error_rate": f"{errors}/{len(runs)} recent runs" if runs else "0 runs",
        "last_runs": [
            {
                "fetcher": r.fetcher,
                "started_at": r.started_at.isoformat() if r.started_at else None,
                "events_fetched": r.events_fetched,
                "events_new": r.events_new,
                "signals_generated": r.signals_generated,
                "success": r.success,
                "error": r.error,
            }
            for r in runs
        ],
    }


# ── Alert Config ───────────────────────────────────────────────────────────────

@router.get("/alerts")
async def list_alerts(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(AlertConfig))
    alerts = result.scalars().all()
    return {"alerts": [{"id": a.id, "name": a.name, "trigger_type": a.trigger_type,
                        "threshold_value": a.threshold_value, "enabled": a.enabled} for a in alerts]}


@router.patch("/alerts/{alert_id}")
async def toggle_alert(alert_id: int, payload: AlertToggleRequest, db: AsyncSession = Depends(get_db)):
    alert = await db.get(AlertConfig, alert_id)
    if not alert:
        raise HTTPException(status_code=404, detail="Alert not found")
    alert.enabled = payload.enabled
    await db.commit()
    return {"id": alert_id, "enabled": payload.enabled}


# ── Serializers ────────────────────────────────────────────────────────────────

def _serialize_signal(s: Signal) -> dict:
    return {
        "id": s.id,
        "ticker": s.ticker,
        "company_name": s.company_name,
        "signal_type": s.signal_type,
        "priority": s.priority,
        "title": s.title,
        "headline": s.headline,
        "summary": s.summary,
        "generated_at": s.generated_at.isoformat() if s.generated_at else None,
        "composite_score": s.composite_score,
        "score_volume": s.score_volume,
        "score_insider": s.score_insider,
        "score_nlp": s.score_nlp,
        "score_pattern": s.score_pattern,
        "sentiment_label": s.sentiment_label,
        "sentiment_score": s.sentiment_score,
        "nlp_anomaly_sigma": s.nlp_anomaly_sigma,
    }


def _serialize_evidence(e: EvidenceItem) -> dict:
    return {
        "ev_type": e.ev_type,
        "icon_label": e.icon_label,
        "title": e.title,
        "meta": e.meta,
    }


def _serialize_analysis(a: AnalysisPoint) -> dict:
    return {"label": a.label, "value": a.value, "sentiment": a.sentiment}