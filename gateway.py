"""
ET Markets AI Intelligence Platform — Unified Gateway
Single FastAPI app on port 8000 that serves the home page and
wraps each module in a full-screen iframe wrapper page.

Internal service ports (not user-facing):
  Chart Pattern & Radar  →  8001
  Market ChatGPT         →  8002
  AI Video Engine        →  8501
"""

from fastapi import FastAPI
from fastapi.responses import FileResponse, HTMLResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pathlib import Path

ROOT = Path(__file__).parent.resolve()

app = FastAPI(title="ET Markets AI Gateway", docs_url=None, redoc_url=None)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Shared nav HTML snippet ──────────────────────────────────────────
def _nav(active: str) -> str:
    tabs = [
        ("home",          "/",                "🏠 Home"),
        ("chart-pattern", "/chart-pattern",   "📡 Chart Pattern & Radar"),
        ("market-chat",   "/market-chat",     "🤖 MarketGPT"),
        ("video",         "/video",           "🎬 AI Video"),
    ]
    items = ""
    for key, href, label in tabs:
        cls = "gn-tab active" if key == active else "gn-tab"
        items += f'<a class="{cls}" href="{href}">{label}</a>'
    return f"""
<nav class="gateway-nav">
  <a class="gn-logo" href="/">
    <div class="gn-hex">
      <svg viewBox="0 0 18 18" fill="none" width="16" height="16">
        <path d="M9 1.5L15.5 5.25V12.75L9 16.5L2.5 12.75V5.25L9 1.5Z" fill="#0a0900"/>
        <path d="M9 5L12 6.75V10.25L9 12L6 10.25V6.75L9 5Z" fill="rgba(245,158,11,0.7)"/>
      </svg>
    </div>
    <span class="gn-name">ET Markets AI</span>
  </a>
  <div class="gn-tabs">{items}</div>
</nav>"""

# ── Shared CSS ───────────────────────────────────────────────────────
GATEWAY_CSS = """
<link rel="preconnect" href="https://fonts.googleapis.com">
<link href="https://fonts.googleapis.com/css2?family=DM+Mono:wght@400;500&family=Syne:wght@700;800&display=swap" rel="stylesheet">
<style>
  *, *::before, *::after { margin:0; padding:0; box-sizing:border-box; }
  html, body { height: 100%; overflow: hidden; background: #090b0f; }

  .gateway-nav {
    position: fixed; top: 0; left: 0; right: 0; z-index: 9999;
    height: 44px;
    background: rgba(9,11,15,0.97);
    border-bottom: 1px solid rgba(245,158,11,0.18);
    backdrop-filter: blur(16px);
    display: flex; align-items: center;
    padding: 0 16px; gap: 6px;
  }
  .gn-logo {
    display: flex; align-items: center; gap: 8px;
    text-decoration: none; flex-shrink: 0; margin-right: 10px;
  }
  .gn-hex {
    width: 28px; height: 28px; background: #f59e0b;
    clip-path: polygon(50% 0%,100% 25%,100% 75%,50% 100%,0% 75%,0% 25%);
    display: flex; align-items: center; justify-content: center;
  }
  .gn-name {
    font-family: 'Syne', sans-serif; font-size: 13px; font-weight: 800;
    color: #dde1eb; letter-spacing: -0.3px; white-space: nowrap;
  }
  .gn-tabs { display: flex; align-items: center; gap: 3px; }
  .gn-tab {
    font-family: 'DM Mono', monospace; font-size: 9px; letter-spacing: 1px;
    text-transform: uppercase; text-decoration: none;
    padding: 5px 12px; border-radius: 5px;
    color: #5a6070; border: 1px solid transparent;
    transition: all 0.15s; white-space: nowrap;
  }
  .gn-tab:hover { color: #dde1eb; border-color: rgba(255,255,255,0.1); background: #161a22; }
  .gn-tab.active { color: #f59e0b; border-color: rgba(245,158,11,0.25); background: rgba(245,158,11,0.06); }

  .module-frame {
    position: fixed; top: 44px; left: 0; right: 0; bottom: 0; border: none;
    width: 100%; height: calc(100vh - 44px);
  }
</style>
"""

# ── Wrapper page builder ─────────────────────────────────────────────
def _wrapper_page(active: str, iframe_src: str, title: str) -> str:
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>{title} — ET Markets AI</title>
  {GATEWAY_CSS}
</head>
<body>
  {_nav(active)}
  <iframe class="module-frame" src="{iframe_src}"
    allow="microphone; camera; clipboard-write"
    title="{title}">
  </iframe>
</body>
</html>"""

# ── Routes ───────────────────────────────────────────────────────────

@app.get("/", response_class=FileResponse)
async def home():
    """Serve the home page."""
    return FileResponse(str(ROOT / "index.html"), media_type="text/html")

@app.get("/chart-pattern", response_class=HTMLResponse)
async def chart_pattern():
    return _wrapper_page(
        active="chart-pattern",
        iframe_src="http://localhost:8001",
        title="Chart Pattern & Opportunity Radar",
    )

@app.get("/market-chat", response_class=HTMLResponse)
async def market_chat():
    return _wrapper_page(
        active="market-chat",
        iframe_src="http://localhost:8002",
        title="Market ChatGPT — Next Gen",
    )

@app.get("/video", response_class=HTMLResponse)
async def video_engine():
    return _wrapper_page(
        active="video",
        iframe_src="http://localhost:8501",
        title="AI Market Video Engine",
    )

# ── Static assets (CSS, JS, fonts, etc.) ────────────────────────────
# Serve any static files from root (for index.html assets if any)
app.mount("/static", StaticFiles(directory=str(ROOT)), name="static")


if __name__ == "__main__":
    import uvicorn
    print("=" * 60)
    print("  ET Markets AI Intelligence Platform — Gateway")
    print("  Single access point: http://localhost:8000")
    print("=" * 60)
    uvicorn.run(app, host="0.0.0.0", port=8000, log_level="info")
