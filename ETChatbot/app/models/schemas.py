from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class Holding(BaseModel):
    symbol: str = Field(..., description="Ticker symbol")
    weight: float = Field(..., ge=0, le=100, description="Portfolio allocation in percent")
    quantity: int | None = Field(default=None, ge=0)


class Citation(BaseModel):
    id: str
    title: str
    source: str
    date: str


class IntentResult(BaseModel):
    intent: str
    entities: list[str]
    requires_portfolio: bool
    needs_expansion: bool


class ChatRequest(BaseModel):
    user_id: str = Field(default="demo-user")
    query: str
    portfolio: list[Holding] | None = None


class ChatResponse(BaseModel):
    verdict: str
    supporting_analysis: list[str]
    portfolio_impact: str
    citations: list[Citation]
    metadata: dict[str, Any] = Field(default_factory=dict)
    generated_at: datetime = Field(default_factory=datetime.utcnow)


class PortfolioUploadRequest(BaseModel):
    user_id: str
    holdings: list[Holding]


class PortfolioUploadResponse(BaseModel):
    user_id: str
    total_weight: float
    symbols: list[str]
    message: str
