"""
Opportunity Radar — FastAPI Application

Main entry point for the real-time NSE trading signal radar system.
Combines scheduled fetching (APScheduler), NLP analysis (Claude), 
real-time updates (WebSocket), and interactive dashboard.

Run: uvicorn api:app --reload --host 0.0.0.0 --port 8000
"""

import logging
import sys
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from rich.console import Console

from settings import settings
from pipeline import Pipeline

# ── Configure logging ──────────────────────────────────────────────────────────
logging.basicConfig(
    level=settings.log_level.upper(),
    format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)
logger = logging.getLogger(__name__)
console = Console()

# ── Pipeline instance ──────────────────────────────────────────────────────────
pipeline = Pipeline()


# ── Lifespan context manager ───────────────────────────────────────────────────
@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Startup: Initialize database and start all scheduled fetchers.
    Shutdown: Gracefully stop pipeline and close connections.
    """
    console.print("[bold cyan]Opportunity Radar starting up...[/bold cyan]")
    
    # Initialize database
    try:
        from init_db import init_db
        await init_db()
        console.print("[green]Database initialized[/green]")
    except Exception as e:
        console.print(f"[red]Database init failed: {e}[/red]")
        raise

    # Start the pipeline (fetchers + scheduler)
    try:
        await pipeline.start()
        console.print("[green]Pipeline started[/green]")
    except Exception as e:
        console.print(f"[red]Pipeline start failed: {e}[/red]")
        raise

    yield

    # Shutdown
    console.print("[yellow]Shutting down...[/yellow]")
    await pipeline.stop()
    console.print("[green]Shutdown complete[/green]")


# ── FastAPI App ────────────────────────────────────────────────────────────────
app = FastAPI(
    title="Opportunity Radar",
    description="Real-time NSE trading signal radar via NLP + anomaly detection",
    version="1.0.0",
    docs_url="/docs",
    openapi_url="/openapi.json",
    lifespan=lifespan,
)

# ── CORS Middleware ────────────────────────────────────────────────────────────
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Include API routes ─────────────────────────────────────────────────────────
from routes import router as api_router
app.include_router(api_router, prefix="/api")


# ── WebSocket: Real-time signal feed ───────────────────────────────────────────
@app.websocket("/ws/feed")
async def websocket_feed(websocket: WebSocket):
    """
    WebSocket endpoint for real-time signal feed.
    
    Clients connect and receive:
    - New signals as they're generated
    - Sector heatmap updates
    - Pipeline status/health
    """
    await pipeline.broadcaster.connect(websocket)
    try:
        while True:
            # Receive any messages from client (for future interactive features)
            data = await websocket.receive_text()
            # Echo or handle commands if needed
    except WebSocketDisconnect:
        await pipeline.broadcaster.disconnect(websocket)
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
        await pipeline.broadcaster.disconnect(websocket)


# ── Health & Status Endpoints ──────────────────────────────────────────────────

@app.get("/health")
async def health():
    """Health check endpoint."""
    return {
        "status": "ok",
        "ws_connections": pipeline.broadcaster.connection_count,
        "pipeline_running": pipeline.scheduler.running if hasattr(pipeline, "scheduler") else False,
    }


@app.get("/status")
async def status():
    """Pipeline status and metrics."""
    return {
        "status": "running",
        "scheduler_running": pipeline.scheduler.running if hasattr(pipeline, "scheduler") else False,
        "ws_connections": pipeline.broadcaster.connection_count,
        "database": settings.database_url,
        "fetch_intervals": {
            "filings": settings.fetch_interval_filings,
            "bulk": settings.fetch_interval_bulk,
            "insider": settings.fetch_interval_insider,
            "indices": settings.fetch_interval_indices,
        },
    }


# ── Serve index.html ───────────────────────────────────────────────────────────

@app.get("/")
async def root():
    """Serve the main dashboard UI."""
    index_path = Path(__file__).parent / "index.html"
    if index_path.exists():
        return FileResponse(index_path, media_type="text/html")
    return {"error": "index.html not found"}


# ── Fallback for static assets ─────────────────────────────────────────────────
# If you add static files (CSS, JS, images), mount here:
# app.mount("/static", StaticFiles(directory="static"), name="static")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "api:app",
        host=settings.host,
        port=settings.port,
        reload=True,
        log_level=settings.log_level,
    )
