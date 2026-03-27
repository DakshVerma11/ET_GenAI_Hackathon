from __future__ import annotations

from typing import Any


def run(entities: list[str], technicals: dict[str, dict[str, Any]]) -> dict[str, Any]:
    output: dict[str, Any] = {}
    for e in entities:
        if e in technicals:
            t = technicals[e]
            output[e] = {
                "trend": t["trend"],
                "support": t["support"],
                "resistance": t["resistance"],
                "rsi": t["rsi"],
            }
    return output
