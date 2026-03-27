# AI Market Video Engine — System Design (V5)

## 1. Executive Summary

The system is a **fully automated AI-powered market video engine** that generates professional, short-form stock market update videos (30–90 seconds) from real-time market data. The V5 architecture prioritizes **user resilience** with Streamlit-first interactive UI, graceful Gemini API fallback, and manual script input capability. The system handles missing data elegantly and requires zero human editing for final video output.

## 2. High-Level Architecture

### 2.1 Execution Flow

The system now operates as a **user-interactive Streamlit pipeline** with optional headless automation:

```
┌─────────────────────┐
│  Double-click run.bat│  → Launches Streamlit UI
└─────────────────────┘
         ↓
┌─────────────────────┐
│  Streamlit Frontend  │
└─────────────────────┘
   ↓         ↓         ↓
[Step 1]  [Step 2]  [Step 3]
Fetch     Script     Generate
Data      Gen        Video
   ↓         ↓         ↓
  ┌─────────────────────┐
  │  Headless Pipeline  │ (src/pipeline_runner.py)
  │  - Validate data    │
  │  - Render scenes    │
  │  - Synthesize TTS   │
  │  - Composite video  │
  └─────────────────────┘
         ↓
   ┌──────────────┐
   │ Output MP4 + │
   │  Metadata   │
   └──────────────┘
```

### 2.2 Module Architecture

| Layer | Module | Responsibility | Fault Tolerance |
|-------|--------|---|---|
| **UI** | [app.py](app.py) | Streamlit interactive pipeline, manual fallback, step-by-step guidance | Manual script input on Gemini failure |
| **Orchestration** | [src/pipeline_runner.py](src/pipeline_runner.py) | Coordinate data → script → visuals → audio → video | Script/dashboard override support for manual input |
| **Data** | [src/extractor.py](src/extractor.py) | yfinance concurrent fetch with timeout, symbol fallback | Skipped symbols, batch timeout, cancellation |
| **Validation** | [src/validation.py](src/validation.py) | Sanitize market data, filter invalid symbols | Partial data preservation |
| **Insights** | [src/insight_engine.py](src/insight_engine.py) | Market trend, volatility, sector leaders analysis | Neutral messaging when data is sparse |
| **Scene Planning** | [src/scene_planner.py](src/scene_planner.py) | Dynamic 7-scene layout with optional scenes | Core structure + conditional inserts |
| **Script Generation** | [src/ai_engine.py](src/ai_engine.py) | Gemini 1.5 Flash with strict JSON validation, fallback narrator | Fallback text on API failure |
| **Visuals** | [src/visual_engine.py](src/visual_engine.py), [src/chart_gen.py](src/chart_gen.py) | Scene renderer registry + 8+ scene types | Dynamic scene type mapping |
| **Audio** | [src/tts_engine.py](src/tts_engine.py) | Edge-TTS with retry and fallback voice | Retry loop, fallback voice on failure |
| **Video** | [src/video_engine.py](src/video_engine.py) | MoviePy composition with timeout and sync | FFmpeg error graceful degradation |

## 3. User-Facing Flow (Streamlit Interactive)

### Step 1: Fetch Market Data
- **User clicks:** "📊 Fetch Real-Time Market Data"
- **Pipeline fetches:** 10+ indices, 8+ sectors, FII/DII, IPO data (if available)
- **Resilience:** Missing symbols are skipped, but pipeline continues
- **Output:** Dashboard summary with metric cards (Indices, Sectors, Skipped)

### Step 2: Generate Script
- **Option A (Preferred):** User clicks "🤖 Generate Script (Gemini AI)"
  - Gemini generates data-driven narration script in strict JSON format
  - Normalizes and validates script automatically
  - If succeeds: proceed to Step 3 with ✅ confirmation
  
- **Option B (Fallback):** If Gemini API fails
  - UI shows error message
  - **User provided two recovery options:**
    1. **Manual Input:** Paste JSON script directly in text area
    2. **Try Again:** Retry Gemini after network issue resolves
  - Sample script template available for quick start

### Step 3: Generate Video
- **Preconditions:** Market data fetched + Script available (from Gemini or manual input)
- **Processing:** Streamlit shows real-time progress
  - Rendering visuals from scene blueprint
  - Synthesizing narration audio
  - Creating captions
  - Compositing final MP4
- **Output:**
  - Playable MP4 video (1080×1920, 9:16 aspect)
  - Publishing metadata (title options, hashtags)
  - Full run report with skipped symbols and provider health

## 4. Gemini API Fallback Strategy

The system handles Gemini failures gracefully:

| Scenario | Behavior |
|----------|----------|
| API Key missing or invalid | Proceed to manual input directly; show configuration warning |
| API timeout/network error | Show fallback prompt; user can paste JSON or retry |
| Malformed JSON response | Normalize response or fallback to neutral narrator text |
| API rate limit | Exponential backoff in place; user can provide manual script |

**Manual Input Format:** User pastes a valid JSON object with:
```json
{
  "video_title": "Indian Market Daily Update",
  "scenes": [
    {
      "scene_number": 1,
      "title": "Scene Title",
      "voiceover": "Narration text...",
      "caption": "On-screen text"
    },
    ...7 total scenes
  ]
}
```

## 5. Data Resilience & Partial Success

### Symbol-Level Failover
- yfinance fetch has **per-symbol timeout (8 sec)** and **batch timeout (25 sec indices, 20 sec sectors)**
- Delisted symbols (e.g., ^BANKEX, ^NN50.NS) are silently skipped
- Remaining symbols are used; narrator generates neutral messaging for missing winners/losers

### Validation Layer
- Filters out rows with missing `Close` or `Change` values
- Preserves all valid data
- Emits quality flags: `Validation.Skipped_Symbols`, `Validation.Has_Indices`, `Validation.Has_Sectors`

### Scene Planner Resilience
- Core structure: Intro → Market Summary → Indices → Sector Winners → Sector Losers → Market Insight → Closing
- Optional slot (Scene 6) inserts: Institutional Flows, Race Chart, or IPO Tracker if data exists
- Always produces exactly 7 scenes (padded with neutral content if needed)

## 6. Dependencies & Setup

    TA --> Gemini
    Math --> Gemini
    RAG <--> Gemini

    Gemini --> TTS
    TA --> Video
    Assets --> Video
    TTS --> Video

    UI --> Scraper
    UI --> Parser
    Video --> UI
    Gemini -. Chat .-> UI
```

## 3. Core Subsystems

### 3.1 Data Ingestion & Parsing (The Plumbing)
*   **Market Data Connector:** Polls NSE/BSE and platforms like Yahoo Finance (`yfinance`) for real-time OHLCV (Open, High, Low, Close, Volume) data. 
*   **Document Extractor:** Uses `pdfplumber` or `PyPDF2` to extract structured text from CAMS/KFintech statements and Form 16s. Extracts key values (80C, HRA, Gross Income) into a strictly typed Pydantic JSON schema.

### 3.2 Deterministic Engine (The Math)
All numerical calculations are isolated from the LLM to prevent hallucinations.
*   **Tax Optimizer Module:** Implements Indian Income Tax slabs (Old vs. New Regime) programmatically. Uses linear logic to calculate total liability and highlight the $\Delta$ (savings).
*   **FIRE / XIRR Module:** Solves XIRR via the Newton-Raphson method for non-periodic SIP cash flows. Estimates corpus requirements using standard compound interest formulas adjusted for Indian inflation rates.
*   **Signal Generator:** Uses `pandas_ta` to identify actionable stock patterns (e.g., MACD crossovers, Bollinger Band squeezes) to trigger the "Micro Sniper" video generation.

### 3.3 Intelligence Layer (The Brain)
*   **Script Generator (Gemini 3 Flash):** Ingests JSON payloads from the Deterministic Engine and structural instructions to output engaging narrative scripts.
*   **Localization pipeline:** Executes the "Translate-then-Localize" strategy. Converts English scripts into native-sounding Hindi and Hinglish using contextual financial terminology (e.g., Bull Market $\rightarrow$ Tezi).
*   **Contextual RAG:** Embeds fresh regulatory filings and ET articles continuously. Resolves user "Why" queries via similarity search, ensuring every response is cited.

### 3.4 Media Assembly Factory (The Studio)
*   **Audio Synthesis:** Native Indian-accent TTS models transform localized scripts into audio tracks.
*   **Asset Generation:** Tools like `matplotlib` and `plotly` dynamically generate sub-second accurate financial charts mapped to the video's timestamp. Background visuals rendered via Veo or Nano Banana 2.
*   **Video Compositor:** `MoviePy` stitches the TTS audio, background scores (Lyria 3), chart overlays, and animated transitions into a final MP4, optimized to render within the strict 180-second SLA.

---

## 4. Workflows & Execution Paths

### 4.1 Automated Market Wrap Workflow
1.  **Trigger:** End of day cron job (3:45 PM IST).
2.  **Data Fetch:** Pulls Nifty50/Sensex indices, Sectoral Heatmaps, and FII/DII net flows.
3.  **Scripting:** Gemini generates a 60-second summary.
4.  **Localization:** Script is translated into English, Hindi, and Hinglish streams.
5.  **Rendering:** TTS generates voiceovers. `MoviePy` composites the daily charts with voiceovers.
6.  **Distribution:** Final video pushed to Streamlit UI or downstream delivery channels (e.g., WhatsApp).

### 4.2 Tax Wizard Workflow
1.  **Input:** User uploads Form 16 PDF securely.
2.  **Extraction:** OCR/Parser maps variables (Salary, 80C, 80D).
3.  **Computation:** FinMath engine calculates exact liability under both tax regimes.
4.  **Formatting:** Gemini receives the raw numbers and generates a conversational, easy-to-understand response comparing the two regimes.
5.  **Cleanup:** The ephemeral PDF and data are immediately wiped from memory.

---

## 5. Technology Stack Recommendations (48-Hour MVP)

| Layer | Tools & Libraries |
| :--- | :--- |
| **Frontend UI** | Streamlit (Rapid prototyping, Python-native) |
| **Backend & APIs** | FastAPI (Async endpoints, fast execution) |
| **LLM Engine** | Google Gemini 3 Flash (Fast inference, excellent localization) |
| **Video Production** | MoviePy, FFmpeg |
| **Financial Math** | Numpy, Scipy (Newton-Raphson), pandas_ta |
| **Document Parsing** | pdfplumber, PyTesseract |
| **Audio & TTS** | Edge-TTS (Free) or ElevenLabs API (Premium) |
| **Visual Assets** | Matplotlib/Plotly (Charts), Veo/Lyria 3 (GenAI Video/Audio) |

---

## 7. V5 Deployment & Quick Start Guide

### Quick Start (Windows)
1. **Double-click** `run.bat` in the project root
2. Virtual environment auto-creates if needed
3. Dependencies auto-install
4. **Streamlit app launches automatically** at `http://localhost:8501`

### Step-by-Step UI Walkthrough

#### Step 1: Market Data Fetch
```
📊 Click "Fetch Real-Time Market Data"
↓
System fetches 10+ indices + 8+ sectors from yfinance
↓
Dashboard summary shows:
  • Indices count
  • Sectors count  
  • Skipped symbols (delisted)
```

#### Step 2: Script Generation
```
Option A: 🤖 Generate Script (Gemini AI)
  → Gemini creates data-driven narration
  → ✅ Script preview shown
  → Proceed to video generation

Option B: Manual Input (if Gemini fails)
  → Paste JSON script in text area
  → Click "Accept Manual Script"
  → Proceed to video generation
```

#### Step 3: Video Generation
```
🎬 Click "Generate Video"
↓
Real-time progress bar:
  1. Render visuals (scenes)
  2. Synthesize narration (TTS)
  3. Create captions
  4. Composite final video
↓
Outputs:
  • output_macro_wrap_v5.mp4 (final video)
  • output_macro_wrap_v5.metadata.json (publishing info)
```

### Headless Mode (Advanced)
For automated daily runs without UI:
```
set PIPELINE_DRY_RUN=1
py run_pipeline.py
```
Produces script and metadata without video rendering.

### Configuration
Set environment variables in `.env`:
```env
GOOGLE_API_KEY=your_gemini_api_key_here
VIDEO_WIDTH=1080
VIDEO_HEIGHT=1920
VIDEO_FPS=24
VIDEO_MIN_DURATION_SEC=30
VIDEO_MAX_DURATION_SEC=90
TTS_RATE=+25%
OUTPUT_DIR=output
TEMP_DIR=temp_assets
```

### Monitoring & Debugging
- **API Logs:** `output/gemini_log.txt` (prompt + raw response)
- **Script Artifact:** `output/fallback_script_v5.json` (last generated script)
- **Metadata:** `output/output_macro_wrap_v5.metadata.json` (publishing + QA info)

---

## 6. System Constraints & Non-Functional Requirements
1.  **Performance:** Complete rendering of a 60s video must take $< 180$ seconds. Parallel processing with `ffmpeg` threads is required.
2.  **Stateless Privacy:** Financial documents (Form 16/CAS) are loaded into ephemeral `/tmp/` storage, parsed, and immediately `os.remove()`'d. No user persistence for Phase 1.
3.  **Determinism:** Under no circumstances should the LLM calculate percentages or tax slabs. The prompt must explicitly enforce: "You are a formatter; rely solely on the provided JSON numbers."
