#!/bin/bash

# NFL Analysis Engine Server Startup Script

echo "==================================="
echo "NFL Analysis Engine - Web Interface"
echo "==================================="

# Navigate to project directory
cd /Users/jon/Documents/code/nfl-analysis-engine

# Activate virtual environment
source venv/bin/activate

# Check if port is provided as argument, otherwise use 8003
PORT=${1:-8003}

echo ""
echo "Starting server on port $PORT..."
echo ""
echo "Once started, open your browser and visit:"
echo "  → http://localhost:$PORT"
echo ""
echo "Available pages:"
echo "  → http://localhost:$PORT/web/ - Web Interface"
echo "  → http://localhost:$PORT/api/docs - API Documentation"
echo ""
echo "Press Ctrl+C to stop the server"
echo "==================================="
echo ""

# Run the server
uvicorn src.api.main:app --host 127.0.0.1 --port $PORT --reload