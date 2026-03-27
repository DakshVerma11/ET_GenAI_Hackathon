from __future__ import annotations


def expand_query(query: str, intent: str) -> list[str]:
    base = [query]
    templates = {
        "comparison": [
            "fundamentals comparison pe roe debt growth",
            "technicals trend support resistance rsi",
            "sentiment and management guidance",
        ],
        "portfolio_risk": [
            "portfolio risk concentration leverage",
            "technical downside support breakdown",
            "negative sentiment and risk factors",
        ],
        "concall_query": [
            "concall commentary guidance margins capex demand",
            "management tone risks and outlook",
        ],
        "general_query": [
            "valuation trend sentiment filing updates",
        ],
    }
    for suffix in templates.get(intent, templates["general_query"]):
        base.append(f"{query} {suffix}")
    return base
