from typing import Dict, List, Tuple


def _is_number(value) -> bool:
    try:
        return value is not None and float(value) == float(value)
    except Exception:
        return False


def validate_dashboard(dashboard: Dict) -> Tuple[Dict, List[str]]:
    """Normalize dashboard payload and remove unusable rows while preserving partial data."""
    skipped: List[str] = []

    indices_in = dashboard.get("Indices", []) or []
    sectors_in = (dashboard.get("Sectors", {}) or {}).get("All", []) or []

    def _clean_row(row: Dict, bucket: str):
        name = row.get("Name", "Unknown")
        close = row.get("Close")
        change = row.get("Change")
        if not _is_number(close) or not _is_number(change):
            skipped.append(f"{bucket}:{name}")
            return None
        return {
            "Name": name,
            "Close": round(float(close), 2),
            "Change": round(float(change), 2),
            "Trend": "Up" if float(change) >= 0 else "Down",
        }

    clean_indices = [r for r in (_clean_row(x, "index") for x in indices_in) if r]
    clean_sectors_all = [r for r in (_clean_row(x, "sector") for x in sectors_in) if r]

    clean_sectors_all.sort(key=lambda x: x["Change"], reverse=True)
    top_gainers = [s for s in clean_sectors_all if s["Change"] > 0][:3]
    top_losers = [s for s in reversed(clean_sectors_all) if s["Change"] < 0][:3]

    normalized = {
        "Indices": clean_indices,
        "Sectors": {
            "Top_Gainers": top_gainers,
            "Top_Losers": top_losers,
            "All": clean_sectors_all,
        },
        "Flows": dashboard.get("Flows", {"FII_Net": None, "DII_Net": None}),
        "IPO": dashboard.get("IPO", []),
        "Validation": {
            "Skipped": skipped,
            "Has_Indices": bool(clean_indices),
            "Has_Sectors": bool(clean_sectors_all),
        },
    }
    return normalized, skipped
