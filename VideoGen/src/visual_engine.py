import os
from typing import Dict, List

from VideoGen.src.chart_gen import (
    generate_scene_1_intro,
    generate_scene_2_indices,
    generate_scene_3_trend,
    generate_scene_4_winners,
    generate_scene_5_losers,
    generate_scene_6_insight,
    generate_scene_7_outro,
    generate_scene_market_summary,
    generate_scene_institutional_flows,
    generate_scene_race_chart,
    generate_scene_ipo_tracker,
)


def render_scene(scene_type: str, scene_data: Dict, dashboard: Dict, insights: Dict, bg_path: str, output_path: str) -> str:
    if scene_type == "intro":
        return generate_scene_1_intro(scene_data, bg_path, output_path)
    if scene_type == "market_summary":
        return generate_scene_market_summary(scene_data, insights, bg_path, output_path)
    if scene_type == "major_indices":
        return generate_scene_2_indices(scene_data, dashboard.get("Indices", []), bg_path, output_path)
    if scene_type == "sector_winners":
        return generate_scene_4_winners(scene_data, dashboard.get("Sectors", {}), bg_path, output_path)
    if scene_type == "sector_losers":
        return generate_scene_5_losers(scene_data, dashboard.get("Sectors", {}), bg_path, output_path)
    if scene_type == "institutional_flows":
        return generate_scene_institutional_flows(scene_data, dashboard.get("Flows", {}), bg_path, output_path)
    if scene_type == "race_chart":
        return generate_scene_race_chart(scene_data, dashboard.get("Sectors", {}), bg_path, output_path)
    if scene_type == "ipo_tracker":
        return generate_scene_ipo_tracker(scene_data, dashboard.get("IPO", []), bg_path, output_path)
    if scene_type == "market_insight":
        return generate_scene_6_insight(scene_data, bg_path, output_path)
    if scene_type == "closing":
        return generate_scene_7_outro(scene_data, bg_path, output_path)

    # Fallback to trend scene for unknown types.
    return generate_scene_3_trend(scene_data, dashboard.get("Indices", []), bg_path, output_path)


def render_dynamic_scenes(scene_blueprint: List[Dict], parsed_scenes: List[Dict], dashboard: Dict, insights: Dict, temp_dir: str, bg_path: str) -> List[str]:
    paths: List[str] = []

    parsed_by_num = {
        int(scene.get("scene_number", idx + 1)): scene
        for idx, scene in enumerate(parsed_scenes)
        if isinstance(scene, dict)
    }

    for idx, item in enumerate(scene_blueprint, start=1):
        scene_num = int(item.get("scene_number", idx))
        scene_type = item.get("scene_type", "market_insight")
        scene_data = dict(parsed_by_num.get(scene_num, {}))
        scene_data.setdefault("scene_title", item.get("title", f"Scene {scene_num}"))

        out_path = os.path.join(temp_dir, f"s{idx}.png")
        paths.append(render_scene(scene_type, scene_data, dashboard, insights, bg_path, out_path))

    return paths
