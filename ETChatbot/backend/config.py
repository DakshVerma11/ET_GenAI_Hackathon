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
    data_path: Path = ROOT_DIR / "data"
    vectorstore_path: Path = ROOT_DIR / "vectorstore"


settings = Settings()
