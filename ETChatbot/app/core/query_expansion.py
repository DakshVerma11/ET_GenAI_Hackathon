from __future__ import annotations

from app.models.schemas import IntentResult


def expand_query(query: str, intent_result: IntentResult) -> list[str]:
    expansions = [query]

    if intent_result.intent == "comparison":
        expansions.extend(
            [
                f"{query} fundamentals comparison pe roe debt profitability",
                f"{query} technical trend support resistance rsi",
                f"{query} sentiment and concall tone",
            ]
        )
    elif intent_result.intent in {"portfolio_risk", "risk_lookup"}:
        expansions.extend(
            [
                f"{query} leverage earnings volatility",
                f"{query} technical downside and support breakdown",
                f"{query} negative sentiment filing risk factors",
            ]
        )
    elif intent_result.intent == "concall_query":
        expansions.extend([f"{query} management guidance capex margin demand"]) 
    else:
        expansions.extend([f"{query} valuation trend sentiment regulatory updates"])

    return list(dict.fromkeys(expansions))
