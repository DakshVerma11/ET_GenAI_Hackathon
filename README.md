# ET Markets AI Intelligence Platform

Submission for The Economic Times GenAI Hackathon 2026  
Problem Statement: PS-6 - AI for the Indian Investor  
Team: NITDominars

## Table of Contents

1. Executive Summary
2. Problem Statement Alignment
3. Product Overview
4. Key Features by Module
5. System Architecture (Detailed)
6. Data Flow and Request Lifecycle
7. Repository Structure
8. Setup and Configuration
9. Run Instructions
10. API Surface
11. Reliability, Constraints, and Mitigations
12. Security and Secret Management
13. Impact Model (Detailed)
14. Submission Readiness Checklist
15. Team and License

## 1) Executive Summary

ET Markets AI Intelligence Platform is a unified GenAI system designed to help Indian retail investors convert fragmented data into actionable decisions. The platform integrates four required problem-statement capabilities in one deployable application:

- Opportunity Radar
- Chart Pattern Intelligence
- MarketGPT (portfolio-aware assistant)
- AI Video Engine

Instead of running disconnected services and UIs, this project exposes a single user-facing app on one port.

Primary URL:

- http://localhost:8000

## 2) Problem Statement Alignment

PS-6 asks for a practical intelligence layer for Indian investors. This repository addresses that through four operational modules:

1. Opportunity Radar
2. Chart Pattern Intelligence
3. MarketGPT - Next Gen
4. AI Market Video Engine

Why this implementation is practical:

- One-command startup
- Unified navigation and API integration
- Real market data ingestion paths
- AI reasoning and summarization components
- Output formats for both analysis and communication

## 3) Product Overview

The platform is implemented as a unified FastAPI-based gateway with mounted module routes and static frontends.

Core entry points:

- [main.py](main.py)
- [start.py](start.py)

High-level behavior:

1. User opens root URL.
2. Frontend routes provide access to each module.
3. APIs call module logic for signals, chat, or video processing.
4. Results are shown in web dashboards or generated media outputs.

## Cloud Demo Mode (Render Free Tier)

This deployment runs in a constrained cloud environment. Full-scale video rendering and high-frequency processing are available in production or local setups.

Recommended environment flags for cloud demo reliability:

- ENABLE_VIDEO=false
- DEMO_MODE=true
- REQUEST_TIMEOUT_SEC=22

Render start command:

- uvicorn main:app --host 0.0.0.0 --port $PORT

## 4) Key Features by Module

### 4.1 Opportunity Radar

Primary code areas:

- [Radar/routes.py](Radar/routes.py)
- [Radar/pipeline.py](Radar/pipeline.py)
- [Radar/signals.py](Radar/signals.py)

Capabilities:

- Event/opportunity signal generation
- Alert listing and alert state update APIs
- Sector-level heat and opportunity views
- Dashboard integration through unified /api/radar endpoints

### 4.2 Chart Pattern Intelligence

Primary code areas:

- [Chart_Pattern/main.py](Chart_Pattern/main.py)
- [Chart_Pattern/pattern_engine.py](Chart_Pattern/pattern_engine.py)

Capabilities:

- Technical pattern extraction
- Signal confidence/conviction scoring
- Symbol-level pattern interpretation and reporting
- JSON/API-delivered signal outputs for UI

### 4.3 MarketGPT (Portfolio-Aware)

Primary code areas:

- [ETChatbot/backend/main.py](ETChatbot/backend/main.py)
- [ETChatbot/backend/rag](ETChatbot/backend/rag)
- [ETChatbot/frontend/script.js](ETChatbot/frontend/script.js)

Capabilities:

- Portfolio-context Q&A
- Intent-aware orchestration and retrieval
- Response synthesis from market + document context
- Query prefill integration from Radar deep-research flow

### 4.4 AI Video Engine

Primary code areas:

- [VideoGen/api.py](VideoGen/api.py)
- [VideoGen/src/pipeline_runner.py](VideoGen/src/pipeline_runner.py)
- [VideoGen/src/tts_engine.py](VideoGen/src/tts_engine.py)
- [VideoGen/src/video_engine.py](VideoGen/src/video_engine.py)

Capabilities:

- Market snapshot extraction
- AI script generation
- TTS narration synthesis
- Rendered MP4 generation pipeline

## 5) System Architecture (Detailed)

### 5.1 Architecture Style

The system follows a modular-monolith integration approach:

- Modular responsibilities per domain folder
- Unified runtime process for simpler operation and demo reliability
- Route-level isolation for each module namespace

This choice reduces operational complexity while preserving clear component boundaries.

### 5.2 Runtime Topology

Text diagram:

Browser
	-> Unified FastAPI App (port 8000)
		-> Frontend Routes: /, /chart-pattern, /radar, /market-chat, /video
		-> API Routes:
			 -> /api/chart/*
			 -> /api/radar/*
			 -> /api/chat/*
			 -> /api/video/*

### 5.3 Unified Gateway Responsibilities

In [main.py](main.py), the app:

- initializes the root FastAPI application
- includes each module router with prefix scoping
- mounts static frontends/assets
- coordinates startup lifecycle hooks where needed

### 5.4 Module Communication Pattern

The modules are integrated by in-process function/API composition, not distributed RPC:

- Frontend calls the unified API namespace
- API handlers dispatch to module-specific business logic
- Results return to frontend without inter-service network hops

Benefits:

- Lower latency in local execution
- Easier debugging and deterministic startup
- Fewer deployment moving parts

Trade-off:

- Long-running tasks can hold request context unless offloaded

### 5.5 Handling Long-Running Work

Video generation can take substantial time. The system avoids event-loop conflicts by offloading blocking execution paths (for example, thread offloading patterns in video API paths).

Future production enhancement:

- move long renders to a queued job model
- expose status polling endpoint
- optionally persist job state in database/cache

### 5.6 Data Sources and AI Dependencies

Data inputs:

- market feeds via yfinance/external providers
- project JSON knowledge files in data folders
- user portfolio CSV inputs

Model and AI dependencies:

- Groq API for generation/inference workflows
- embedding/retrieval stack for MarketGPT RAG paths

### 5.7 Error Handling and Resilience Design

Current resilience characteristics:

- startup dependency checks in launcher
- process-failure detection to avoid false-success startup
- route-prefix normalization for unified mode
- Windows-safe console logging choices for stability

Known operational realities:

- external provider intermittency (timeouts/cookies/404s)
- long render durations can exceed short HTTP client timeouts

## 6) Data Flow and Request Lifecycle

### 6.1 User Navigation Flow

1. User lands on root page.
2. User selects module via navigation.
3. Frontend module page loads.
4. Frontend calls corresponding /api/* routes.
5. Response is rendered as charts, cards, text analysis, or media links.

### 6.2 Example Radar Flow

1. UI calls /api/radar/signals.
2. Radar route invokes pipeline/aggregation logic.
3. Response returns signals and metadata.
4. UI updates signal cards and filters.

### 6.3 Example MarketGPT Flow

1. User submits query or query is prefilled from Radar deep research.
2. Backend classifies intent and retrieves relevant context.
3. Synthesis layer creates final answer.
4. UI renders answer with supporting structure.

### 6.4 Example Video Flow

1. UI calls video generation endpoint.
2. Pipeline extracts market state and drafts script.
3. TTS and rendering stages generate final media.
4. Output metadata and artifact path are returned.

## 7) Repository Structure

Core files:

- [main.py](main.py): unified app and mounted routes
- [start.py](start.py): launcher, install bootstrap, startup checks
- [index.html](index.html): platform entry frontend

Module roots:

- [Radar](Radar)
- [Chart_Pattern](Chart_Pattern)
- [ETChatbot](ETChatbot)
- [VideoGen](VideoGen)

Important subpaths:

- [Radar/routes.py](Radar/routes.py)
- [Chart_Pattern/pattern_engine.py](Chart_Pattern/pattern_engine.py)
- [ETChatbot/backend/rag](ETChatbot/backend/rag)
- [VideoGen/src](VideoGen/src)

## 8) Setup and Configuration

### 8.1 Prerequisites

- Python 3.8 or higher
- Internet access for model and market endpoints

### 8.2 Environment Variables

Expected secret locations:

- [ETChatbot/.env](ETChatbot/.env)
- [VideoGen/.env](VideoGen/.env)

Required variables:

- GROQ_API_KEY
- HF_API_KEY

Optional model override variables may be configured in module-level settings when needed.

### 8.3 First-Run Notes

- first run can take longer due to dependency install
- startup behavior is controlled through launcher flags

## 9) Run Instructions

Run from repository root:

```powershell
python start.py
```

Skip dependency installation:

```powershell
python start.py --skip-install
```

Do not auto-open browser:

```powershell
python start.py --no-browser
```

Access the app at:

- http://localhost:8000

## 10) API Surface

Primary namespaces:

- /api/chart/*
- /api/radar/*
- /api/chat/*
- /api/video/*

Common UI routes:

- /
- /chart-pattern
- /radar
- /market-chat
- /video

## 11) Reliability, Constraints, and Mitigations

### 11.1 Reliability Improvements Already Present

- dependency compatibility fixes across modules
- robust startup checks in launcher
- route alignment fixes for unified and standalone compatibility
- safer async boundaries for long-running video generation

### 11.2 Known Constraints

- third-party market providers can occasionally fail or throttle
- video rendering can exceed short synchronous client timeout windows

### 11.3 Recommended Next Technical Enhancements

1. Introduce asynchronous job queue for video generation.
2. Add status polling and retry metadata endpoint.
3. Cache high-frequency market fetches with stale-while-revalidate strategy.
4. Add module-level integration tests for top API paths.

## 12) Security and Secret Management

- Keep API keys in local .env files only.
- Do not commit secrets to repository history.
- Rotate keys before public demos if keys were shared in temporary environments.
- Consider adding request logging redaction for sensitive payloads.

## 13) Impact Model (Detailed)

### 13.1 Objective

Estimate practical value created for a retail investor using the platform versus a manual baseline.

### 13.2 Baseline Assumptions

Assume one active investor:

- reviews market data 5 days per week
- spends around 45 minutes/day on discovery and interpretation
- makes 8 tactical decisions/month under incomplete information

Assume platform usage:

- daily use of Radar + Chart Pattern modules
- regular use of MarketGPT for portfolio-context decisions
- consumption of AI Video summaries for compact updates

### 13.3 Time-Saving Model

Manual baseline:

- $45$ min/day x $22$ days/month $= 990$ min/month

With platform:

- $20$ min/day x $22$ days/month $= 440$ min/month

Net savings:

- $990 - 440 = 550$ min/month
- $550/60 = 9.17$ hours/month

If time value is INR 300/hour:

- monthly value $= 9.17 \times 300 = 2,751$ INR
- annual value $= 2,751 \times 12 = 33,012$ INR

### 13.4 Decision-Quality Model

Assumptions:

- tactical capital influenced monthly: INR 200,000
- avoidable baseline drag from noise/timing: $1.2\%$/month
- platform reduces avoidable drag by $25\%$

Baseline drag:

- $200,000 \times 1.2\% = 2,400$ INR/month

Recovered value:

- $2,400 \times 25\% = 600$ INR/month
- annualized $= 7,200$ INR

### 13.5 Combined User-Level Annual Value

- productivity component: INR 33,012
- decision-quality component: INR 7,200
- combined: INR 40,212 per user per year

### 13.6 Scale Scenario

If 10,000 active users adopt and 35% realize full modeled impact:

- effective users: $10,000 \times 35\% = 3,500$
- aggregate annual value: $3,500 \times 40,212 = 140,742,000$ INR
- approximately INR 14.07 crore annual value

### 13.7 Conservative Scenario

Conservative assumptions:

- only 5 hours/month saved
- only INR 300/month decision-drag recovery

Annual user value:

- $5 \times 300 \times 12 + 300 \times 12 = 21,600$ INR/year

Even this conservative case remains materially positive.

### 13.8 Non-Quantified Benefits

- higher decision confidence from explainable outputs
- reduced dependence on low-signal social media tips
- faster reaction to opportunity windows
- better investor communication through generated video summaries

### 13.9 Model Limitations

- directional model; not audited PnL attribution
- real outcomes vary with behavior and market regime
- production validation should use controlled cohort analysis and retention-linked metrics

## 14) Submission Readiness Checklist

- complete codebase present in public repository
- one-command startup available
- architecture details included in this README
- impact model included in this README
- module coverage mapped to PS-6 requirements

## 15) Team and License

Team:

- NITDominars

License note:

- Built for ET GenAI Hackathon 2026 submission.
