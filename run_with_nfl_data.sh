#!/bin/bash

# NFL Analysis Engine - Production Startup with Real NFL Data
echo "🏈 Starting NFL Analysis Engine with 2024 NFL Data..."

# Set environment variables for NFL database
export DATABASE_URL="sqlite:///nfl_data.db"
export PYTHONPATH="/Users/jon/Documents/code/nfl-analysis-engine/src"

# Verify database exists
if [ ! -f "nfl_data.db" ]; then
    echo "❌ NFL database not found! Run setup_nfl_database.py first."
    exit 1
fi

echo "✅ Using NFL database: nfl_data.db"
echo "✅ Python path: $PYTHONPATH"

# Activate virtual environment
source venv/bin/activate

echo "🚀 Starting server on http://localhost:8000"
echo "   Expected League Leaders:"
echo "   📊 QBs: Joe Burrow (4,918 yards), Jared Goff (4,942 yards)"  
echo "   🏃 RBs: Saquon Barkley (2,504 yards), Brian Robinson (2,384 yards)"
echo "   🎯 WRs: Ja'Marr Chase (1,708 yards), Justin Jefferson (1,601 yards)"
echo ""

# Start the server
uvicorn src.api.main:app --reload --host 0.0.0.0 --port 8000