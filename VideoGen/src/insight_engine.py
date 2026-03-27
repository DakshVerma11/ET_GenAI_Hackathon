from typing import Dict


def compute_market_insights(dashboard: Dict) -> Dict:
    indices = dashboard.get("Indices", [])
    sectors = (dashboard.get("Sectors", {}) or {}).get("All", [])
    top_gainers = (dashboard.get("Sectors", {}) or {}).get("Top_Gainers", [])
    top_losers = (dashboard.get("Sectors", {}) or {}).get("Top_Losers", [])

    breadth_up = sum(1 for i in indices if i.get("Change", 0) > 0)
    breadth_down = sum(1 for i in indices if i.get("Change", 0) < 0)

    if breadth_up > breadth_down:
        market_trend = "Bullish"
    elif breadth_down > breadth_up:
        market_trend = "Bearish"
    else:
        market_trend = "Mixed"

    vix = next((x for x in indices if x.get("Name") == "India VIX"), None)
    vix_change = (vix or {}).get("Change")
    if isinstance(vix_change, (int, float)):
        volatility = "Rising" if vix_change > 0 else "Cooling"
    else:
        volatility = "Unknown"

    biggest_index_move = max(indices, key=lambda x: abs(float(x.get("Change", 0))), default=None)
    notable_sector = max(sectors, key=lambda x: abs(float(x.get("Change", 0))), default=None)

    return {
        "market_trend": market_trend,
        "breadth": {
            "up": breadth_up,
            "down": breadth_down,
        },
        "volatility": volatility,
        "vix": vix,
        "top_gainers": top_gainers,
        "top_losers": top_losers,
        "biggest_index_move": biggest_index_move,
        "notable_sector": notable_sector,
    }
