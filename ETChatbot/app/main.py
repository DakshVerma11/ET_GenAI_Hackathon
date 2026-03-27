from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from app.core.orchestrator import IntelligenceEngine
from app.models.schemas import (
    ChatRequest,
    ChatResponse,
    PortfolioUploadRequest,
    PortfolioUploadResponse,
)
from app.services.data_store import DataStore


app = FastAPI(title="Market ChatGPT - Next Gen", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

store = DataStore()
engine = IntelligenceEngine(store)

ROOT = Path(__file__).resolve().parent.parent
FRONTEND_DIR = ROOT / "frontend"

if FRONTEND_DIR.exists():
    app.mount("/frontend", StaticFiles(directory=str(FRONTEND_DIR)), name="frontend")


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/portfolio/upload", response_model=PortfolioUploadResponse)
def upload_portfolio(payload: PortfolioUploadRequest) -> PortfolioUploadResponse:
    total_weight = round(sum(h.weight for h in payload.holdings), 2)
    if total_weight <= 0:
        raise HTTPException(status_code=400, detail="Portfolio weights must be positive.")

    engine.upsert_portfolio(payload.user_id, payload.holdings)
    return PortfolioUploadResponse(
        user_id=payload.user_id,
        total_weight=total_weight,
        symbols=[h.symbol for h in payload.holdings],
        message="Portfolio uploaded to in-memory session store.",
    )


@app.post("/chat", response_model=ChatResponse)
def chat(payload: ChatRequest) -> ChatResponse:
    return engine.run(payload)


@app.get("/")
def home() -> FileResponse:
    index = FRONTEND_DIR / "index.html"
    if not index.exists():
        raise HTTPException(status_code=404, detail="Frontend not found")
    return FileResponse(index)
