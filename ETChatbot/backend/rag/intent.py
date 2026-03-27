from __future__ import annotations


def classify_intent(query: str) -> str:
    q = query.lower()
    if any(k in q for k in ["compare", "vs", "versus"]):
        return "comparison"
    if any(k in q for k in ["risk", "risky", "downside", "drawdown"]):
        return "portfolio_risk" if any(k in q for k in ["my", "portfolio", "holdings"]) else "risk_lookup"
    if any(k in q for k in ["concall", "transcript"]):
        return "concall_query"
    return "general_query"


def extract_entities(query: str, symbols: list[str]) -> list[str]:
    q = query.upper()
    return [s for s in symbols if s in q]
