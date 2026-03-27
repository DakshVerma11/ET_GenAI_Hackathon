#!/usr/bin/env python3
"""
ET Markets - FastAPI Server Launcher
Starts the Chart Pattern Intelligence backend server
"""

import sys
import subprocess
import platform

def check_python_version():
    """Verify Python 3.8+"""
    if sys.version_info < (3, 8):
        print("❌ Python 3.8+ required")
        print(f"   Current: {sys.version}")
        sys.exit(1)
    print(f"✓ Python {sys.version.split()[0]}")

def check_dependencies():
    """Check and install required packages"""
    required = ['fastapi', 'uvicorn', 'yfinance', 'pandas']
    missing = []
    
    for package in required:
        try:
            __import__(package)
        except ImportError:
            missing.append(package)
    
    if missing:
        print(f"⚠️  Missing packages: {', '.join(missing)}")
        print("   Installing dependencies...")
        subprocess.check_call([sys.executable, '-m', 'pip', 'install', '-r', 'requirements.txt'])
        print("✓ Dependencies installed")
    else:
        print(f"✓ All dependencies available ({len(required)} packages)")

def start_server():
    """Start the FastAPI server"""
    print("\n" + "="*50)
    print("  Starting ET Markets API Server")
    print("="*50 + "\n")
    print("📍 Server: http://localhost:8000")
    print("📊 Dashboard: http://localhost:8000")
    print("📡 API Docs: http://localhost:8000/docs")
    print("⚙️  Redoc: http://localhost:8000/redoc")
    print("\nPress CTRL+C to stop\n")
    
    try:
        from uvicorn import run
        run("main:app", host="0.0.0.0", port=8000, log_level="info")
    except KeyboardInterrupt:
        print("\n\n✓ Server stopped")
        sys.exit(0)
    except Exception as e:
        print(f"\n❌ Error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    try:
        print("╔════════════════════════════════════════════════╗")
        print("║   ET Markets - Chart Pattern Intelligence      ║")
        print("║         Initializing Server...                 ║")
        print("╚════════════════════════════════════════════════╝\n")
        
        check_python_version()
        check_dependencies()
        start_server()
        
    except Exception as e:
        print(f"\n❌ Initialization error: {e}")
        sys.exit(1)
