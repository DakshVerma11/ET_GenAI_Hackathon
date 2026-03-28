#!/bin/bash

# Opportunity Radar — Quick Start Script

echo "🚀 Opportunity Radar — Starting up..."
echo

# Check Python
if ! command -v python &> /dev/null; then
    echo "❌ Python not found. Please install Python 3.10+"
    exit 1
fi

# Check venv
if [ ! -d "venv" ]; then
    echo "📦 Creating virtual environment..."
    python -m venv venv
fi

# Activate venv
echo "✅ Activating virtual environment..."
source venv/bin/activate 2>/dev/null || source venv/Scripts/activate 2>/dev/null

# Install dependencies
echo "📚 Installing dependencies..."
pip install -q -r requirements.txt

# Check .env file
if [ ! -f ".env" ]; then
    echo "⚠️  .env file not found. Creating from .env.example..."
    cp .env.example .env
    echo "📝 Please edit .env and set ANTHROPIC_API_KEY"
fi

# Initialize database
if [ ! -f "signals.db" ]; then
    echo "🗄️  Initializing database..."
    python init_db.py
else
    echo "✅ Database exists (signals.db)"
fi

# Start the app
echo
echo "════════════════════════════════════════════════════════════"
echo "🎯 Opportunity Radar is starting..."
echo "════════════════════════════════════════════════════════════"
echo
echo "📊 Dashboard:  http://localhost:8000"
echo "📚 API Docs:   http://localhost:8000/docs"
echo "🔗 WebSocket:  ws://localhost:8000/ws/feed"
echo
echo "Press Ctrl+C to stop."
echo "════════════════════════════════════════════════════════════"
echo

uvicorn api:app --reload --host 0.0.0.0 --port 8000
