from __future__ import annotations

import json
from typing import Any

import requests

from backend.config import settings


class HFService:
    def __init__(self) -> None:
        self.api_key = settings.hf_api_key
        self.headers = {"Authorization": f"Bearer {self.api_key}"} if self.api_key else {}

    def embed_texts(self, texts: list[str]) -> list[list[float]]:
        if not self.api_key:
            return [self._fallback_embedding(t) for t in texts]

        # Use new HF router
        url = f"https://router.huggingface.co/hf-inference/models/{settings.embedding_model}"
        vectors: list[list[float]] = []
        
        for text in texts:
            try:
                response = requests.post(url, headers=self.headers, json={"inputs": text}, timeout=15)
                if response.status_code == 200:
                    raw = response.json()
                    # Some models return a list of lists of floats
                    if raw and isinstance(raw[0], list):
                        dim = len(raw[0])
                        pooled = [0.0] * dim
                        for token_vec in raw:
                            for i, value in enumerate(token_vec):
                                pooled[i] += float(value)
                        vectors.append([v / max(len(raw), 1) for v in pooled])
                    else:
                        vectors.append([float(x) for x in raw])
                else:
                    vectors.append(self._fallback_embedding(text))
            except Exception:
                vectors.append(self._fallback_embedding(text))
        return vectors

    def generate(self, prompt: str) -> str:
        if settings.groq_api_key:
            url = "https://api.groq.com/openai/v1/chat/completions"
            headers = {
                "Authorization": f"Bearer {settings.groq_api_key}",
                "Content-Type": "application/json"
            }
            payload = {
                "model": "llama-3.3-70b-versatile",
                "messages": [
                    {"role": "system", "content": "You are a precise financial analyst for Indian retail investors."},
                    {"role": "user", "content": prompt}
                ],
                "temperature": 0.2,
                "max_tokens": 1024
            }
            try:
                response = requests.post(url, headers=headers, json=payload, timeout=30)
                if response.status_code == 200:
                    return response.json()["choices"][0]["message"]["content"].strip()
                else:
                    return f"Groq Model call failed: {response.status_code} - {response.text}"
            except Exception as ex:
                return f"Groq Model call failed exception: {ex}"

        if not self.api_key:
            return "HF_API_KEY missing. Using deterministic fallback synthesis."

        url = f"https://router.huggingface.co/hf-inference/models/{settings.generator_model}"
        payload = {
            "inputs": f"System: You are a precise financial analyst for Indian retail investors.\nUser: {prompt}\nAssistant:",
            "parameters": {
                "max_new_tokens": 650,
                "temperature": 0.2,
                "return_full_text": False
            }
        }
        
        try:
            response = requests.post(url, headers=self.headers, json=payload, timeout=30)
            
            # If 404 or 503, fallback to robust free-tier models natively hosted
            fallbacks = [
                "Qwen/Qwen2.5-72B-Instruct",
                "mistralai/Mistral-7B-Instruct-v0.3",
                "HuggingFaceH4/zephyr-7b-beta"
            ]
            
            for f_model in fallbacks:
                if response.status_code in [404, 503]:
                    url = f"https://router.huggingface.co/hf-inference/models/{f_model}"
                    response = requests.post(url, headers=self.headers, json=payload, timeout=30)
                else:
                    break
                
            if response.status_code == 200:
                body = response.json()
                if isinstance(body, list) and len(body) > 0 and "generated_text" in body[0]:
                    return body[0]["generated_text"].strip()
                return str(body).strip()
            else:
                # Ultimate MVP Fallback
                return (f"[API Offline - Fallback Synthesis] Based on the retrieved context, "
                        f"the market shows mixed signals. For specific stocks, observe the "
                        f"Agent Insights and the provided documents below.")
        except Exception as ex:
            return f"Model call failed exception: {ex}"

    @staticmethod
    def _fallback_embedding(text: str, dim: int = 64) -> list[float]:
        vec = [0.0] * dim
        for idx, ch in enumerate(text.lower()):
            vec[idx % dim] += (ord(ch) % 31) / 31.0
        norm = sum(v * v for v in vec) ** 0.5
        if norm == 0:
            return vec
        return [v / norm for v in vec]


hf_service = HFService()
