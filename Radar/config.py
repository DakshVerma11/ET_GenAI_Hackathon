"""
Configuration management for Opportunity Radar.
All settings are loaded from environment variables via Pydantic.
"""
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field
from typing import Optional


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # ── Anthropic / NLP ────────────────────────────────────────────────────────
    anthropic_api_key: str = Field(default="", alias="ANTHROPIC_API_KEY")

    # ── Fetch intervals (seconds) ──────────────────────────────────────────────
    fetch_interval_filings: int = Field(default=300, alias="FETCH_INTERVAL_FILINGS")
    fetch_interval_bulk: int = Field(default=120, alias="FETCH_INTERVAL_BULK")
    fetch_interval_insider: int = Field(default=600, alias="FETCH_INTERVAL_INSIDER")
    fetch_interval_indices: int = Field(default=60, alias="FETCH_INTERVAL_INDICES")

    # ── Signal thresholds ──────────────────────────────────────────────────────
    signal_min_score: float = Field(default=40.0, alias="SIGNAL_MIN_SCORE")
    volume_zscore_threshold: float = Field(default=2.0, alias="VOLUME_ZSCORE_THRESHOLD")
    nlp_anomaly_sigma: float = Field(default=2.0, alias="NLP_ANOMALY_SIGMA")
    insider_min_value_cr: float = Field(default=0.5, alias="INSIDER_MIN_VALUE_CR")
    bulk_deal_min_pct: float = Field(default=0.5, alias="BULK_DEAL_MIN_PCT")

    # ── Server ─────────────────────────────────────────────────────────────────
    host: str = Field(default="0.0.0.0", alias="HOST")
    port: int = Field(default=8000, alias="PORT")
    log_level: str = Field(default="info", alias="LOG_LEVEL")

    # ── Database ───────────────────────────────────────────────────────────────
    database_url: str = Field(
        default="sqlite+aiosqlite:///./signals.db",
        alias="DATABASE_URL",
    )

    # ── NSE Configuration ──────────────────────────────────────────────────────
    nse_user_agent: str = Field(
        default="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        alias="NSE_USER_AGENT",
    )
    nse_base_url: str = "https://www.nseindia.com"
    nse_api_base: str = "https://www.nseindia.com/api"


settings = Settings()
