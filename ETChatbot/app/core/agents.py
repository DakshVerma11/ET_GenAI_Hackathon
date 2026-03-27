from __future__ import annotations

from collections import Counter
from typing import Any

from app.models.schemas import Holding


def fundamentals_agent(entities: list[str], fundamentals: dict[str, dict[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for symbol in entities:
        if symbol in fundamentals:
            f = fundamentals[symbol]
            result[symbol] = {
                "pe": f["pe"],
                "roe": f["roe"],
                "debt_to_equity": f["debt_to_equity"],
                "revenue_growth": f["revenue_growth"],
                "sector": f["sector"],
            }
    return result


def technicals_agent(entities: list[str], technicals: dict[str, dict[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for symbol in entities:
        if symbol in technicals:
            t = technicals[symbol]
            result[symbol] = {
                "trend": t["trend"],
                "rsi": t["rsi"],
                "support": t["support"],
                "resistance": t["resistance"],
                "volatility": t["volatility"],
            }
    return result


def sentiment_agent(entities: list[str], docs: list[dict[str, Any]]) -> dict[str, Any]:
    counts: dict[str, Counter] = {e: Counter() for e in entities}

    for doc in docs:
        for ticker in doc.get("tickers", []):
            if ticker in counts:
                counts[ticker][doc.get("tone", "neutral")] += 1

    output: dict[str, Any] = {}
    for symbol, counter in counts.items():
        total = sum(counter.values())
        if total == 0:
            output[symbol] = {"label": "neutral", "confidence": 0.0}
            continue
        label, value = counter.most_common(1)[0]
        output[symbol] = {"label": label, "confidence": round(value / total, 2)}
    return output


def portfolio_agent(holdings: list[Holding], fundamentals: dict[str, dict[str, Any]]) -> dict[str, Any]:
    if not holdings:
        return {
            "has_portfolio": False,
            "concentration_risk": "No portfolio provided",
            "sector_skew": {},
            "top_exposure": None,
        }

    total_weight = sum(h.weight for h in holdings)
    normalized = []
    if total_weight > 0:
        normalized = [(h.symbol, h.weight / total_weight * 100.0) for h in holdings]

    top = max(normalized, key=lambda x: x[1], default=(None, 0.0))
    concentration = "elevated" if top[1] >= 35 else "moderate" if top[1] >= 20 else "low"

    sector_counter: Counter = Counter()
    for symbol, weight in normalized:
        sector = fundamentals.get(symbol, {}).get("sector", "Unknown")
        sector_counter[sector] += weight

    return {
        "has_portfolio": True,
        "concentration_risk": concentration,
        "sector_skew": dict(sector_counter),
        "top_exposure": {"symbol": top[0], "weight": round(top[1], 2)},
    }
