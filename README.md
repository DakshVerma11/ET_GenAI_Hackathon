# 🏆 ET Markets AI Intelligence Platform

> **Submission for The Economic Times GenAI Hackathon 2026**  
> **Problem Statement: PS-6 — AI for the Indian Investor**  
> **Team: NITDominars**

---

## 📋 Table of Contents

1. [Hackathon Context](#hackathon-context)
2. [Problem Statement](#problem-statement)
3. [Our Solution](#our-solution)
4. [Platform Architecture](#platform-architecture)
5. [Modules](#modules)
   - [Opportunity Radar](#1-opportunity-radar)
   - [Chart Pattern Intelligence](#2-chart-pattern-intelligence)
   - [Market ChatGPT — Next Gen](#3-market-chatgpt--next-gen)
   - [AI Market Video Engine](#4-ai-market-video-engine)
6. [Tech Stack](#tech-stack)
7. [Project Structure](#project-structure)
8. [Setup & Installation](#setup--installation)
9. [Running the Platform](#running-the-platform)
10. [Environment Variables](#environment-variables)
11. [API Reference](#api-reference)
12. [Judging Criteria Alignment](#judging-criteria-alignment)
13. [Team](#team)

---

## 🏅 Hackathon Context

| Field | Details |
|-------|---------|
| **Hackathon** | The Economic Times GenAI Hackathon 2026 |
| **Organiser** | The Economic Times & Times Internet |
| **Partner** | Unstop |
| **Prize Pool** | ₹10 Lakh |
| **Track** | AI & Finance |
| **Problem Statement** | **PS-6 — AI for the Indian Investor** |
| **Team Name** | **NITDominars** |
| **Submission Deadline** | 29th March 2026 |
| **Phase** | Phase 2 — Prototype Submission |

---

## 🎯 Problem Statement

> *"India has 14 crore+ demat accounts, but most retail investors are flying blind — reacting to tips, missing filings, unable to read technicals, and managing mutual fund portfolios on gut feel. ET Markets has the data. Build the intelligence layer that turns data into actionable, money-making decisions."*

### What We Were Asked to Build

| Module | Description |
|--------|-------------|
| **Opportunity Radar** | AI that monitors corporate filings, bulk/block deals, insider trades, and management commentary shifts — surfacing missed opportunities as daily alerts |
| **Chart Pattern Intelligence** | Real-time technical pattern detection across NSE with plain-English explanation and historical back-tested success rates |
| **Market ChatGPT — Next Gen** | A deeper, portfolio-aware AI assistant with multi-step analysis, deep data integration, and source-cited responses |
| **AI Market Video Engine** | Auto-generate 30–90 second market update videos from real-time data with race charts, sector rotations, FII/DII flows, and zero human editing |

---

## 💡 Our Solution

We built the **ET Markets AI Intelligence Platform** — a fully integrated, production-grade solution that implements **all four modules** from the problem statement, unified behind a single web interface.

### Key Differentiators

- 🏠 **Single-port architecture** — One URL (`http://localhost:8000`), one command, everything running
- 🔗 **True integration** — All modules share a unified design system, navigation, and entry point
- ⚡ **Groq-powered inference** — Using `llama-3.3-70b-versatile` for sub-second AI responses
- 📡 **Live NSE data** — Real-time prices via `yfinance` across all modules
- 🎬 **End-to-end video generation** — From raw market data → AI script → narrated video with captions
- 📊 **3-year backtesting** — Chart patterns backed by historical win rates, not just signals

---

## 🏗 Platform Architecture

```
┌──────────────────────────────────────────────────────────────────┐
│                    User Browser                                   │
│                   localhost:8000                                  │
└──────────────────────────┬───────────────────────────────────────┘
                           │
                           ▼
┌──────────────────────────────────────────────────────────────────┐
│                    gateway.py  (FastAPI)                          │
│                                                                   │
│  GET /                →  Home Page (index.html)                  │
│  GET /chart-pattern   →  iframe → Chart Pattern & Radar           │
│  GET /market-chat     →  iframe → Market ChatGPT                 │
│  GET /video           →  iframe → AI Video Engine                │
└──────┬────────────────────────┬─────────────────────┬────────────┘
       │                        │                     │
       ▼                        ▼                     ▼
┌─────────────┐      ┌─────────────────┐    ┌─────────────────┐
│ Chart_Pattern│      │   ETChatbot     │    │    VideoGen     │
│  (FastAPI)  │      │   (FastAPI)     │    │  (Streamlit)    │
│  port 8001  │      │   port 8002     │    │   port 8501     │
│             │      │                 │    │                 │
│  - Pattern  │      │ - Groq LLM RAG  │    │ - Groq LLM      │
│    Engine   │      │ - HF Embeddings │    │ - edge-tts TTS  │
│  - Radar    │      │ - Portfolio CSV │    │ - moviepy video │
│  - yfinance │      │ - yfinance      │    │ - yfinance      │
└─────────────┘      └─────────────────┘    └─────────────────┘
```

---

## 📦 Modules

### 1. Opportunity Radar
**Path:** `Chart_Pattern/` | **Port:** 8001 (internal) | **Access:** `/chart-pattern`

Monitors the NSE universe for actionable trading signals based on technical patterns and corporate events.

**Features:**
- 🔍 Scans 50+ NSE stocks for technical patterns on startup and on-demand
- 📊 Detects: Breakouts, RSI divergences, Moving average crossovers, Support/Resistance breaks, Candlestick patterns (Hammer, Doji, Engulfing)
- 💯 Conviction scoring (0–100) based on signal strength and volume confirmation
- 📈 3-year historical backtesting with win rates and average gain per pattern per stock
- 🏭 Sector-wise signal breakdown
- ⚡ Background scan thread — results live-update without user action

**API Endpoints:**
```
GET  /api/signals           # All signals with optional filters
GET  /api/signals/{symbol}  # Signal for specific stock
GET  /api/stats             # Market-wide statistics
GET  /api/sectors           # Sector analysis
POST /api/scan              # Trigger a fresh scan
GET  /api/health            # Server health
```

---

### 2. Chart Pattern Intelligence
**Path:** `Chart_Pattern/` | **Port:** 8001 (internal) | **Access:** `/chart-pattern`

The front-facing dashboard for the Opportunity Radar backend. Provides a rich UI with real-time signal visualization.

**Features:**
- 🎯 Live signal cards with bullish/bearish classification
- 📊 Per-signal detail view with entry price, stop-loss, target, and timeframe
- 🔎 Filter by direction (bullish/bearish) and minimum conviction score
- 🗂 Sector grouping and sorting
- 🔄 Manual rescan trigger with live status indicator

---

### 3. Market ChatGPT — Next Gen
**Path:** `ETChatbot/` | **Port:** 8002 (internal) | **Access:** `/market-chat`

A RAG-powered portfolio-aware AI assistant for Indian retail investors.

**Features:**
- 🤖 Groq LLM (`llama-3.3-70b-versatile`) for fast, accurate financial reasoning
- 📁 **Portfolio Upload** — Upload a CSV of your holdings; all answers become portfolio-aware
- 🔍 **RAG Pipeline** — HuggingFace embeddings + hybrid retriever for source-cited responses
- 📡 **Live Ticker** — Real-time NSE index feed across the top bar
- 🌍 Geopolitical risk context injection
- 📄 Response format: Verdict → Key Insights → Full Analysis → Portfolio Impact → Citations

**Portfolio CSV Format:**
```csv
symbol,allocation
RELIANCE,25
TCS,20
HDFCBANK,15
INFY,10
```

**API Endpoints:**
```
POST /chat                           # Main chat endpoint
POST /portfolio/upload-csv           # Upload portfolio holdings
GET  /portfolio/{user_id}            # Get stored portfolio
GET  /ticker                         # Live NSE data feed
```

---

### 4. AI Market Video Engine
**Path:** `VideoGen/` | **Port:** 8501 (internal) | **Access:** `/video`

Fully automated pipeline that converts live market data into a narrated 9:16 vertical video — zero human editing.

**Pipeline:**
```
Live NSE Data (yfinance)
        ↓
Market Dashboard Extraction
        ↓
Scene Planning (Blueprint Engine)
        ↓
AI Script Generation (Groq llama-3.3-70b-versatile)
        ↓
Text-to-Speech Narration (edge-tts)
        ↓
Video Rendering (moviepy + matplotlib)
        ↓
Animated Captions (shorts-style pop-up overlays)
        ↓
Final MP4 (1080×1920, 9:16 vertical)
```

**Features:**
- 🎬 7-scene structured storyboard (Intro → Indices → VIX → Sector Winners → Losers → Insight → Outro)
- 🗣 AI narration at 1.25× speed for energetic delivery
- 📊 Race-chart style animated bar charts for sector performance
- 💬 Dynamic shorts-style animated captions synced to speech
- 📱 9:16 vertical aspect ratio (YouTube Shorts / Instagram Reels ready)
- 🔄 Robust data filtering — handles missing/delisted symbols gracefully

---

## 🛠 Tech Stack

| Layer | Technology |
|-------|-----------|
| **AI / LLM** | Groq API (`llama-3.3-70b-versatile`) |
| **Embeddings** | HuggingFace `sentence-transformers/all-MiniLM-L6-v2` |
| **Market Data** | `yfinance` (live NSE data) |
| **Backend (Chart Pattern & Gateway)** | FastAPI + Uvicorn |
| **Backend (ETChatbot)** | FastAPI + Uvicorn |
| **Frontend (Chart Pattern)** | Vanilla HTML/CSS/JS |
| **Frontend (ETChatbot)** | Vanilla HTML/CSS/JS |
| **Video App** | Streamlit |
| **Video Rendering** | `moviepy 1.0.3` + `matplotlib` + `Pillow` |
| **Text-to-Speech** | `edge-tts` (Microsoft Neural TTS) |
| **Design System** | Syne + DM Sans + DM Mono (Google Fonts) |
| **Gateway** | FastAPI (iframe-based module wrapper) |

---

## 📁 Project Structure

```
ET Hackathon/
│
├── gateway.py               # 🌐 Unified gateway (port 8000) — single entry point
├── start.py                 # 🚀 One-command launcher for all services
├── start.bat                # 🪟 Windows double-click launcher
├── index.html               # 🏠 Home page / platform hub
│
├── Chart_Pattern/           # 📡 Module 1+2: Opportunity Radar & Chart Pattern
│   ├── main.py              # FastAPI backend (port 8001)
│   ├── pattern_engine.py    # NSE pattern detection engine
│   ├── index.html           # Dashboard frontend
│   ├── requirements.txt
│   └── signals.json         # Cached scan results
│
├── ETChatbot/               # 🤖 Module 3: Market ChatGPT Next Gen
│   ├── backend/
│   │   ├── main.py          # FastAPI app (port 8002)
│   │   ├── config.py        # Settings (Groq + HF keys)
│   │   ├── agents/          # Specialized analysis agents
│   │   └── rag/             # RAG pipeline (retriever, embedder, orchestrator)
│   ├── frontend/
│   │   ├── index.html       # Chat UI
│   │   ├── styles.css       # Unified design system
│   │   └── script.js        # Chat + portfolio upload logic
│   ├── data/                # Knowledge base documents
│   ├── vectorstore/         # FAISS index
│   ├── .env                 # API keys
│   └── requirements.txt
│
└── VideoGen/                # 🎬 Module 4: AI Market Video Engine
    ├── app.py               # Streamlit app (port 8501)
    ├── src/
    │   ├── ai_engine.py     # Groq script generation
    │   ├── extractor.py     # NSE data extraction
    │   ├── scene_planner.py # Scene blueprint logic
    │   ├── pipeline_runner.py # Video assembly pipeline
    │   └── insight_engine.py
    ├── output/              # Generated videos & logs
    ├── .env                 # API keys
    └── requirements.txt
```

---

## ⚙️ Setup & Installation

### Prerequisites

- Python 3.8 or higher
- pip
- Internet connection (for live NSE data + Groq API)

### API Keys Required

| Key | Where to Get | Used By |
|-----|-------------|---------|
| `GROQ_API_KEY` | [console.groq.com](https://console.groq.com) | ETChatbot + VideoGen |
| `HF_API_KEY` | [huggingface.co/settings/tokens](https://huggingface.co/settings/tokens) | ETChatbot (embeddings) |

### Configure Environment Files

**`ETChatbot/.env`:**
```env
GROQ_API_KEY=gsk_xxxxxxxxxxxxxxxxxxxxxxxxxxxx
HF_API_KEY=hf_xxxxxxxxxxxxxxxxxxxxxxxxxxxx
HF_GENERATOR_MODEL=Qwen/Qwen2.5-7B-Instruct
HF_EMBEDDING_MODEL=sentence-transformers/all-MiniLM-L6-v2
```

**`VideoGen/.env`:**
```env
GROQ_API_KEY=gsk_xxxxxxxxxxxxxxxxxxxxxxxxxxxx
```

> 💡 You can use the **same Groq API key** in both `.env` files.

---

## 🚀 Running the Platform

### One-Command Start

```powershell
# Clone / navigate to project root
cd "ET Hackathon"

# Start everything (installs deps automatically on first run)
python start.py
```

```bash
# Or on Windows, double-click:
start.bat
```

The launcher will:
1. ✅ Check Python version
2. 📦 Install all module dependencies automatically
3. 🚀 Start all 4 services
4. 🌐 Open `http://localhost:8000` in your browser

### Skip Install (Faster Subsequent Runs)

```powershell
python start.py --skip-install
```

### What Starts

| Service | Internal Port | Description |
|---------|-------------|-------------|
| Gateway | **8000** (user-facing) | Unified entry point + home page |
| Chart Pattern & Radar | 8001 (internal) | FastAPI backend |
| Market ChatGPT | 8002 (internal) | FastAPI RAG backend |
| AI Video Engine | 8501 (internal) | Streamlit app |

### 🌐 The Only URL You Need

```
http://localhost:8000
```

Navigate between all modules using the top nav bar. No port numbers required.

---

## 🔑 Environment Variables

| Variable | File | Required | Description |
|----------|------|----------|-------------|
| `GROQ_API_KEY` | `ETChatbot/.env` | ✅ | Groq API key for LLM inference |
| `HF_API_KEY` | `ETChatbot/.env` | ✅ | HuggingFace API key for embeddings |
| `HF_GENERATOR_MODEL` | `ETChatbot/.env` | Optional | Override generator model |
| `HF_EMBEDDING_MODEL` | `ETChatbot/.env` | Optional | Override embedding model |
| `GROQ_API_KEY` | `VideoGen/.env` | ✅ | Groq API key for video script generation |

---

## 📡 API Reference

### Chart Pattern & Radar API (port 8001)

```http
GET  /api/signals?direction=bullish&min_conviction=60&sort_by=conviction
GET  /api/signals/{symbol}
GET  /api/stats
GET  /api/sectors
POST /api/scan?max_stocks=50
GET  /api/patterns
GET  /api/status
GET  /api/health
```

### Market ChatGPT API (port 8002)

```http
POST /chat
Content-Type: application/json
{
  "user_id": "user123",
  "query": "What is my risk exposure in the banking sector?"
}

POST /portfolio/upload-csv?user_id=user123
Content-Type: multipart/form-data
(CSV with 'symbol' and 'allocation' columns)

GET  /portfolio/{user_id}
GET  /ticker
```

---

## 📊 Judging Criteria Alignment

| Criterion | Weight | Our Implementation |
|-----------|--------|-------------------|
| **Innovation & Creativity** | 20% | All 4 modules built + unified gateway; real backtesting; Groq-powered video scripts |
| **Technical Implementation** | 20% | FastAPI + RAG + Streamlit + moviepy; clean architecture; typed Python; single-port gateway |
| **Practical Impact** | 20% | Directly addresses all 4 sub-problems in PS-6; live NSE data; portfolio-aware answers |
| **User Experience** | 20% | Premium dark-mode UI; single URL; top-nav module switching; mobile-optimised video output |
| **Pitch Quality** | 20% | Live working demo; detailed architecture; one-command start; this README |

---

## 👥 Team

**Team NITDominars**

Submission for the **ET GenAI Hackathon 2026** — India's Largest GenAI Challenge  
Problem Statement: **PS-6 — AI for the Indian Investor**

---

## 📄 License

Built for the ET Hackathon 2026. All code is original and created for this submission.

---

<div align="center">

**ET Markets AI Intelligence Platform**  
*Turn Market Data Into Money-Making Intelligence*

Built with ❤️ by Team NITDominars for the ET GenAI Hackathon 2026

</div>
