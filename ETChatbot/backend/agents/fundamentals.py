from __future__ import annotations

from typing import Any


def run(entities: list[str], fundamentals: dict[str, dict[str, Any]]) -> dict[str, Any]:
    output: dict[str, Any] = {}
    for e in entities:
        if e in fundamentals:
            f = fundamentals[e]
            output[e] = {
                "pe": f["pe"],
                "roe": f["roe"],
                "growth": f["revenue_growth"],
                "debt": f["debt_to_equity"],
            }
    return output
