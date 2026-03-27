from __future__ import annotations

from langchain_core.prompts import PromptTemplate

from backend.agents import fundamentals, portfolio_risk, sentiment, technicals
from backend.models.schemas import ChatResponse, Holding
from backend.rag.hf_client import hf_service
from backend.rag.hybrid_retriever import HybridRetriever
from backend.rag.intent import classify_intent, extract_entities
from backend.rag.query_expansion import expand_query
from backend.services.market_store import MarketStore
from backend.services.stock_data import get_weekly_stock_data


PROMPT_TMPL = PromptTemplate.from_template(
    """
You are a financial analyst.

User Question:
{query}

Portfolio:
{portfolio_data}

Live Market Data (Past Week Closes):
{live_data}

Agent Insights:
{agent_outputs}

Retrieved Evidence:
{documents}

Generate:
1. Verdict
2. Key Insights
3. Portfolio Impact
4. Sources (with references)
""".strip()
)

class Orchestrator:
    def __init__(self, store: MarketStore) -> None:
        self.store = store
        self.retriever = HybridRetriever(store.documents)

    def run(self, query: str, holdings: list[Holding]) -> ChatResponse:
        intent = classify_intent(query)
        expanded = expand_query(query, intent)
        entities = extract_entities(query, self.store.symbols)
        if not entities and holdings and "portfolio" in query.lower():
            entities = [h.symbol for h in holdings]

        retrieved = self.retriever.retrieve(expanded, top_k=8)

        f_out = fundamentals.run(entities, self.store.fundamentals)
        t_out = technicals.run(entities, self.store.technicals)
        s_out = sentiment.run(entities, retrieved)
        p_out = portfolio_risk.run(holdings, self.store.fundamentals)

        agent_outputs = {
            "fundamentals": f_out,
            "technicals": t_out,
            "sentiment": s_out,
            "portfolio_risk": p_out,
        }

        evidence_text = "\n".join(
            [
                f"[{idx + 1}] {d['metadata']['title']} ({d['metadata']['source']}, {d['metadata']['date']}): {d['text']}"
                for idx, d in enumerate(retrieved[:6])
            ]
        )
        prompt = PROMPT_TMPL.format(
            query=query,
            portfolio_data=[h.model_dump() for h in holdings] if holdings else "No portfolio provided",
            live_data=get_weekly_stock_data(entities),
            agent_outputs=agent_outputs,
            documents=evidence_text,
        )
        generated = hf_service.generate(prompt)

        key_insights = []
        for symbol in entities:
            f = f_out.get(symbol)
            t = t_out.get(symbol)
            s = s_out.get(symbol)
            if f:
                key_insights.append(
                    f"{symbol}: PE {f['pe']}, ROE {f['roe']}%, growth {f['growth']}%, debt {f['debt']}."
                )
            if t:
                key_insights.append(
                    f"{symbol}: trend {t['trend']}, RSI {t['rsi']}, support {t['support']}, resistance {t['resistance']}."
                )
            if s:
                key_insights.append(f"{symbol}: sentiment {s['label']} ({s['confidence']}).")

        risk_scores: dict[str, float] = {}
        for symbol in entities:
            score = 0.0
            f = f_out.get(symbol, {})
            t = t_out.get(symbol, {})
            s = s_out.get(symbol, {})
            if f.get("debt", 0) > 1.0:
                score += 0.4
            if t.get("trend") in ["downtrend", "range_weak"]:
                score += 0.3
            if s.get("label") == "negative":
                score += 0.3
            risk_scores[symbol] = score

        if risk_scores:
            verdict_symbol = max(risk_scores, key=risk_scores.get)
            verdict = f"Most risky stock currently appears to be {verdict_symbol}."
        elif entities:
            verdict = f"No specific risk flagged for {entities[0]}."
        else:
            verdict = "General query. No specific stock risks flagged."

        if p_out.get("has_portfolio"):
            te = p_out["top_exposure"]
            portfolio_impact = (
                f"Concentration risk is {p_out['concentration_risk']}. "
                f"Top exposure: {te['symbol']} at {te['allocation']}%."
            )
        else:
            portfolio_impact = "Portfolio data missing. Risk analysis is not personalized."

        citations = [
            {
                "doc_id": d["metadata"]["doc_id"],
                "title": d["metadata"]["title"],
                "source": d["metadata"]["source"],
                "stock": d["metadata"]["stock"],
                "date": d["metadata"]["date"],
            }
            for d in retrieved[:4]
        ]

        return ChatResponse(
            verdict=verdict,
            key_insights=key_insights,
            portfolio_impact=portfolio_impact,
            answer=generated,
            citations=citations,
            debug={
                "intent": intent,
                "entities": entities,
                "expanded_queries": expanded,
                "retrieved_count": len(retrieved),
            },
        )
