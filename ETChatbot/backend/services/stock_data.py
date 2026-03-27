import yfinance as yf
from datetime import datetime, timedelta

def get_weekly_stock_data(symbols: list[str]) -> str:
    """Fetches the past 1 week closing prices for given Indian stock symbols."""
    if not symbols:
        return "No symbols queried for live data."
    
    mapped_symbols = []
    symbol_map = {}
    for sym in symbols:
        clean = sym.replace("_", "&") # Handle M_M -> M&M
        yf_sym = f"{clean.upper()}.NS"
        mapped_symbols.append(yf_sym)
        symbol_map[yf_sym] = sym

    data_text = []
    end_date = datetime.today()
    start_date = end_date - timedelta(days=7)
    
    # yfinance bulk download might be flaky, fetch individual
    for yf_sym in mapped_symbols:
        try:
            ticker = yf.Ticker(yf_sym)
            hist = ticker.history(start=start_date.strftime("%Y-%m-%d"), end=end_date.strftime("%Y-%m-%d"))
            
            # Fallback to BSE if NSE not found or empty
            if hist.empty:
                yf_sym_bo = yf_sym.replace(".NS", ".BO")
                ticker = yf.Ticker(yf_sym_bo)
                hist = ticker.history(start=start_date.strftime("%Y-%m-%d"), end=end_date.strftime("%Y-%m-%d"))

            if not hist.empty:
                # Format to short date strings (MM-DD: Price)
                prices = hist['Close'].round(2).to_dict()
                price_str = ", ".join([f"{str(k.date())[5:]}: {v}" for k, v in prices.items()])
                data_text.append(f"{symbol_map[yf_sym]} (1-week closes): {price_str}")
            else:
                data_text.append(f"{symbol_map[yf_sym]}: No recent data.")
        except Exception:
            pass # Silently skip failures for MVP to avoid breaking prompt
            
    if not data_text:
        return "No recent market data could be loaded."
        
    return "\n".join(data_text)
