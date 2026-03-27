from __future__ import annotations

from typing import Any


def _risk_score_for_symbol(
    symbol: str,
    fundamentals: dict[str, dict[str, Any]],
    technicals: dict[str, dict[str, Any]],
    sentiment: dict[str, dict[str, Any]],
) -> float:
    score = 0.0
    f = fundamentals.get(symbol, {})
    t = technicals.get(symbol, {})
    s = sentiment.get(symbol, {})

    if f.get("debt_to_equity", 0) > 1.2:
        score += 0.35
    if t.get("trend") in {"downtrend", "range_weak"}:
        score += 0.3
    if t.get("volatility", "low") == "high":
        score += 0.2
    if s.get("label") == "negative":
        score += 0.15
    return score


def synthesize(
    query: str,
    intent: str,
    entities: list[str],
    fundamentals_out: dict[str, Any],
    technicals_out: dict[str, Any],
    sentiment_out: dict[str, Any],
    portfolio_out: dict[str, Any],
    retrieved_docs: list[dict[str, Any]],
) -> dict[str, Any]:
    if not entities and portfolio_out.get("top_exposure", {}).get("symbol"):
        entities = [portfolio_out["top_exposure"]["symbol"]]

    analysis: list[str] = []
    risky_symbol = None
    max_risk = -1.0

    for symbol in entities:
        risk = _risk_score_for_symbol(symbol, fundamentals_out, technicals_out, sentiment_out)
        if risk > max_risk:
            max_risk = risk
            risky_symbol = symbol

        f = fundamentals_out.get(symbol)
        t = technicals_out.get(symbol)
        s = sentiment_out.get(symbol)
        if f:
            analysis.append(
                f"{symbol}: PE {f['pe']}, ROE {f['roe']}%, Debt/Equity {f['debt_to_equity']}, Revenue Growth {f['revenue_growth']}%."
            )
        if t:
            analysis.append(
                f"{symbol}: Trend {t['trend']}, RSI {t['rsi']}, Support {t['support']}, Resistance {t['resistance']}, Volatility {t['volatility']}."
            )
        if s:
            analysis.append(
                f"{symbol}: Sentiment {s['label']} (confidence {s['confidence']})."
            )

    if risky_symbol:
        verdict = f"Most risky symbol right now: {risky_symbol}."
    else:
        verdict = "Insufficient entity context; showing best-effort market summary."

    if not analysis:
        analysis.append("No strong structured signals were available. Returned retrieval-backed summary.")

    if portfolio_out.get("has_portfolio"):
        top = portfolio_out.get("top_exposure")
        portfolio_impact = (
            f"Concentration risk is {portfolio_out['concentration_risk']}. "
            f"Top exposure is {top['symbol']} at {top['weight']}%."
            if top and top.get("symbol")
            else "Portfolio provided, but top exposure could not be computed."
        )
    else:
        portfolio_impact = "Portfolio context missing, so personalization was limited."

    citations = [
        {
            "id": d["id"],
            "title": d["title"],
            "source": d["source"],
            "date": d["date"],
        }
        for d in retrieved_docs[:4]
    ]

    return {
        "verdict": verdict,
        "supporting_analysis": analysis,
        "portfolio_impact": portfolio_impact,
        "citations": citations,
        "metadata": {
            "intent": intent,
            "query": query,
            "entity_count": len(entities),
            "retrieved_docs": len(retrieved_docs),
        },
    }
