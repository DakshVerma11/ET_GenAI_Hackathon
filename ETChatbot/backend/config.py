from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv


ROOT_DIR = Path(__file__).resolve().parent.parent
load_dotenv(ROOT_DIR.parent / ".env")


class Settings:
    hf_api_key: str = os.getenv("HF_API_KEY", "")
    groq_api_key: str = os.getenv("GROQ_API_KEY", "")
    generator_model: str = os.getenv("HF_GENERATOR_MODEL", "Qwen/Qwen2.5-7B-Instruct")
    embedding_model: str = os.getenv("HF_EMBEDDING_MODEL", "sentence-transformers/all-MiniLM-L6-v2")
    demo_mode: bool = os.getenv("DEMO_MODE", "true").lower() in {"1", "true", "yes"}
    request_timeout_sec: int = int(os.getenv("CHAT_REQUEST_TIMEOUT_SEC", "20"))
    retrieve_top_k: int = min(5, int(os.getenv("CHAT_RETRIEVE_TOP_K", "5")))
    context_char_limit: int = int(os.getenv("CHAT_CONTEXT_CHAR_LIMIT", "3500"))
    data_path: Path = ROOT_DIR / "data"
    vectorstore_path: Path = ROOT_DIR / "vectorstore"


settings = Settings()
