from src.config import PipelineConfig
from src.pipeline_runner import run_pipeline


def main():
    cfg = PipelineConfig.from_env()
    result = run_pipeline(cfg)
    if result.get("ok"):
        print("Pipeline run complete")
        if cfg.dry_run:
            print("Mode: DRY RUN (video render skipped)")
        print(f"Video: {result.get('video_path')}")
        print(f"Metadata: {result.get('metadata_path')}")
    else:
        print("Pipeline run failed")
        print(result)


if __name__ == "__main__":
    main()
