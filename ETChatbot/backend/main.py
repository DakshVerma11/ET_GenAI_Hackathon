from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from backend.api.routes import build_router
from backend.config import settings
from backend.rag.orchestrator import Orchestrator
from backend.services.market_store import MarketStore


store = MarketStore(settings.data_path)
orchestrator = Orchestrator(store)

app = FastAPI(title="Market ChatGPT - Next Gen", version="1.0.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(build_router(orchestrator))

# Mount the static frontend directory
import os
frontend_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "frontend")
app.mount("/", StaticFiles(directory=frontend_path, html=True), name="frontend")
