from __future__ import annotations

from app.core.agents import fundamentals_agent, portfolio_agent, sentiment_agent, technicals_agent
from app.core.intent import classify_intent
from app.core.query_expansion import expand_query
from app.core.retrieval import HybridRetriever
from app.core.synthesizer import synthesize
from app.models.schemas import ChatRequest, ChatResponse, Holding
from app.services.data_store import DataStore


class IntelligenceEngine:
    def __init__(self, store: DataStore) -> None:
        self.store = store
        self.retriever = HybridRetriever(store.documents)
        self.portfolio_sessions: dict[str, list[Holding]] = {}

    def upsert_portfolio(self, user_id: str, holdings: list[Holding]) -> None:
        self.portfolio_sessions[user_id] = holdings

    def _resolve_entities(self, request: ChatRequest, intent_entities: list[str], holdings: list[Holding]) -> list[str]:
        symbols = set(intent_entities)
        if request.portfolio:
            symbols.update([h.symbol for h in request.portfolio])
        if holdings:
            symbols.update([h.symbol for h in holdings])
        return list(symbols)

    def run(self, request: ChatRequest) -> ChatResponse:
        intent = classify_intent(request.query, self.store.symbol_universe)
        expansions = expand_query(request.query, intent) if intent.needs_expansion else [request.query]

        retrieved = self.retriever.retrieve(expansions, top_k=8)
        retrieved_docs = [item.doc for item in retrieved]

        session_holdings = self.portfolio_sessions.get(request.user_id, [])
        active_holdings = request.portfolio if request.portfolio is not None else session_holdings

        entities = self._resolve_entities(request, intent.entities, active_holdings)
        if not entities and self.store.symbol_universe:
            entities = self.store.symbol_universe[:2]

        fundamentals_out = fundamentals_agent(entities, self.store.fundamentals)

        try:
            technicals_out = technicals_agent(entities, self.store.technicals)
        except Exception:
            technicals_out = {}

        try:
            sentiment_out = sentiment_agent(entities, retrieved_docs)
        except Exception:
            sentiment_out = {}

        portfolio_out = portfolio_agent(active_holdings, self.store.fundamentals)

        composed = synthesize(
            query=request.query,
            intent=intent.intent,
            entities=entities,
            fundamentals_out=fundamentals_out,
            technicals_out=technicals_out,
            sentiment_out=sentiment_out,
            portfolio_out=portfolio_out,
            retrieved_docs=retrieved_docs,
        )

        return ChatResponse(**composed)
