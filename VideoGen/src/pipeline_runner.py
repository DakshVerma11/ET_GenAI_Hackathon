import json
import os
from datetime import datetime
from typing import Dict

from src.ai_engine import generate_structured_script
from src.chart_gen import create_caption_image
from src.config import PipelineConfig
from src.extractor import fetch_market_dashboard
from src.insight_engine import compute_market_insights
from src.tts_engine import generate_audio_from_text
from src.validation import validate_dashboard
from src.video_engine import create_macro_video
from src.scene_planner import build_scene_blueprint
from src.visual_engine import render_dynamic_scenes


def run_pipeline(config: PipelineConfig = None, base_bg: str = "", script_override: Dict = None, dashboard_override: Dict = None) -> Dict:
    config = config or PipelineConfig.from_env()

    os.makedirs(config.temp_dir, exist_ok=True)
    os.makedirs(config.output_dir, exist_ok=True)

    if not base_bg:
        # Optional image, renderer has its own fallback background.
        base_bg = ""

    # Use provided dashboard or fetch fresh data
    if dashboard_override:
        raw_dashboard = dashboard_override
    else:
        raw_dashboard = fetch_market_dashboard()
    
    dashboard, skipped_symbols = validate_dashboard(raw_dashboard)
    insights = compute_market_insights(dashboard)
    scene_blueprint = build_scene_blueprint(dashboard, insights)

    # Use provided script or generate new one
    if script_override:
        script_json = script_override
    else:
        script_json = generate_structured_script(dashboard, scene_blueprint, expected_scenes=7)
    
    parsed_scenes = script_json.get("scenes", [])

    while len(parsed_scenes) < 7:
        parsed_scenes.append(
            {
                "scene_number": len(parsed_scenes) + 1,
                "scene_title": "Scene",
                "voiceover": "Market update is being generated.",
                "caption": "MARKET UPDATE",
            }
        )

    video_path = os.path.join(config.output_dir, config.output_video_name)
    if not config.dry_run:
        scene_paths = render_dynamic_scenes(
            scene_blueprint=scene_blueprint,
            parsed_scenes=parsed_scenes[:7],
            dashboard=dashboard,
            insights=insights,
            temp_dir=config.temp_dir,
            bg_path=base_bg,
        )

        voiceovers = [scene.get("voiceover", "Market conditions are processing.") for scene in parsed_scenes[:7]]
        captions = [
            (scene.get("captions") or [scene.get("caption", "MARKET UPDATE")])[0]
            for scene in parsed_scenes[:7]
        ]

        audio_paths = []
        for i, text in enumerate(voiceovers):
            a_path = os.path.join(config.temp_dir, f"audio_{i}.mp3")
            generate_audio_from_text(text, a_path)
            audio_paths.append(a_path)

        caption_paths = []
        for i, cap_text in enumerate(captions):
            c_path = os.path.join(config.temp_dir, f"cap_{i}.png")
            create_caption_image(cap_text, c_path)
            caption_paths.append(c_path)

        create_macro_video(audio_paths, scene_paths, caption_paths, video_path)

    metadata = {
        "generated_at": datetime.utcnow().isoformat() + "Z",
        "video_path": video_path,
        "video_title": script_json.get("video_title", "Indian Stock Market Daily Update"),
        "format": {
            "width": config.width,
            "height": config.height,
            "aspect_ratio": "9:16",
            "fps": config.fps,
            "duration_target_sec": [config.min_duration_sec, config.max_duration_sec],
        },
        "scene_count": len(parsed_scenes[:7]),
        "scene_blueprint": scene_blueprint,
        "script_source": (script_json.get("meta") or {}).get("source", "unknown"),
        "skipped_symbols": skipped_symbols,
        "provider_meta": raw_dashboard.get("Meta", {}),
        "publishing": {
            "title_options": [
                "India Market Wrap Today",
                "Nifty Sensex Daily Update",
                "Stock Market Closing Bell Brief",
            ],
            "hashtags": ["#StockMarket", "#Nifty50", "#Sensex", "#MarketUpdate", "#IndianMarkets"],
            "description_template": "Daily Indian market update with indices, sectors, volatility, and key insights.",
        },
        "dry_run": config.dry_run,
    }

    metadata_path = os.path.join(config.output_dir, config.output_metadata_name)
    with open(metadata_path, "w", encoding="utf-8") as f:
        json.dump(metadata, f, indent=2)

    fallback_script_path = os.path.join(config.output_dir, config.fallback_script_name)
    with open(fallback_script_path, "w", encoding="utf-8") as f:
        json.dump(script_json, f, indent=2)

    return {
        "ok": True,
        "video_path": video_path,
        "metadata_path": metadata_path,
        "script_path": fallback_script_path,
        "error": None,
    }
