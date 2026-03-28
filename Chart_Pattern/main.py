"""
FastAPI Backend for Chart Pattern Intelligence
NSE Stock Pattern Detection with Live Signal Generation
"""

from fastapi import APIRouter, HTTPException, BackgroundTasks, Query
from fastapi.responses import JSONResponse, Response
import json
import threading
import time
import os
from datetime import datetime
from typing import List, Optional, Any
import asyncio
import numpy as np

# Import pattern detection engine
from pattern_engine import scan_universe, scan_stock, NSE_UNIVERSE

# ─────────────────────────────────────────────
# NUMPY TYPE CONVERSION & JSON ENCODER
# ─────────────────────────────────────────────
def convert_numpy_types(obj: Any) -> Any:
    """
    Recursively convert numpy types to native Python types.
    Fixes JSON serialization errors from numpy.bool and other numpy types.
    """
    if isinstance(obj, dict):
        return {key: convert_numpy_types(val) for key, val in obj.items()}
    elif isinstance(obj, (list, tuple)):
        return [convert_numpy_types(item) for item in obj]
    elif isinstance(obj, (np.bool_, bool)):  # Handle both numpy.bool_ and bool
        return bool(obj)
    elif isinstance(obj, (np.integer, np.int64, np.int32, np.int16, np.int8)):
        return int(obj)
    elif isinstance(obj, (np.floating, np.float64, np.float32)):
        return float(obj)
    elif isinstance(obj, np.ndarray):
        return obj.tolist()
    elif hasattr(obj, 'item'):  # Handle numpy scalar types via item() method
        return obj.item()
    else:
        return obj


class NumpyJSONEncoder(json.JSONEncoder):
    """Custom JSON encoder to handle numpy types"""
    def default(self, obj):
        if isinstance(obj, np.ndarray):
            return obj.tolist()
        elif isinstance(obj, (np.bool_, bool)):
            return bool(obj)
        elif isinstance(obj, (np.integer, int)):
            return int(obj)
        elif isinstance(obj, (np.floating, float)):
            return float(obj)
        elif hasattr(obj, 'item'):
            return obj.item()
        return super().default(obj)

# ─────────────────────────────────────────────
# API ROUTER INITIALIZATION
# ─────────────────────────────────────────────
router = APIRouter()
DEMO_MODE = os.getenv("DEMO_MODE", "true").lower() in {"1", "true", "yes"}


def _now_iso() -> str:
    return datetime.utcnow().isoformat() + "Z"

# ─────────────────────────────────────────────
# GLOBAL STATE
# ─────────────────────────────────────────────
class AppState:
    signals = []
    last_scan_time = None
    last_scan_duration = 0
    is_scanning = False
    error_message = None

app_state = AppState()

# ─────────────────────────────────────────────
# BACKGROUND SCANNING
# ─────────────────────────────────────────────
def perform_scan(symbols: Optional[List[str]] = None, max_stocks: int = 20):
    """Background task to scan stocks and update global signals"""
    try:
        app_state.is_scanning = True
        app_state.error_message = None
        
        start_time = time.time()
        print(f"[{datetime.now().isoformat()}] Starting scan...")
        
        # Scan stocks
        if symbols is None:
            symbols = NSE_UNIVERSE[:max_stocks]
        
        results = scan_universe(symbols)
        
        # Convert numpy types to native Python types for JSON serialization
        results = convert_numpy_types(results)
        
        # Update global state
        app_state.signals = results
        app_state.last_scan_time = datetime.now().isoformat()
        app_state.last_scan_duration = round(time.time() - start_time, 2)
        app_state.is_scanning = False
        
        print(f"[{datetime.now().isoformat()}] Scan complete: {len(results)} signals found in {app_state.last_scan_duration}s")
        
        # Save to signals.json for persistence (with numpy encoder as fallback)
        with open('signals.json', 'w') as f:
            json.dump(results, f, indent=2, cls=NumpyJSONEncoder)
        print(f"[{datetime.now().isoformat()}] Signals saved to signals.json")
        
    except Exception as e:
        app_state.is_scanning = False
        app_state.error_message = str(e)
        print(f"[{datetime.now().isoformat()}] Scan error: {e}")


def load_cached_signals():
    """Load signals from signals.json if available"""
    try:
        with open('signals.json', 'r') as f:
            return json.load(f)
    except FileNotFoundError:
        return []


# ─────────────────────────────────────────────
# STARTUP & SHUTDOWN
# ─────────────────────────────────────────────
@router.on_event("startup")
async def startup_event():
    """Load cached signals and trigger auto-scan on startup"""
    print("[STARTUP] Loading cached signals...")
    app_state.signals = load_cached_signals()
    print(f"[STARTUP] Loaded {len(app_state.signals)} cached signals")
    
    # Auto-scan on startup in background
    startup_scan_count = 20 if DEMO_MODE else 50
    print(f"[STARTUP] Triggering initial scan of {startup_scan_count} NSE stocks...")
    thread = threading.Thread(target=perform_scan, args=(None, startup_scan_count), daemon=True)
    thread.start()
    print("[STARTUP] Scan initiated in background...")


# ─────────────────────────────────────────────
# API ROUTES
# ─────────────────────────────────────────────

# The root HTML is now served by the main gateway app, so we remove the / route.


@router.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "signals_count": len(app_state.signals),
        "is_scanning": app_state.is_scanning,
        "last_scan": app_state.last_scan_time,
        "timestamp": _now_iso(),
    }


@router.get("/signals")
async def get_signals(
    direction: Optional[str] = Query(None, description="Filter by 'bullish' or 'bearish'"),
    min_conviction: Optional[int] = Query(None, description="Minimum conviction score (0-100)"),
    sort_by: str = Query("conviction", description="Sort by: conviction, symbol, pattern"),
    lite: bool = Query(False, description="Faster, simplified response for demo mode"),
):
    """
    Get all detected signals with optional filtering
    
    Query Parameters:
    - direction: Filter by bullish/bearish
    - min_conviction: Minimum conviction threshold
    - sort_by: conviction, symbol, or pattern
    """
    # Convert numpy types to native Python types FIRST for proper filtering/sorting
    signals = convert_numpy_types(app_state.signals)
    
    # Apply filters
    if direction and direction in ["bullish", "bearish"]:
        signals = [s for s in signals if s["direction"] == direction]
    
    if min_conviction is not None:
        signals = [s for s in signals if s["conviction"] >= min_conviction]
    
    # Sort results
    if sort_by == "conviction":
        signals = sorted(signals, key=lambda x: x["conviction"], reverse=True)
    elif sort_by == "symbol":
        signals = sorted(signals, key=lambda x: x["symbol"])
    elif sort_by == "pattern":
        signals = sorted(signals, key=lambda x: x["pattern"])

    if lite:
        # Keep payload small for constrained demos.
        signals = signals[:15]
    
    return {
        "total": len(signals),
        "signals": signals,
        "last_scan": app_state.last_scan_time,
        "is_scanning": app_state.is_scanning,
        "lite": lite,
        "timestamp": _now_iso(),
    }


@router.get("/signals/{symbol}")
async def get_signal_by_symbol(symbol: str):
    """Get a specific signal by stock symbol"""
    symbol = symbol.upper()
    
    for signal in app_state.signals:
        if signal["symbol"].upper() == symbol:
            # Convert numpy types to native Python types for JSON serialization
            return convert_numpy_types(signal)
    
    raise HTTPException(status_code=404, detail=f"No signal found for {symbol}")


@router.get("/stats")
async def get_statistics():
    """Get overall market statistics"""
    if not app_state.signals:
        return {
            "total_signals": 0,
            "bullish": 0,
            "bearish": 0,
            "avg_conviction": 0,
            "high_conviction": 0,
        }
    
    bullish = [s for s in app_state.signals if s["direction"] == "bullish"]
    bearish = [s for s in app_state.signals if s["direction"] == "bearish"]
    high_conv = [s for s in app_state.signals if s["conviction"] > 75]
    avg_conv = sum(s["conviction"] for s in app_state.signals) / len(app_state.signals)
    
    return {
        "total_signals": len(app_state.signals),
        "bullish": len(bullish),
        "bearish": len(bearish),
        "avg_conviction": round(avg_conv, 1),
        "high_conviction": len(high_conv),
        "last_scan": app_state.last_scan_time,
        "scan_duration_seconds": app_state.last_scan_duration,
        "timestamp": _now_iso(),
    }


@router.post("/scan")
async def trigger_scan(
    background_tasks: BackgroundTasks,
    max_stocks: int = Query(50),
    lite: bool = Query(False, description="Use faster demo scan limits"),
):
    """
    Trigger a new scan of NSE stocks
    Runs in background and updates global signals
    Scans all 50 stocks by default (production: real-time data)
    """
    if app_state.is_scanning:
        raise HTTPException(status_code=409, detail="Scan already in progress")
    
    if DEMO_MODE or lite:
        max_stocks = min(max_stocks, 15)
    else:
        max_stocks = min(max_stocks, 50)

    # Add background task - bounded scan size for reliability on free-tier infra.
    background_tasks.add_task(perform_scan, None, max_stocks)
    
    return {
        "status": "scanning",
        "message": f"Scan initiated for {max_stocks} NSE stocks",
        "lite": lite,
        "timestamp": _now_iso(),
    }


@router.post("/scan-symbol/{symbol}")
async def scan_single_symbol(symbol: str, background_tasks: BackgroundTasks):
    """Scan a single stock symbol"""
    symbol_with_ns = f"{symbol.upper()}.NS" if not symbol.endswith(".NS") else symbol.upper()
    
    def single_scan():
        try:
            result = scan_stock(symbol_with_ns)
            if result:
                # Convert numpy types to native Python types
                result = convert_numpy_types(result)
                # Update or add signal
                app_state.signals = [s for s in app_state.signals if s["symbol"].upper() != symbol.upper()]
                app_state.signals.append(result)
                # Re-sort by conviction
                app_state.signals.sort(key=lambda x: x["conviction"], reverse=True)
                print(f"Scanned {symbol}: {result['pattern']} ({result['conviction']} conviction)")
            else:
                print(f"No pattern detected for {symbol}")
        except Exception as e:
            print(f"Error scanning {symbol}: {e}")
    
    background_tasks.add_task(single_scan)
    
    return {
        "status": "queued",
        "symbol": symbol.upper(),
        "message": f"Scan queued for {symbol.upper()}",
        "timestamp": _now_iso(),
    }


@router.get("/patterns")
async def get_pattern_list():
    """Get list of all detected patterns"""
    patterns = {}
    for signal in app_state.signals:
        pattern = signal["pattern"]
        if pattern not in patterns:
            patterns[pattern] = {
                "count": 0,
                "bullish": 0,
                "bearish": 0,
                "avg_conviction": 0,
                "symbols": []
            }
        
        patterns[pattern]["count"] += 1
        patterns[pattern]["symbols"].append(signal["symbol"])
        if signal["direction"] == "bullish":
            patterns[pattern]["bullish"] += 1
        else:
            patterns[pattern]["bearish"] += 1
    
    # Calculate averages
    for pattern in patterns:
        matching = [s for s in app_state.signals if s["pattern"] == pattern]
        if matching:
            patterns[pattern]["avg_conviction"] = round(
                sum(s["conviction"] for s in matching) / len(matching), 1
            )
    
    return {"patterns": patterns}


@router.get("/sectors")
async def get_sector_analysis():
    """Get sector-wise signal breakdown"""
    sectors = {}
    for signal in app_state.signals:
        sector = signal.get("sector", "Unknown")
        if sector not in sectors:
            sectors[sector] = {
                "total": 0,
                "bullish": 0,
                "bearish": 0,
                "avg_conviction": 0,
                "stocks": []
            }
        
        sectors[sector]["total"] += 1
        sectors[sector]["stocks"].append(signal["symbol"])
        if signal["direction"] == "bullish":
            sectors[sector]["bullish"] += 1
        else:
            sectors[sector]["bearish"] += 1
    
    # Calculate averages
    for sector in sectors:
        matching = [s for s in app_state.signals if s.get("sector") == sector]
        if matching:
            sectors[sector]["avg_conviction"] = round(
                sum(s["conviction"] for s in matching) / len(matching), 1
            )
    
    return {"sectors": sectors}


@router.get("/status")
async def get_scan_status():
    """Get current scan status and metrics"""
    return {
        "is_scanning": app_state.is_scanning,
        "last_scan_time": app_state.last_scan_time,
        "last_scan_duration": app_state.last_scan_duration,
        "signals_count": len(app_state.signals),
        "error": app_state.error_message,
        "timestamp": _now_iso(),
    }


# ─────────────────────────────────────────────
# (Static files and fallback routing handled by Root App)
# ─────────────────────────────────────────────
