from __future__ import annotations

from collections import Counter
from typing import Any

from backend.models.schemas import Holding


def run(holdings: list[Holding], fundamentals: dict[str, dict[str, Any]]) -> dict[str, Any]:
    if not holdings:
        return {
            "has_portfolio": False,
            "top_exposure": None,
            "concentration_risk": "unknown",
            "sector_imbalance": {},
        }

    alloc_sum = sum(h.allocation for h in holdings)
    normalized = []
    for h in holdings:
        allocation = (h.allocation / alloc_sum * 100) if alloc_sum > 0 else 0
        normalized.append((h.symbol, allocation))

    top_symbol, top_weight = max(normalized, key=lambda x: x[1])
    concentration = "high" if top_weight >= 35 else "medium" if top_weight >= 20 else "low"

    sector_counter: Counter = Counter()
    for symbol, weight in normalized:
        sector = fundamentals.get(symbol, {}).get("sector", "Unknown")
        sector_counter[sector] += weight

    return {
        "has_portfolio": True,
        "top_exposure": {"symbol": top_symbol, "allocation": round(top_weight, 2)},
        "concentration_risk": concentration,
        "sector_imbalance": dict(sector_counter),
    }
