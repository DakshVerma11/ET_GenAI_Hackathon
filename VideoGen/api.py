from fastapi import APIRouter, HTTPException, BackgroundTasks
from pydantic import BaseModel
from typing import Optional, Dict, Any, List
import asyncio

from VideoGen.src.config import PipelineConfig
from VideoGen.src.extractor import fetch_market_dashboard
from VideoGen.src.ai_engine import generate_structured_script_with_prompt
from VideoGen.src.scene_planner import build_scene_blueprint
from VideoGen.src.insight_engine import compute_market_insights
from VideoGen.src.validation import validate_dashboard
from VideoGen.src.pipeline_runner import run_pipeline

router = APIRouter()

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
    try:
        dashboard = fetch_market_dashboard()
        return {"status": "success", "dashboard": dashboard}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch market data: {str(e)}")

@router.post("/generate_script")
async def generate_script(req: ScriptRequest):
    """Generate script via Groq AI using fetched dashboard."""
    try:
        dashboard_normalized, skipped = validate_dashboard(req.dashboard)
        insight = compute_market_insights(dashboard_normalized)
        scene_blueprint = build_scene_blueprint(dashboard_normalized, insight)
        
        prompt, script_json, status = generate_structured_script_with_prompt(
            dashboard_normalized, scene_blueprint, expected_scenes=7
        )
        
        if status.get("source") == "groq" and status.get("status") == "success":
            return {
                "status": "success",
                "script_json": script_json,
                "prompt": prompt
            }
        else:
            return {
                "status": "error",
                "message": status.get("reason", "Groq AI generation failed"),
                "prompt": prompt
            }
            
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/generate_video")
async def generate_video(req: VideoJobRequest):
    """Execute the full video pipeline to render the video and return the path."""
    try:
        cfg = PipelineConfig.from_env()
        
        # Run the CPU/IO heavy pipeline off the FastAPI event loop.
        result = await asyncio.to_thread(
            run_pipeline,
            config=cfg,
            script_override=req.script_json,
            dashboard_override=req.dashboard,
        )
        
        if result.get("ok"):
            # Update path to use web path instead of system absolute path if served by FastAPI
            video_path = result.get("video_path")
            return {
                "status": "success",
                "video_path": video_path,
                "metadata_path": result.get("metadata_path")
            }
        else:
            return {
                "status": "error",
                "error": result.get("error", "Unknown pipeline error")
            }
            
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
