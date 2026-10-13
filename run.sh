#!/usr/bin/env bash
set -e

# Setup or reuse virtual environment
if [ ! -d "venv" ]; then
    echo "Creating virtual environment..."
    python3 -m venv venv || python -m venv venv
fi

if [ -f "venv/bin/activate" ]; then
    source venv/bin/activate
elif [ -f "venv/Scripts/activate" ]; then
    source venv/Scripts/activate
fi

# Install dependencies
pip install -r requirements.txt

# Start service on port 8000 (supports custom PORT env var if provided)
PORT="${PORT:-8000}"
echo "Starting invoice extraction service on port $PORT..."
uvicorn app.main:app --host 0.0.0.0 --port "$PORT"
