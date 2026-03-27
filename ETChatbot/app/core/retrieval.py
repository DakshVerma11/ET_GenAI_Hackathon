from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from typing import Any

import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer


@dataclass
class RetrievedDoc:
    doc: dict[str, Any]
    score: float


class HybridRetriever:
    def __init__(self, documents: list[dict[str, Any]]) -> None:
        self.documents = documents
        self.vectorizer = TfidfVectorizer(stop_words="english")
        self.matrix = self.vectorizer.fit_transform([d["text"] for d in documents])

    @staticmethod
    def _keyword_score(query: str, text: str) -> float:
        q_tokens = set(query.lower().split())
        t_tokens = set(text.lower().split())
        if not q_tokens:
            return 0.0
        return len(q_tokens.intersection(t_tokens)) / len(q_tokens)

    def retrieve(self, queries: list[str], top_k: int = 8) -> list[RetrievedDoc]:
        score_map: dict[str, float] = {}
        doc_map: dict[str, dict[str, Any]] = {d["id"]: d for d in self.documents}

        for query in queries:
            q_vec = self.vectorizer.transform([query])
            dense_scores = (q_vec @ self.matrix.T).toarray().flatten()

            for idx, dense in enumerate(dense_scores):
                doc = self.documents[idx]
                sparse = self._keyword_score(query, doc["text"])
                hybrid = 0.45 * float(sparse) + 0.55 * float(dense)
                score_map[doc["id"]] = max(score_map.get(doc["id"], 0.0), hybrid)

        reranked = self._rerank(score_map, doc_map)
        return reranked[:top_k]

    def _rerank(self, score_map: dict[str, float], doc_map: dict[str, dict[str, Any]]) -> list[RetrievedDoc]:
        today = date.today()
        source_weight = {"filing": 1.0, "concall": 0.9, "sebi": 0.95, "news": 0.75}
        results: list[RetrievedDoc] = []

        for doc_id, score in score_map.items():
            doc = doc_map[doc_id]
            doc_date = date.fromisoformat(doc["date"])
            days_old = max((today - doc_date).days, 1)
            recency = 1 / np.log1p(days_old + 1)
            weighted = 0.65 * score + 0.2 * recency + 0.15 * source_weight.get(doc["source"], 0.7)
            results.append(RetrievedDoc(doc=doc, score=float(weighted)))

        return sorted(results, key=lambda x: x.score, reverse=True)
