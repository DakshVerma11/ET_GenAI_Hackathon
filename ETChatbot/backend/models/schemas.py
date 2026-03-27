from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class Holding(BaseModel):
    symbol: str
    quantity: float = Field(default=0, ge=0)
    allocation: float = Field(default=0, ge=0, le=100)


class ChatRequest(BaseModel):
    user_id: str = "demo-user"
    query: str


class Citation(BaseModel):
    doc_id: str
    title: str
    source: str
    stock: str
    date: str


class ChatResponse(BaseModel):
    verdict: str
    key_insights: list[str]
    portfolio_impact: str
    answer: str
    citations: list[Citation]
    debug: dict[str, Any] = Field(default_factory=dict)
    generated_at: datetime = Field(default_factory=datetime.utcnow)


class PortfolioResponse(BaseModel):
    user_id: str
    holdings: list[Holding]
    total_allocation: float
    message: str
