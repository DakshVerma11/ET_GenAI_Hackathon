from __future__ import annotations

from collections import defaultdict
from typing import Any

import numpy as np
from langchain_community.vectorstores import FAISS
from langchain_core.documents import Document
from langchain_core.embeddings import Embeddings
from langchain_text_splitters import RecursiveCharacterTextSplitter

from backend.rag.hf_client import hf_service


class HFInferenceEmbeddings(Embeddings):
    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        return hf_service.embed_texts(texts)

    def embed_query(self, text: str) -> list[float]:
        return hf_service.embed_texts([text])[0]


def _cosine(a: np.ndarray, b: np.ndarray) -> float:
    denom = (np.linalg.norm(a) * np.linalg.norm(b))
    if denom == 0:
        return 0.0
    return float(np.dot(a, b) / denom)


class HybridRetriever:
    def __init__(self, raw_documents: list[dict[str, Any]]) -> None:
        self.embedding = HFInferenceEmbeddings()
        self.documents = self._to_chunks(raw_documents)
        self.vectorstore = FAISS.from_documents(self.documents, self.embedding)

    @staticmethod
    def _to_chunks(raw_documents: list[dict[str, Any]]) -> list[Document]:
        splitter = RecursiveCharacterTextSplitter(chunk_size=400, chunk_overlap=40)
        docs: list[Document] = []
        for item in raw_documents:
            chunks = splitter.split_text(item["text"])
            for idx, chunk in enumerate(chunks):
                metadata = {
                    "id": f"{item['id']}-c{idx}",
                    "doc_id": item["id"],
                    "title": item["title"],
                    "source": item["source"],
                    "stock": item["stock"],
                    "date": item["date"],
                }
                docs.append(Document(page_content=chunk, metadata=metadata))
        return docs

    @staticmethod
    def _sparse_score(query: str, text: str) -> float:
        q = set(query.lower().split())
        t = set(text.lower().split())
        if not q:
            return 0.0
        return len(q.intersection(t)) / len(q)

    def retrieve(self, expanded_queries: list[str], top_k: int = 8) -> list[dict[str, Any]]:
        combined: dict[str, dict[str, Any]] = defaultdict(lambda: {"dense": 0.0, "sparse": 0.0, "doc": None})

        for q in expanded_queries:
            dense_hits = self.vectorstore.similarity_search_with_score(q, k=top_k)
            for doc, distance in dense_hits:
                dense = 1.0 / (1.0 + float(distance))
                key = doc.metadata["id"]
                combined[key]["dense"] = max(combined[key]["dense"], dense)
                combined[key]["doc"] = doc

            for doc in self.documents:
                score = self._sparse_score(q, doc.page_content)
                if score > 0:
                    key = doc.metadata["id"]
                    combined[key]["sparse"] = max(combined[key]["sparse"], score)
                    combined[key]["doc"] = doc

        reranked: list[dict[str, Any]] = []
        for item in combined.values():
            doc = item["doc"]
            if doc is None:
                continue
            dense = item["dense"]
            sparse = item["sparse"]
            query_vec = np.array(self.embedding.embed_query(expanded_queries[0]))
            doc_vec = np.array(self.embedding.embed_query(doc.page_content))
            cosine = _cosine(query_vec, doc_vec)
            final_score = 0.45 * dense + 0.25 * sparse + 0.30 * cosine
            reranked.append(
                {
                    "score": round(float(final_score), 4),
                    "text": doc.page_content,
                    "metadata": doc.metadata,
                }
            )

        reranked.sort(key=lambda x: x["score"], reverse=True)
        return reranked[:top_k]
