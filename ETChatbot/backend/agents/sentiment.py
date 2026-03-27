from __future__ import annotations

from collections import Counter


def run(entities: list[str], retrieved_docs: list[dict]) -> dict:
    counters = {e: Counter() for e in entities}
    for d in retrieved_docs:
        stock = d["metadata"].get("stock", "")
        if stock in counters:
            text = d["text"].lower()
            if any(k in text for k in ["pressure", "softness", "risk", "slower", "cautious"]):
                counters[stock]["negative"] += 1
            elif any(k in text for k in ["robust", "strong", "improved", "upside"]):
                counters[stock]["positive"] += 1
            else:
                counters[stock]["neutral"] += 1

    result = {}
    for stock, counter in counters.items():
        total = sum(counter.values())
        if total == 0:
            result[stock] = {"label": "neutral", "confidence": 0.0}
            continue
        label, count = counter.most_common(1)[0]
        result[stock] = {"label": label, "confidence": round(count / total, 2)}
    return result
