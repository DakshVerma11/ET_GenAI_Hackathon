from __future__ import annotations

from app.models.schemas import IntentResult


def detect_entities(query: str, symbol_universe: list[str]) -> list[str]:
    q = query.lower()
    hits = []
    for symbol in symbol_universe:
        if symbol.lower() in q:
            hits.append(symbol)
    return sorted(set(hits))


def classify_intent(query: str, symbol_universe: list[str]) -> IntentResult:
    q = query.lower()
    entities = detect_entities(query, symbol_universe)

    if any(token in q for token in ["compare", "vs", "versus"]):
        intent = "comparison"
    elif any(token in q for token in ["risk", "risky", "drawdown", "downside"]):
        intent = "portfolio_risk" if any(x in q for x in ["my", "portfolio", "holdings"]) else "risk_lookup"
    elif any(token in q for token in ["concall", "transcript", "management commentary"]):
        intent = "concall_query"
    else:
        intent = "general_market_query"

    requires_portfolio = intent in {"portfolio_risk"} or any(x in q for x in ["my portfolio", "my holdings"])
    needs_expansion = True

    return IntentResult(
        intent=intent,
        entities=entities,
        requires_portfolio=requires_portfolio,
        needs_expansion=needs_expansion,
    )
