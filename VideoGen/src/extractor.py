import yfinance as yf
import pandas as pd
import concurrent.futures
from typing import Dict, List, Optional

INDICES = {
    "Sensex": "^BSESN",
    "Nifty 50": "^NSEI",
    "Nifty 100": "^CNX100",
    "Nifty 500": "^CRSLDX",
    "BSE 500": "BSE-500.BO",
    "Nifty Bank": "^NSEBANK",
    "Nifty Fin Service": "NIFTY_FIN_SERVICE.NS",
    "India VIX": "^INDIAVIX"
}

SECTORS = {
    "IT": "^CNXIT",
    "Auto": "^CNXAUTO",
    "FMCG": "^CNXFMCG",
    "Metal": "^CNXMETAL",
    "Pharma": "^CNXPHARMA",
    "Energy": "^CNXENERGY",
    "Realty": "^CNXREALTY",
    "Infra": "^CNXINFRA"
}

def _fetch_symbol(name, ticker) -> dict:
    try:
        t = yf.Ticker(ticker)
        hist = t.history(period="5d")
        if len(hist) >= 2:
            close = hist['Close'].iloc[-1]
            prev_close = hist['Close'].iloc[-2]
            change_pct = ((close - prev_close) / prev_close) * 100
            return {
                "Name": name,
                "Close": round(float(close), 2),
                "Change": round(float(change_pct), 2),
                "Trend": "Up" if change_pct >= 0 else "Down"
            }
    except Exception:
        pass
    return None


def _safe_future_result(future, timeout_sec: float = 8.0):
    try:
        return future.result(timeout=timeout_sec)
    except Exception:
        return None


def _collect_results_with_timeout(
    futures_map: Dict,
    bucket_name: str,
    timeout_total_sec: float,
    data_out: List[Dict],
    skipped_symbols: List[str],
):
    done, not_done = concurrent.futures.wait(
        futures_map.keys(), timeout=timeout_total_sec, return_when=concurrent.futures.ALL_COMPLETED
    )

    for fut in done:
        res = _safe_future_result(fut)
        if res:
            data_out.append(res)
        else:
            skipped_symbols.append(f"{bucket_name}:{futures_map[fut]}")

    for fut in not_done:
        skipped_symbols.append(f"{bucket_name}:{futures_map[fut]}")
        fut.cancel()


def _top_sector_buckets(sectors_data: List[Dict]):
    sectors_data.sort(key=lambda x: x['Change'], reverse=True)
    top_3_up = [s for s in sectors_data if s['Change'] > 0][:3]
    top_3_down = [s for s in reversed(sectors_data) if s['Change'] < 0][:3]
    return top_3_up, top_3_down

def fetch_market_dashboard() -> dict:
    """Fetches indices and sectors concurrently, tolerating missing symbols and partial failures."""
    indices_data = []
    sectors_data = []
    skipped_symbols: List[str] = []
    provider_health = {
        "primary": "yfinance",
        "status": "ok",
    }
    
    with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
        idx_futures = {executor.submit(_fetch_symbol, k, v): k for k, v in INDICES.items()}
        _collect_results_with_timeout(
            futures_map=idx_futures,
            bucket_name="index",
            timeout_total_sec=25.0,
            data_out=indices_data,
            skipped_symbols=skipped_symbols,
        )
            
        sec_futures = {executor.submit(_fetch_symbol, k, v): k for k, v in SECTORS.items()}
        _collect_results_with_timeout(
            futures_map=sec_futures,
            bucket_name="sector",
            timeout_total_sec=20.0,
            data_out=sectors_data,
            skipped_symbols=skipped_symbols,
        )

    # Sort indices to maintain display order
    order = list(INDICES.keys())
    indices_data.sort(key=lambda x: order.index(x['Name']) if x['Name'] in order else 99)
    
    top_3_up, top_3_down = _top_sector_buckets(sectors_data)

    if not indices_data and not sectors_data:
        provider_health["status"] = "degraded"
    
    return {
        "Indices": indices_data,
        "Sectors": {
            "Top_Gainers": top_3_up,
            "Top_Losers": top_3_down,
            "All": sectors_data
        },
        "Flows": {
            "FII_Net": None,
            "DII_Net": None,
        },
        "IPO": [],
        "Meta": {
            "Skipped_Symbols": skipped_symbols,
            "Provider_Health": provider_health,
        },
    }
