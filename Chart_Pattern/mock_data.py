"""
Generate realistic NSE signal data for demo
Using actual approximate price levels for major NSE stocks
"""
import json
import random
import math

random.seed(42)

# Realistic NSE stock data (approximate current prices, March 2025)
NSE_STOCKS = {
    "RELIANCE": {"price": 2847, "sector": "Energy"},
    "TCS": {"price": 3921, "sector": "IT"},
    "INFY": {"price": 1589, "sector": "IT"},
    "HDFCBANK": {"price": 1712, "sector": "Banking"},
    "ICICIBANK": {"price": 1243, "sector": "Banking"},
    "SBIN": {"price": 812, "sector": "Banking"},
    "WIPRO": {"price": 478, "sector": "IT"},
    "BAJFINANCE": {"price": 7124, "sector": "Finance"},
    "TITAN": {"price": 3456, "sector": "Consumer"},
    "ITC": {"price": 445, "sector": "FMCG"},
    "TATAMOTORS": {"price": 987, "sector": "Auto"},
    "MARUTI": {"price": 11234, "sector": "Auto"},
    "SUNPHARMA": {"price": 1634, "sector": "Pharma"},
    "AXISBANK": {"price": 1167, "sector": "Banking"},
    "LT": {"price": 3678, "sector": "Infrastructure"},
    "HINDUNILVR": {"price": 2398, "sector": "FMCG"},
    "ADANIENT": {"price": 2934, "sector": "Conglomerate"},
    "BHARTIARTL": {"price": 1678, "sector": "Telecom"},
    "KOTAKBANK": {"price": 1892, "sector": "Banking"},
    "TECHM": {"price": 1456, "sector": "IT"},
}

PATTERNS = [
    {"name": "Bull Flag", "direction": "bullish", "base_conviction": 74, "success_rate": 0.75},
    {"name": "Double Bottom", "direction": "bullish", "base_conviction": 71, "success_rate": 0.72},
    {"name": "Ascending Triangle", "direction": "bullish", "base_conviction": 68, "success_rate": 0.70},
    {"name": "Inverse Head & Shoulders", "direction": "bullish", "base_conviction": 77, "success_rate": 0.74},
    {"name": "Support Breakout", "direction": "bullish", "base_conviction": 69, "success_rate": 0.68},
    {"name": "RSI Divergence (Bullish)", "direction": "bullish", "base_conviction": 63, "success_rate": 0.65},
    {"name": "Head & Shoulders", "direction": "bearish", "base_conviction": 73, "success_rate": 0.73},
    {"name": "Double Top", "direction": "bearish", "base_conviction": 70, "success_rate": 0.71},
    {"name": "Descending Triangle", "direction": "bearish", "base_conviction": 66, "success_rate": 0.69},
    {"name": "Bear Flag", "direction": "bearish", "base_conviction": 72, "success_rate": 0.73},
    {"name": "Resistance Breakdown", "direction": "bearish", "base_conviction": 67, "success_rate": 0.67},
    {"name": "RSI Divergence (Bearish)", "direction": "bearish", "base_conviction": 61, "success_rate": 0.63},
]

INSIGHTS = {
    "Bull Flag": "Strong rally of {gain}% over 8 sessions followed by tight consolidation on declining volume ({vol_ratio}x avg). Coiling for continuation. This pattern on {name} has resolved bullishly {win_pct}% of the time in the last 3 years ({occ} occurrences) with an avg move of {avg_gain}% over {avg_days} days. MACD histogram turning positive. RSI at {rsi} with room to run. Key breakout level: ₹{key_level:,.0f} — watch for volume surge above 1.5x average to confirm.",
    "Double Bottom": "Price tested ₹{key_level:,.0f} support twice ({occ} weeks apart) and bounced both times — classic W-formation. Second bounce stronger with {vol_ratio}x volume surge. On {name}, Double Bottoms have led to meaningful rallies {win_pct}% of the time ({occ} instances). RSI showed bullish divergence at the second low (RSI: {rsi}). Neckline breakout above ₹{neckline:,.0f} triggers the pattern with measured target of ₹{target:,.0f}.",
    "Ascending Triangle": "Flat resistance at ₹{key_level:,.0f} tested 3 times while support rises — a classic coil. Volume contracting to {vol_ratio}x average signals buyer accumulation. {name} has broken out of Ascending Triangles {win_pct}% of the time ({occ} occasions) with avg gain of {avg_gain}% in {avg_days} days. RSI at {rsi} — neutral with upward bias. Breakout above ₹{key_level:,.0f} on volume > 1.8x average would be high-conviction entry.",
    "Inverse Head & Shoulders": "Textbook reversal forming after prolonged downtrend. Left shoulder at ₹{stop_loss:,.0f}, head at lower low, right shoulder matching left — classic reversal geometry. Volume declined on head formation and is rising on right shoulder ({vol_ratio}x avg). {name} has reversed {win_pct}% of the time after this pattern ({occ} instances). RSI divergence at the head adds conviction. Neckline break above ₹{neckline:,.0f} is the trigger.",
    "Support Breakout": "{name} broke above key resistance ₹{key_level:,.0f} — a level that rejected price {occ} times over 4 months. Breakout session volume was {vol_ratio}x the 20-day average — strong institutional participation. Former resistance becomes new support. NSE breakout patterns carry {win_pct}% success rate when confirmed with volume. RSI at {rsi} with bullish MACD crossover. Measured target: ₹{target:,.0f}.",
    "RSI Divergence (Bullish)": "Price made a lower low vs prior swing but RSI registered a higher low — classic bullish momentum divergence signaling seller exhaustion. RSI at {rsi} — approaching oversold territory. This divergence has preceded meaningful bounces on {name} {win_pct}% of the time ({occ} instances). Volume pickup on last 2 sessions ({vol_ratio}x avg). Watch for bullish engulfing candle as entry trigger. Stop below the most recent swing low.",
    "Head & Shoulders": "Classic reversal pattern completing after strong uptrend. Left shoulder, head (highest point at ₹{key_level:,.0f}), and right shoulder forming — symmetrical geometry with neckline at ₹{neckline:,.0f}. Volume declined on head rally and on right shoulder ({vol_ratio}x avg) — distribution in progress. On {name}, H&S has led to declines {win_pct}% of the time ({occ} instances). RSI at {rsi} showing negative divergence. Neckline break confirms — target ₹{target:,.0f}.",
    "Double Top": "{name} tested ₹{key_level:,.0f} resistance twice and failed both times — M-formation signals supply overhang. Second top formed on lower volume ({vol_ratio}x avg) vs first top — clear distribution signal. Double Tops on {name} resolved bearishly {win_pct}% of the time ({occ} occurrences). RSI at {rsi} showing bearish divergence between the two tops. Valley neckline at ₹{neckline:,.0f} — break below confirms pattern with target ₹{target:,.0f}.",
    "Descending Triangle": "Rising supply meets flat demand — compression signaling potential breakdown. Lower highs forming a descending trendline while ₹{key_level:,.0f} support holds flat. Volume contracting ({vol_ratio}x avg) — typical pre-breakdown pattern. {name} has broken down from Descending Triangles {win_pct}% of the time ({occ} instances). RSI at {rsi} trending down with bearish MACD histogram. Break below ₹{key_level:,.0f} on volume > 1.5x average is the trigger.",
    "Bear Flag": "Sharp decline of {gain}% in 7 sessions followed by weak, low-volume bounce ({vol_ratio}x avg) — textbook Bear Flag. Rally retracing only 38% of decline — weak buying. {name}'s Bear Flags have resolved to the downside {win_pct}% of the time ({occ} instances) with avg decline of {avg_gain}% in {avg_days} days. RSI at {rsi} — attempted recovery failed at 50 level. Watch for breakdown below ₹{key_level:,.0f} with volume confirmation.",
    "Resistance Breakdown": "{name} broke below key support ₹{key_level:,.0f} that had held for 6+ months. Breakdown volume was {vol_ratio}x 20-day average — aggressive selling. Former support becomes resistance — any bounce to ₹{key_level:,.0f} is a potential short entry. NSE breakdown patterns carry {win_pct}% follow-through rate when confirmed with volume. RSI at {rsi} below 40 — bearish momentum confirmed. Target: ₹{target:,.0f}.",
    "RSI Divergence (Bearish)": "Price made a higher high vs prior swing but RSI registered a lower high — bearish momentum divergence signaling buyer exhaustion at current levels. RSI at {rsi} — overbought and declining. This divergence has preceded meaningful pullbacks on {name} {win_pct}% of the time ({occ} instances). Watch for bearish engulfing candle as entry trigger. Stop above the most recent swing high at ₹{key_level:,.0f}.",
}

def generate_price_history(base_price, pattern, direction):
    """Generate realistic price history matching the pattern"""
    prices = []
    n = 60
    
    if pattern == "Bull Flag":
        for i in range(n):
            if i < 15:
                p = base_price * (0.88 + i * 0.008)
            elif i < 40:
                noise = random.uniform(-0.005, 0.003)
                p = base_price * (0.97 + noise)
            else:
                p = base_price * (0.97 + (i - 40) * 0.001 + random.uniform(-0.003, 0.005))
            prices.append(round(p, 2))
    
    elif pattern == "Double Bottom":
        for i in range(n):
            if i < 10:
                p = base_price * (1.0 - i * 0.01)
            elif i < 20:
                p = base_price * (0.92 + (i-10) * 0.005)
            elif i < 30:
                p = base_price * (0.97 - (i-20) * 0.005)
            elif i < 40:
                p = base_price * (0.92 + (i-30) * 0.006)
            else:
                p = base_price * (0.96 + (i-40) * 0.001)
            prices.append(round(p + random.uniform(-p*0.005, p*0.005), 2))
    
    elif pattern == "Head & Shoulders":
        for i in range(n):
            if i < 12:
                p = base_price * (0.92 + i * 0.006)
            elif i < 20:
                p = base_price * (1.0 - (i-12) * 0.004)
            elif i < 32:
                p = base_price * (0.97 + (i-20) * 0.005)
            elif i < 42:
                p = base_price * (1.02 - (i-32) * 0.004)
            elif i < 52:
                p = base_price * (0.98 + (i-42) * 0.003)
            else:
                p = base_price * (1.01 - (i-52) * 0.005)
            prices.append(round(p + random.uniform(-p*0.004, p*0.004), 2))
    
    elif pattern == "Double Top":
        for i in range(n):
            if i < 15:
                p = base_price * (0.94 + i * 0.005)
            elif i < 25:
                p = base_price * (1.01 - (i-15) * 0.006)
            elif i < 40:
                p = base_price * (0.95 + (i-25) * 0.004)
            elif i < 50:
                p = base_price * (1.01 - (i-40) * 0.003)
            else:
                p = base_price * (1.00 - (i-50) * 0.004)
            prices.append(round(p + random.uniform(-p*0.004, p*0.004), 2))
    
    else:
        # Generic trending
        for i in range(n):
            trend = 0.001 if direction == "bullish" else -0.001
            p = base_price * (0.95 + i * trend + random.uniform(-0.005, 0.005))
            prices.append(round(p, 2))
    
    return prices


def generate_signals():
    signals = []
    
    stock_items = list(NSE_STOCKS.items())
    random.shuffle(stock_items)
    
    for idx, (name, info) in enumerate(stock_items[:15]):
        pattern_data = random.choice(PATTERNS)
        price = info["price"]
        
        conviction = pattern_data["base_conviction"] + random.randint(-8, 12)
        conviction = max(50, min(95, conviction))
        
        win_rate = pattern_data["success_rate"] + random.uniform(-0.05, 0.05)
        win_rate = round(max(0.55, min(0.82, win_rate)), 2)
        
        direction = pattern_data["direction"]
        
        # Price levels
        if direction == "bullish":
            key_level = round(price * random.uniform(0.98, 1.02), 2)
            target = round(price * random.uniform(1.05, 1.14), 2)
            stop_loss = round(price * random.uniform(0.93, 0.97), 2)
            neckline = round(price * random.uniform(1.00, 1.03), 2)
        else:
            key_level = round(price * random.uniform(0.98, 1.02), 2)
            target = round(price * random.uniform(0.86, 0.95), 2)
            stop_loss = round(price * random.uniform(1.03, 1.07), 2)
            neckline = round(price * random.uniform(0.97, 1.00), 2)
        
        rsi = random.randint(25, 75)
        vol_ratio = round(random.uniform(0.6, 1.8), 2)
        occurrences = random.randint(2, 8)
        avg_gain = round(random.uniform(3.5, 12.0), 1)
        avg_days = random.randint(8, 22)
        gain = round(random.uniform(7, 18), 1)
        
        # Generate insight text
        template = INSIGHTS.get(pattern_data["name"], INSIGHTS["Bull Flag"])
        insight = template.format(
            name=name,
            win_pct=int(win_rate * 100),
            occ=occurrences,
            avg_gain=avg_gain,
            avg_days=avg_days,
            rsi=rsi,
            vol_ratio=vol_ratio,
            key_level=key_level,
            neckline=neckline,
            target=target,
            stop_loss=stop_loss,
            gain=gain,
        )
        
        # Conviction label & color
        if conviction >= 80:
            conviction_label = "Very High"
            conviction_color = "#00C851"
        elif conviction >= 65:
            conviction_label = "High"
            conviction_color = "#4CAF50"
        elif conviction >= 50:
            conviction_label = "Moderate"
            conviction_color = "#FF9800"
        else:
            conviction_label = "Low"
            conviction_color = "#F44336"
        
        # Generate price history
        price_history = generate_price_history(price, pattern_data["name"], direction)
        dates = []
        from datetime import date, timedelta
        base_date = date(2025, 1, 10)
        for i in range(60):
            d = base_date + timedelta(days=i)
            while d.weekday() >= 5:
                d += timedelta(days=1)
            dates.append(str(d))
        
        # SMA calculations
        ph = price_history
        sma20 = [None]*19 + [round(sum(ph[i-19:i+1])/20, 2) for i in range(19, len(ph))]
        sma50 = [None]*49 + [round(sum(ph[i-49:i+1])/50, 2) for i in range(49, len(ph))]
        
        signals.append({
            "symbol": name,
            "sector": info["sector"],
            "pattern": pattern_data["name"],
            "direction": direction,
            "direction_emoji": "🟢" if direction == "bullish" else "🔴",
            "conviction": conviction,
            "conviction_label": conviction_label,
            "conviction_color": conviction_color,
            "insight": insight,
            "current_price": price,
            "target": target,
            "stop_loss": stop_loss,
            "key_level": key_level,
            "neckline": neckline,
            "win_rate": win_rate,
            "occurrences": occurrences,
            "avg_gain": avg_gain,
            "avg_days": avg_days,
            "rsi": rsi,
            "volume_confirm": vol_ratio > 1.0,
            "vol_ratio": vol_ratio,
            "trend_aligned": random.choice([True, True, False]),
            "price_history": price_history,
            "dates": dates,
            "sma20": sma20,
            "sma50": sma50,
        })
    
    signals.sort(key=lambda x: x["conviction"], reverse=True)
    return signals


if __name__ == "__main__":
    signals = generate_signals()
    with open('/home/claude/chart_pattern_intelligence/signals.json', 'w') as f:
        json.dump(signals, f, indent=2)
    print(f"Generated {len(signals)} signals")
    for s in signals[:5]:
        print(f"  {s['direction_emoji']} {s['symbol']} | {s['pattern']} | Conviction: {s['conviction']}")