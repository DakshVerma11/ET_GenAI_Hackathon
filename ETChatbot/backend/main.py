from __future__ import annotations

from ETChatbot.backend.api.routes import build_router
from ETChatbot.backend.config import settings
from ETChatbot.backend.rag.orchestrator import Orchestrator
from ETChatbot.backend.services.market_store import MarketStore


store = MarketStore(settings.data_path)
orchestrator = Orchestrator(store)

router = build_router(orchestrator)
