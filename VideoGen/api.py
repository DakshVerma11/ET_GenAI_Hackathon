import os
import time
from datetime import datetime, timezone

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Dict, Any
import asyncio

from VideoGen.src.config import PipelineConfig
from VideoGen.src.extractor import fetch_market_dashboard
from VideoGen.src.ai_engine import generate_structured_script_with_prompt
from VideoGen.src.scene_planner import build_scene_blueprint
from VideoGen.src.insight_engine import compute_market_insights
from VideoGen.src.validation import validate_dashboard
from VideoGen.src.pipeline_runner import run_pipeline

router = APIRouter()

ENABLE_VIDEO = os.getenv("ENABLE_VIDEO", "false").lower() in {"1", "true", "yes"}
DEMO_MODE = os.getenv("DEMO_MODE", "true").lower() in {"1", "true", "yes"}
REQUEST_TIMEOUT_SEC = int(os.getenv("VIDEO_REQUEST_TIMEOUT_SEC", "20"))
DASHBOARD_TTL_SEC = int(os.getenv("VIDEO_DASHBOARD_TTL_SEC", "45"))

_DASHBOARD_CACHE: dict[str, Any] = {"data": None, "fetched_at": 0.0}


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _cached_dashboard() -> dict[str, Any] | None:
    data = _DASHBOARD_CACHE.get("data")
    fetched_at = float(_DASHBOARD_CACHE.get("fetched_at") or 0.0)
    if not data:
        return None
    age = time.time() - fetched_at
    if age <= DASHBOARD_TTL_SEC:
        return data
    return None


async def _refresh_dashboard_cache() -> None:
    dashboard = await asyncio.to_thread(fetch_market_dashboard)
    _DASHBOARD_CACHE["data"] = dashboard
    _DASHBOARD_CACHE["fetched_at"] = time.time()

# ── REQUEST MODELS ──────────────────────
class DashboardRequest(BaseModel):
    dashboard: Dict[str, Any]

class ScriptRequest(BaseModel):
    dashboard: Dict[str, Any]

class VideoJobRequest(BaseModel):
    dashboard: Dict[str, Any]
    script_json: Dict[str, Any]

# ── ENDPOINTS ───────────────────────────
@router.get("/fetch")
async def fetch_data():
    """Fetch live market data (indices, sectors, top movers)."""
    cached = _cached_dashboard()
    if cached is not None:
        return {
            "status": "success",
            "dashboard": cached,
            "message": "Fetching latest market data...",
            "cached": True,
            "timestamp": _utc_now_iso(),
        }

    try:
        dashboard = await asyncio.wait_for(
            asyncio.to_thread(fetch_market_dashboard),
            timeout=REQUEST_TIMEOUT_SEC,
        )
        _DASHBOARD_CACHE["data"] = dashboard
        _DASHBOARD_CACHE["fetched_at"] = time.time()
        return {
            "status": "success",
            "dashboard": dashboard,
            "message": "Fetching latest market data...",
            "cached": False,
            "timestamp": _utc_now_iso(),
        }
    except asyncio.TimeoutError:
        fallback = _DASHBOARD_CACHE.get("data")
        if fallback:
            return {
                "status": "limited",
                "dashboard": fallback,
                "message": "Data temporarily unavailable, retrying recommended",
                "cached": True,
                "timestamp": _utc_now_iso(),
            }
        raise HTTPException(status_code=504, detail="Data temporarily unavailable, retrying recommended")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch market data: {str(e)}")

@router.post("/generate_script")
async def generate_script(req: ScriptRequest):
    """Generate script via Groq AI using fetched dashboard."""
    try:
        dashboard_normalized, skipped = validate_dashboard(req.dashboard)
        insight = compute_market_insights(dashboard_normalized)
        scene_blueprint = build_scene_blueprint(dashboard_normalized, insight)
        expected_scenes = 5 if DEMO_MODE else 7
        
        prompt, script_json, status = await asyncio.wait_for(
            asyncio.to_thread(
                generate_structured_script_with_prompt,
                dashboard_normalized,
                scene_blueprint,
                expected_scenes,
            ),
            timeout=REQUEST_TIMEOUT_SEC,
        )
        
        if status.get("source") == "groq" and status.get("status") == "success":
            return {
                "status": "success",
                "script_json": script_json,
                "prompt": prompt,
                "timestamp": _utc_now_iso(),
            }
        else:
            return {
                "status": "error",
                "message": status.get("reason", "Groq AI generation failed"),
                "prompt": prompt,
                "timestamp": _utc_now_iso(),
            }
    except asyncio.TimeoutError:
        return {
            "status": "limited",
            "message": "Response truncated due to time constraints",
            "timestamp": _utc_now_iso(),
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/render")
@router.post("/generate_video")
async def generate_video(req: VideoJobRequest):
    """Execute the full video pipeline to render the video and return the path."""
    if not ENABLE_VIDEO:
        script_payload = req.script_json if req.script_json else None
        if not script_payload and req.dashboard:
            try:
                dashboard_normalized, _ = validate_dashboard(req.dashboard)
                insight = compute_market_insights(dashboard_normalized)
                scene_blueprint = build_scene_blueprint(dashboard_normalized, insight)
                _, script_payload, _ = await asyncio.wait_for(
                    asyncio.to_thread(
                        generate_structured_script_with_prompt,
                        dashboard_normalized,
                        scene_blueprint,
                        5 if DEMO_MODE else 7,
                    ),
                    timeout=REQUEST_TIMEOUT_SEC,
                )
            except Exception:
                script_payload = None

        return {
            "status": "limited",
            "message": "Video rendering is disabled on cloud deployment due to compute limits. You can generate scripts here and render videos locally for full functionality.",
            "notice": "Video rendering is limited in cloud demo. Full capability available in local or production deployment.",
            "script": script_payload,
            "timestamp": _utc_now_iso(),
        }

    try:
        cfg = PipelineConfig.from_env()
        
        # Run the CPU/IO heavy pipeline off the FastAPI event loop.
        result = await asyncio.wait_for(
            asyncio.to_thread(
                run_pipeline,
                config=cfg,
                script_override=req.script_json,
                dashboard_override=req.dashboard,
            ),
            timeout=max(REQUEST_TIMEOUT_SEC, 25),
        )
        
        if result.get("ok"):
            # Update path to use web path instead of system absolute path if served by FastAPI
            video_path = result.get("video_path")
            return {
                "status": "success",
                "video_path": video_path,
                "metadata_path": result.get("metadata_path"),
                "timestamp": _utc_now_iso(),
            }
        else:
            return {
                "status": "error",
                "error": result.get("error", "Unknown pipeline error"),
                "timestamp": _utc_now_iso(),
            }
    except asyncio.TimeoutError:
        return {
            "status": "limited",
            "message": "Data temporarily unavailable, retrying recommended",
            "timestamp": _utc_now_iso(),
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
