# Market ChatGPT - Next Gen (Free-Tier MVP)

This project provides a working end-to-end MVP for Indian investor intelligence with:

- Portfolio-aware chat
- Advanced RAG (query expansion + hybrid retrieval + reranking)
- Source-cited responses
- Hugging Face integration:
  - Generator: Qwen2.5-7B-Instruct
  - Embeddings: Hugging Face financial-capable embedding model (configured via env)

## Tech Stack

- Backend: FastAPI
- Frontend: Streamlit
- RAG: LangChain + FAISS
- LLM + embeddings: Hugging Face Inference API

## Project Structure

backend/
  api/
  agents/
  rag/
  models/
  services/
  main.py
frontend/
  streamlit_app.py
data/
  documents.json
  fundamentals.json
  technicals.json
vectorstore/
.env
requirements.txt

## Setup

1. Create and activate virtual environment.
2. Install dependencies: pip install -r requirements.txt
3. Create .env from .env.example and set HF_API_KEY.

## Run Backend

uvicorn backend.main:app --reload --port 8000

## Run Frontend

streamlit run frontend/streamlit_app.py

The Streamlit UI calls FastAPI endpoints for CSV portfolio upload and chat.

## Example Queries

- Compare TATAMOTORS vs M_M
- Which stock in my portfolio is most risky?
- What risks were mentioned in last concall?

## Notes

- If HF_API_KEY is missing, the app still runs with deterministic fallback embeddings and synthesis text.
- To use a more finance-specific embedding model, set HF_EMBEDDING_MODEL in .env.
