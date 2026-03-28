"""
ET Markets AI Intelligence Platform — Unified Gateway
Single FastAPI app on port 8000 that integrates all intelligence modules natively.
Modules: Chart Pattern, Market ChatGPT, AI Video Engine, Opportunity Radar
"""

from contextlib import asynccontextmanager
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import FileResponse, RedirectResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
import sys
import logging
from pathlib import Path

ROOT = Path(__file__).parent.resolve()
logger = logging.getLogger(__name__)

# ── sys.path injection so sub-module internal imports work from root ───────
sys.path.insert(0, str(ROOT / "Chart_Pattern"))
sys.path.insert(0, str(ROOT / "ETChatbot"))
sys.path.insert(0, str(ROOT / "VideoGen"))
sys.path.insert(0, str(ROOT / "Radar"))      # Radar uses bare module names

# ── Sub-module routers ──────────────────────────────────────────────────
from Chart_Pattern.main import router as chart_pattern_router
from ETChatbot.backend.main import router as market_chat_router
from VideoGen.api import router as video_gen_router
from routes import router as radar_router   # Radar (bare import via sys.path)
from pipeline import Pipeline               # Radar pipeline
from init_db import init_db                 # Radar DB init
from websocket import broadcaster          # Radar WS broadcaster

# ── Lifespan: start/stop Radar background pipeline ─────────────────────────
radar_pipeline = Pipeline()

@asynccontextmanager
async def lifespan(app: FastAPI):
    # ── Startup ──
    try:
        await init_db()
        logger.info("Radar: Database initialized")
    except Exception as e:
        logger.error(f"Radar: DB init failed — {e}")
    try:
        await radar_pipeline.start()
        logger.info("Radar: Pipeline started")
    except Exception as e:
        logger.error(f"Radar: Pipeline start failed — {e}")
    yield
    # ── Shutdown ──
    await radar_pipeline.stop()
    logger.info("Radar: Pipeline stopped")


app = FastAPI(
    title="ET Markets AI Gateway",
    docs_url=None,
    redoc_url=None,
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── API Routers ─────────────────────────────────────────────────────────
app.include_router(chart_pattern_router, prefix="/api/chart")
app.include_router(market_chat_router,   prefix="/api/chat")
app.include_router(video_gen_router,     prefix="/api/video")
app.include_router(radar_router,         prefix="/api/radar")   # Opportunity Radar REST

# ── Radar WebSocket (live signal feed) ───────────────────────────────────
@app.websocket("/api/radar/ws/feed")
async def radar_ws(websocket: WebSocket):
    await broadcaster.connect(websocket)
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        await broadcaster.disconnect(websocket)
    except Exception as e:
        logger.error(f"Radar WS error: {e}")
        await broadcaster.disconnect(websocket)

# ── Page routes ─────────────────────────────────────────────────────────────
@app.get("/")
async def home():
    return FileResponse(str(ROOT / "index.html"), media_type="text/html")

@app.get("/chart-pattern")
async def chart_pattern_redir():
    return RedirectResponse("/chart-pattern/")

@app.get("/market-chat")
async def market_chat_redir():
    return RedirectResponse("/market-chat/")

@app.get("/video")
async def video_redir():
    return RedirectResponse("/video/")

@app.get("/radar")
async def radar_redir():
    return RedirectResponse("/radar/")

# ── Static mounts ─────────────────────────────────────────────────────────
outputs_path = ROOT / "VideoGen" / "outputs"
outputs_path.mkdir(parents=True, exist_ok=True)
app.mount("/video_output",   StaticFiles(directory=str(outputs_path)), name="video_output")
app.mount("/chart-pattern/", StaticFiles(directory=str(ROOT / "Chart_Pattern"), html=True), name="chart_pattern_frontend")
app.mount("/market-chat/",   StaticFiles(directory=str(ROOT / "ETChatbot" / "frontend"), html=True), name="market_chat_frontend")
app.mount("/video/",         StaticFiles(directory=str(ROOT / "VideoGen" / "frontend"), html=True), name="video_frontend")
app.mount("/radar/",         StaticFiles(directory=str(ROOT / "Radar"), html=True), name="radar_frontend")

if __name__ == "__main__":
    import uvicorn
    print("=" * 60)
    print("  ET Markets AI Intelligence Platform — Unified")
    print("  Starting natively on: http://localhost:8000")
    print("=" * 60)
    uvicorn.run("main:app", host="0.0.0.0", port=8000, log_level="info", reload=True)
