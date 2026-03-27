#!/usr/bin/env python3
"""
ET Markets AI Intelligence Platform — Master Launcher
Single command to start the entire platform.

Usage:
    python start.py               # installs deps + starts all + opens browser
    python start.py --skip-install  # skip pip install (faster after first run)
    python start.py --no-browser    # don't auto-open browser

User-facing:
    http://localhost:8000  ← the ONLY URL you need

Internal (do not access directly):
    http://localhost:8001  Chart Pattern & Radar backend
    http://localhost:8002  Market ChatGPT backend
    http://localhost:8501  AI Video Engine (Streamlit)
"""

import subprocess
import sys
import os
import time
import signal
import threading
import argparse
import webbrowser
from pathlib import Path
from typing import Any, Dict, List

# ─────────────────────────────────────────────────────────────
# SERVICE DEFINITIONS
# ─────────────────────────────────────────────────────────────
ROOT = Path(__file__).parent.resolve()

Service = Dict[str, Any]

SERVICES: List[Service] = [
    # ── 1. Unified Gateway (user-facing, port 8000) ──────────────
    {
        "name":  "Gateway (port 8000)",
        "color": "\033[97m",   # white — primary service
        "cwd":   str(ROOT),
        "cmd":   [sys.executable, "-m", "uvicorn", "gateway:app",
                  "--host", "0.0.0.0", "--port", "8000"],
        "wait_seconds": 3,
        "user_facing": True,
    },
    # ── 2. Chart Pattern & Radar backend (internal, port 8001) ───
    {
        "name":  "Chart Pattern & Radar (internal 8001)",
        "color": "\033[93m",   # amber
        "cwd":   str(ROOT / "Chart_Pattern"),
        "cmd":   [sys.executable, "-m", "uvicorn", "main:app",
                  "--host", "0.0.0.0", "--port", "8001"],
        "wait_seconds": 5,
        "user_facing": False,
    },
    # ── 3. Market ChatGPT backend (internal, port 8002) ──────────
    {
        "name":  "Market ChatGPT (internal 8002)",
        "color": "\033[92m",   # teal/green
        "cwd":   str(ROOT / "ETChatbot"),
        "cmd":   [sys.executable, "-m", "uvicorn", "backend.main:app",
                  "--host", "0.0.0.0", "--port", "8002"],
        "wait_seconds": 5,
        "user_facing": False,
    },
    # ── 4. AI Video Engine (internal, port 8501) ──────────────────
    {
        "name":  "AI Video Engine (internal 8501)",
        "color": "\033[95m",   # purple
        "cwd":   str(ROOT / "VideoGen"),
        "cmd":   [sys.executable, "-m", "streamlit", "run", "app.py",
                  "--server.port", "8501",
                  "--server.address", "0.0.0.0",
                  "--server.headless", "true"],
        "wait_seconds": 7,
        "user_facing": False,
    },
]

RESET = "\033[0m"
BOLD  = "\033[1m"
RED   = "\033[91m"
CYAN  = "\033[96m"
DIM   = "\033[2m"

processes: list = []
stop_event = threading.Event()

# ─────────────────────────────────────────────────────────────
# HELPERS
# ─────────────────────────────────────────────────────────────
def tag(svc: Service) -> str:
    color: str = svc["color"]
    name:  str = svc["name"]
    return f"{color}[{name}]{RESET}"

def pipe_output(proc: subprocess.Popen, svc: Service) -> None:  # type: ignore[type-arg]
    """Stream subprocess output with a colored service prefix."""
    assert proc.stdout is not None
    for raw_line in iter(proc.stdout.readline, b""):
        if stop_event.is_set():
            break
        decoded = raw_line.decode("utf-8", errors="replace").rstrip()
        if decoded:
            prefix = tag(svc)
            # Dim internal service logs to reduce noise
            if not svc.get("user_facing"):
                print(f"  {DIM}{prefix}  {decoded}{RESET}")
            else:
                print(f"  {prefix}  {decoded}")

def start_service(svc: Service) -> subprocess.Popen:  # type: ignore[type-arg]
    """Launch a subprocess for a single service."""
    marker = "▶" if svc.get("user_facing") else "·"
    print(f"  {marker}  {tag(svc)}")

    proc = subprocess.Popen(
        svc["cmd"],
        cwd=svc["cwd"],
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        env=os.environ.copy(),
    )
    processes.append(proc)
    threading.Thread(target=pipe_output, args=(proc, svc), daemon=True).start()
    return proc

def check_python() -> None:
    v = sys.version_info
    if v < (3, 8):
        print(f"{RED}✗ Python 3.8+ required (found {v.major}.{v.minor}){RESET}")
        sys.exit(1)
    print(f"  ✓ Python {v.major}.{v.minor}.{v.micro}")

def install_deps() -> None:
    reqs = [
        ROOT / "Chart_Pattern" / "requirements.txt",
        ROOT / "ETChatbot"     / "requirements.txt",
        ROOT / "VideoGen"      / "requirements.txt",
    ]
    gateway_deps = ["fastapi", "uvicorn[standard]"]
    print(f"  📦 Gateway deps...")
    subprocess.run(
        [sys.executable, "-m", "pip", "install", "-q"] + gateway_deps,
        capture_output=True,
    )
    for req in reqs:
        if req.exists():
            module = req.parent.name
            print(f"  📦 {module}...")
            result = subprocess.run(
                [sys.executable, "-m", "pip", "install", "-q", "-r", str(req)],
                capture_output=True, text=True,
            )
            if result.returncode != 0:
                stderr_out: str = result.stderr if isinstance(result.stderr, str) else ""
                print(f"  {RED}⚠  {module}: {stderr_out[0:150]}{RESET}")

def cleanup(signum: Any = None, frame: Any = None) -> None:
    print(f"\n\n{BOLD}🛑 Shutting down...{RESET}")
    stop_event.set()
    for proc in processes:
        try:
            proc.terminate()
        except Exception:
            pass
    time.sleep(1)
    for proc in processes:
        try:
            proc.kill()
        except Exception:
            pass
    print(f"{BOLD}✓ All services stopped.{RESET}")
    sys.exit(0)

# ─────────────────────────────────────────────────────────────
# MAIN
# ─────────────────────────────────────────────────────────────
def main() -> None:
    parser = argparse.ArgumentParser(description="ET Markets AI Platform Launcher")
    parser.add_argument("--no-browser",    action="store_true", help="Don't open browser")
    parser.add_argument("--skip-install",  action="store_true", help="Skip pip install")
    args = parser.parse_args()

    signal.signal(signal.SIGINT,  cleanup)
    signal.signal(signal.SIGTERM, cleanup)

    print(f"""
{BOLD}\033[93m╔══════════════════════════════════════════════════════════╗
║      ET Markets AI Intelligence Platform                 ║
║      Single-Command Launcher — Unified on port 8000      ║
╚══════════════════════════════════════════════════════════╝{RESET}
""")

    print(f"{BOLD}Pre-flight check:{RESET}")
    check_python()

    if not args.skip_install:
        print(f"\n{BOLD}Installing dependencies:{RESET}")
        install_deps()
    else:
        print("  ⚡ Skipping install")

    print(f"\n{BOLD}Starting services:{RESET}")
    for svc in SERVICES:
        start_service(svc)
        time.sleep(0.4)

    # Wait for services to boot
    max_wait: float = float(max(float(s["wait_seconds"]) for s in SERVICES))
    total = int(max_wait)
    print(f"\n{BOLD}⏳ Waiting {total}s for services to boot...{RESET}", flush=True)
    for i in range(total):
        time.sleep(1)
        bar = "█" * (i + 1) + "░" * (total - i - 1)
        print(f"  [{bar}] {i+1}/{total}", flush=True)

    print(f"""
{BOLD}\033[92m╔══════════════════════════════════════════════════════════╗
║        ✅  PLATFORM RUNNING — ONE URL TO RULE THEM ALL   ║
╚══════════════════════════════════════════════════════════╝{RESET}

  🌐  {BOLD}http://localhost:8000{RESET}  ← open this in your browser

  Navigate between modules using the top nav bar.
  {CYAN}Press CTRL+C to stop everything.{RESET}
""")

    if not args.no_browser:
        try:
            webbrowser.open("http://localhost:8000")
        except Exception:
            pass

    try:
        while True:
            time.sleep(2)
            for i, proc in enumerate(processes):
                if proc.poll() is not None:
                    svc_name = str(SERVICES[i]["name"]) if i < len(SERVICES) else f"Service {i}"
                    print(f"  {RED}⚠  {svc_name} exited (code {proc.returncode}){RESET}")
    except KeyboardInterrupt:
        cleanup()

if __name__ == "__main__":
    main()
