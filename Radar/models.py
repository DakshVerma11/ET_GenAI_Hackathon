"""
Database models for Opportunity Radar.
All tables are append-only — signals and evidence are never mutated after insert.
"""
from datetime import datetime
from sqlalchemy import (
    Column, Integer, String, Float, Text, DateTime,
    Boolean, ForeignKey, Index, JSON,
)
from sqlalchemy.orm import DeclarativeBase, relationship


class Base(DeclarativeBase):
    pass


class RawEvent(Base):
    """
    Raw event fetched from any NSE data source, before NLP/scoring.
    Stored verbatim so we can re-process if the scoring model changes.
    """
    __tablename__ = "raw_events"

    id = Column(Integer, primary_key=True, autoincrement=True)
    source = Column(String(32), nullable=False)       # filings | bulk | insider | result
    ticker = Column(String(20), nullable=False)
    event_date = Column(DateTime, nullable=False)
    fetched_at = Column(DateTime, default=datetime.utcnow)
    raw_json = Column(JSON, nullable=False)
    content_hash = Column(String(64), unique=True)    # SHA256 — dedup key
    processed = Column(Boolean, default=False)

    __table_args__ = (
        Index("ix_raw_ticker_source", "ticker", "source"),
        Index("ix_raw_processed", "processed"),
    )


class Signal(Base):
    """
    A scored, actionable signal derived from one or more RawEvents.
    The core output of the pipeline.
    """
    __tablename__ = "signals"

    id = Column(Integer, primary_key=True, autoincrement=True)
    ticker = Column(String(20), nullable=False)
    company_name = Column(String(128))
    signal_type = Column(String(32), nullable=False)  # filing | bulk | insider | result | nlp
    priority = Column(String(8), nullable=False)      # high | med | low
    title = Column(String(256), nullable=False)
    headline = Column(String(512))
    summary = Column(Text)
    generated_at = Column(DateTime, default=datetime.utcnow)

    # Composite score (0–100)
    composite_score = Column(Float, nullable=False)

    # Dimensional scores
    score_volume = Column(Float, default=0.0)
    score_insider = Column(Float, default=0.0)
    score_nlp = Column(Float, default=0.0)
    score_pattern = Column(Float, default=0.0)

    # NLP outputs
    sentiment_label = Column(String(64))
    sentiment_score = Column(Float)           # 0–100
    nlp_anomaly_sigma = Column(Float)         # how many σ from sector mean

    # Market context
    price_at_signal = Column(Float)
    volume_zscore = Column(Float)

    # Status
    alerted = Column(Boolean, default=False)

    evidence = relationship("EvidenceItem", back_populates="signal", cascade="all, delete-orphan")
    analysis_points = relationship("AnalysisPoint", back_populates="signal", cascade="all, delete-orphan")

    __table_args__ = (
        Index("ix_signal_ticker", "ticker"),
        Index("ix_signal_type", "signal_type"),
        Index("ix_signal_priority", "priority"),
        Index("ix_signal_generated", "generated_at"),
    )


class EvidenceItem(Base):
    """
    Individual piece of evidence supporting a Signal.
    Multiple evidence items build the evidence trail shown in the UI.
    """
    __tablename__ = "evidence_items"

    id = Column(Integer, primary_key=True, autoincrement=True)
    signal_id = Column(Integer, ForeignKey("signals.id"), nullable=False)
    raw_event_id = Column(Integer, ForeignKey("raw_events.id"), nullable=True)

    ev_type = Column(String(32))       # filing | insider | bulk | nlp
    icon_label = Column(String(4))     # short label shown in UI (F, I, B, N, R)
    title = Column(String(512))
    meta = Column(String(256))         # source description + timestamp

    signal = relationship("Signal", back_populates="evidence")

    __table_args__ = (
        Index("ix_evidence_signal", "signal_id"),
    )


class AnalysisPoint(Base):
    """
    Key/value analysis facts shown in the signal detail grid.
    """
    __tablename__ = "analysis_points"

    id = Column(Integer, primary_key=True, autoincrement=True)
    signal_id = Column(Integer, ForeignKey("signals.id"), nullable=False)
    label = Column(String(128))
    value = Column(String(256))
    sentiment = Column(String(16))     # positive | negative | neutral

    signal = relationship("Signal", back_populates="analysis_points")


class SectorStats(Base):
    """
    Aggregated sector-level signal density, updated every fetch cycle.
    Used for the heatmap panel.
    """
    __tablename__ = "sector_stats"

    id = Column(Integer, primary_key=True, autoincrement=True)
    sector = Column(String(64), nullable=False)
    signal_count_24h = Column(Integer, default=0)
    high_priority_count = Column(Integer, default=0)
    avg_score = Column(Float, default=0.0)
    bulk_flow_cr = Column(Float, default=0.0)   # net crores
    updated_at = Column(DateTime, default=datetime.utcnow)

    __table_args__ = (Index("ix_sector_name", "sector"),)


class AlertConfig(Base):
    """
    User-configured alert triggers.
    """
    __tablename__ = "alert_configs"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(128), nullable=False)
    trigger_type = Column(String(32))            # insider | bulk | nlp | result
    threshold_value = Column(Float)
    enabled = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)


class PipelineRun(Base):
    """
    Audit log of every fetch cycle — used for monitoring and debugging.
    """
    __tablename__ = "pipeline_runs"

    id = Column(Integer, primary_key=True, autoincrement=True)
    fetcher = Column(String(32))
    started_at = Column(DateTime, default=datetime.utcnow)
    finished_at = Column(DateTime)
    events_fetched = Column(Integer, default=0)
    events_new = Column(Integer, default=0)
    signals_generated = Column(Integer, default=0)
    error = Column(Text)
    success = Column(Boolean, default=True)