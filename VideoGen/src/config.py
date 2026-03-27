import os
from dataclasses import dataclass


@dataclass(frozen=True)
class PipelineConfig:
    width: int = 1080
    height: int = 1920
    fps: int = 24
    min_duration_sec: int = 30
    max_duration_sec: int = 90
    tts_rate: str = "+25%"
    output_dir: str = "output"
    temp_dir: str = "temp_assets"
    output_video_name: str = "output_macro_wrap_v5.mp4"
    output_metadata_name: str = "output_macro_wrap_v5.metadata.json"
    fallback_script_name: str = "fallback_script_v5.json"
    dry_run: bool = False

    @staticmethod
    def from_env() -> "PipelineConfig":
        return PipelineConfig(
            width=int(os.getenv("VIDEO_WIDTH", "1080")),
            height=int(os.getenv("VIDEO_HEIGHT", "1920")),
            fps=int(os.getenv("VIDEO_FPS", "24")),
            min_duration_sec=int(os.getenv("VIDEO_MIN_DURATION_SEC", "30")),
            max_duration_sec=int(os.getenv("VIDEO_MAX_DURATION_SEC", "90")),
            tts_rate=os.getenv("TTS_RATE", "+25%"),
            output_dir=os.getenv("OUTPUT_DIR", "output"),
            temp_dir=os.getenv("TEMP_DIR", "temp_assets"),
            output_video_name=os.getenv("OUTPUT_VIDEO_NAME", "output_macro_wrap_v5.mp4"),
            output_metadata_name=os.getenv("OUTPUT_METADATA_NAME", "output_macro_wrap_v5.metadata.json"),
            fallback_script_name=os.getenv("FALLBACK_SCRIPT_NAME", "fallback_script_v5.json"),
            dry_run=os.getenv("PIPELINE_DRY_RUN", "0").lower() in {"1", "true", "yes"},
        )
