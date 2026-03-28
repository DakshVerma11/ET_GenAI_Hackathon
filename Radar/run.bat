@echo off

REM Opportunity Radar — Quick Start Script for Windows

echo.
echo 🚀 Opportunity Radar — Starting up...
echo.

REM Check if Python is installed
python --version >nul 2>&1
if errorlevel 1 (
    echo ❌ Python not found. Please install Python 3.10+
    pause
    exit /b 1
)

REM Create venv if it doesn't exist
if not exist "venv" (
    echo 📦 Creating virtual environment...
    python -m venv venv
)

REM Activate venv
echo ✅ Activating virtual environment...
call venv\Scripts\activate.bat

REM Install dependencies
echo 📚 Installing dependencies...
pip install -q -r requirements.txt

REM Check .env file
if not exist ".env" (
    echo ⚠️  .env file not found. Creating from .env.example...
    copy .env.example .env
    echo 📝 Please edit .env and set ANTHROPIC_API_KEY
    pause
)

REM Initialize database
if not exist "signals.db" (
    echo 🗄️  Initializing database...
    python init_db.py
) else (
    echo ✅ Database exists (signals.db)
)

echo.
echo ════════════════════════════════════════════════════════════
echo 🎯 Opportunity Radar is starting...
echo ════════════════════════════════════════════════════════════
echo.
echo 📊 Dashboard:  http://localhost:8000
echo 📚 API Docs:   http://localhost:8000/docs
echo 🔗 WebSocket:  ws://localhost:8000/ws/feed
echo.
echo Press Ctrl+C to stop.
echo ════════════════════════════════════════════════════════════
echo.

uvicorn api:app --reload --host 0.0.0.0 --port 8000
pause
