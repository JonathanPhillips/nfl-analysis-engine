# Quick Start Guide

Get the NFL Analysis Engine running in under 5 minutes with this streamlined setup.

## Docker Quick Start (Recommended)

```bash
# Clone and start
git clone https://github.com/JonathanPhillips/nfl-analysis-engine.git
cd nfl-analysis-engine
docker-compose up --build

# Wait 2-3 minutes for initial setup
# Access at http://localhost:8000
```

## What You Get

After startup, you'll have access to:

- **Web Dashboard**: http://localhost:8000
- **API Documentation**: http://localhost:8000/api/docs  
- **Teams Analytics**: 32 NFL teams with comprehensive stats
- **Player Statistics**: 949+ players with position-specific metrics
- **ML Predictions**: 75% accuracy game outcome predictions
- **Play-by-Play**: 49,492+ plays from 2024 season

## Key Features Tour

### 1. Team Analytics Dashboard
Navigate to **Teams** to explore:
- Red zone efficiency (scoring percentage inside 20-yard line)
- Third down conversion rates
- Turnover differential analysis
- Points per game and yards per play

### 2. Player Statistics
Visit **Players** for:
- Position-specific metrics (QB rating, RB YPC, WR catch rate)
- Individual player profiles with season stats
- League leaders with minimum qualification thresholds
- Advanced analytics (EPA, success rate)

### 3. Game Predictions
Use **Predictions** to:
- Generate ML-powered game outcome predictions
- View win probabilities and confidence scores
- Compare predictions against Vegas lines
- Analyze team matchup advantages

### 4. League Leaders
Check **League Leaders** for:
- Top performers by position (QB, RB, WR)
- Professional-grade statistics
- Minimum attempt/carry thresholds
- EPA and advanced metrics

## Sample API Usage

```bash
# Get all teams
curl http://localhost:8000/api/v1/teams

# Get specific team analytics
curl http://localhost:8000/api/v1/teams/KC

# Get player statistics
curl http://localhost:8000/api/v1/players/limit=10

# Generate game prediction
curl -X POST http://localhost:8000/api/v1/predictions \
  -H "Content-Type: application/json" \
  -d '{"home_team": "KC", "away_team": "BUF", "game_date": "2024-12-01"}'
```

## Data Verification

Verify your setup is working correctly:

```bash
# Check database health
curl http://localhost:8000/api/v1/health

# Verify team count (should return 32)
curl http://localhost:8000/api/v1/teams | jq '. | length'

# Check player statistics
curl http://localhost:8000/api/v1/players?limit=5

# Test ML prediction
curl -X POST http://localhost:8000/api/v1/predictions \
  -H "Content-Type: application/json" \
  -d '{"home_team": "SF", "away_team": "DAL", "game_date": "2024-12-01"}'
```

## Performance Benchmarks

Expected performance on modern hardware:

- **Startup Time**: 2-3 minutes (initial data load)
- **API Response**: <200ms for most endpoints
- **ML Prediction**: <500ms per game prediction
- **Database Queries**: <100ms for player/team lookups
- **Web Page Load**: <1s for dashboard and analytics pages

## Troubleshooting Quick Fixes

**Port 8000 in use?**
```bash
docker-compose down
lsof -ti:8000 | xargs kill -9
docker-compose up
```

**Database connection issues?**
```bash
docker-compose down
docker system prune -f
docker-compose up --build
```

**Missing data?**
```bash
# Check database is populated
curl http://localhost:8000/api/v1/teams
curl http://localhost:8000/api/v1/players?limit=1
```

## Next Steps

- [Configuration Guide](configuration.md) - Customize your setup
- [Architecture Overview](../architecture/overview.md) - Understanding the system
- [API Reference](../api/teams.md) - Complete API documentation
- [Development Setup](../development/setup.md) - Contributing and development