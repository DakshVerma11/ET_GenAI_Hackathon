from typing import Dict, List


def build_scene_blueprint(dashboard: Dict, insights: Dict) -> List[Dict]:
    """Build a dynamic 7-scene plan with a stable core plus one highest-priority optional scene."""
    flows = dashboard.get("Flows", {}) or {}
    ipo = dashboard.get("IPO", []) or []

    core = [
        {"scene_type": "intro", "title": "Intro Hook"},
        {"scene_type": "market_summary", "title": "Market Summary"},
        {"scene_type": "major_indices", "title": "Major Index Performance"},
        {"scene_type": "sector_winners", "title": "Sector Winners"},
        {"scene_type": "sector_losers", "title": "Sector Losers"},
        {"scene_type": "market_insight", "title": "Market Insight"},
        {"scene_type": "closing", "title": "Closing Summary"},
    ]

    optional = []
    if flows.get("FII_Net") is not None or flows.get("DII_Net") is not None:
        optional.append({"scene_type": "institutional_flows", "title": "Institutional Flows"})

    optional.append({"scene_type": "race_chart", "title": "Race Chart"})

    if ipo:
        optional.append({"scene_type": "ipo_tracker", "title": "IPO Tracker"})

    selected = list(core)
    if optional:
        selected[5] = optional[0]

    for idx, sc in enumerate(selected, start=1):
        sc["scene_number"] = idx
        sc["market_trend"] = insights.get("market_trend", "Mixed")
    return selected
