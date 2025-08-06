"""Games API endpoints."""

from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Request, Query
from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError
from datetime import date
import logging

from ...models.game import GameModel as Game
from ..dependencies import get_db_session

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/")
async def get_games(
    request: Request,
    limit: int = Query(50, ge=1, le=500, description="Number of games to return"),
    offset: int = Query(0, ge=0, description="Number of games to skip"),
    season: Optional[int] = Query(None, description="Filter by season"),
    season_type: Optional[str] = Query(None, description="Filter by season type (REG/POST/PRE)"),
    week: Optional[int] = Query(None, description="Filter by week"),
    team: Optional[str] = Query(None, description="Filter by team (home or away)"),
    db: Session = Depends(get_db_session)
):
    """Get list of NFL games with filtering options."""
    try:
        query = db.query(Game)
        
        # Apply filters
        if season:
            query = query.filter(Game.season == season)
        
        if season_type:
            query = query.filter(Game.season_type == season_type.upper())
        
        if week:
            query = query.filter(Game.week == week)
        
        if team:
            team = team.upper()
            query = query.filter(
                (Game.home_team == team) | (Game.away_team == team)
            )
        
        # Order by game date descending
        query = query.order_by(Game.game_date.desc())
        
        # Get total count
        total = query.count()
        
        # Apply pagination
        games = query.offset(offset).limit(limit).all()
        
        return {
            "games": [
                {
                    "id": game.id,
                    "game_id": game.game_id,
                    "season": game.season,
                    "season_type": game.season_type,
                    "week": game.week,
                    "game_date": game.game_date.isoformat() if game.game_date else None,
                    "home_team": game.home_team,
                    "away_team": game.away_team,
                    "home_score": game.home_score,
                    "away_score": game.away_score,
                    "total": game.total,
                    "overtime": game.overtime,
                    "stadium": game.stadium,
                    "weather_temp": game.weather_temp,
                    "weather_humidity": game.weather_humidity,
                    "weather_wind": game.weather_wind,
                    "roof": game.roof,
                    "surface": game.surface
                } for game in games
            ],
            "total": total,
            "limit": limit,
            "offset": offset
        }
    
    except SQLAlchemyError as e:
        logger.error(f"Database error in get_games: {str(e)}")
        raise HTTPException(status_code=500, detail="Database error")
    except Exception as e:
        logger.error(f"Unexpected error in get_games: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/{game_id}")
async def get_game(
    game_id: str,
    db: Session = Depends(get_db_session)
):
    """Get a specific game by ID."""
    try:
        game = db.query(Game).filter(Game.game_id == game_id).first()
        
        if not game:
            raise HTTPException(status_code=404, detail=f"Game {game_id} not found")
        
        return {
            "id": game.id,
            "game_id": game.game_id,
            "season": game.season,
            "season_type": game.season_type,
            "week": game.week,
            "game_date": game.game_date.isoformat() if game.game_date else None,
            "home_team": game.home_team,
            "away_team": game.away_team,
            "home_score": game.home_score,
            "away_score": game.away_score,
            "total": game.total,
            "overtime": game.overtime,
            "stadium": game.stadium,
            "weather_temp": game.weather_temp,
            "weather_humidity": game.weather_humidity,
            "weather_wind": game.weather_wind,
            "roof": game.roof,
            "surface": game.surface,
            "home_coach": game.home_coach,
            "away_coach": game.away_coach,
            "referee": game.referee,
            "stadium_id": game.stadium_id,
            "created_at": game.created_at,
            "updated_at": game.updated_at
        }
    
    except HTTPException:
        raise
    except SQLAlchemyError as e:
        logger.error(f"Database error in get_game: {str(e)}")
        raise HTTPException(status_code=500, detail="Database error")
    except Exception as e:
        logger.error(f"Unexpected error in get_game: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/recent")
async def get_recent_games(
    limit: int = Query(10, ge=1, le=50, description="Number of recent games to return"),
    db: Session = Depends(get_db_session)
):
    """Get most recent games."""
    try:
        games = (db.query(Game)
                .filter(Game.game_date <= date.today())
                .order_by(Game.game_date.desc())
                .limit(limit)
                .all())
        
        return {
            "games": [
                {
                    "id": game.id,
                    "game_id": game.game_id,
                    "season": game.season,
                    "week": game.week,
                    "game_date": game.game_date.isoformat() if game.game_date else None,
                    "home_team": game.home_team,
                    "away_team": game.away_team,
                    "home_score": game.home_score,
                    "away_score": game.away_score
                } for game in games
            ],
            "count": len(games)
        }
    
    except SQLAlchemyError as e:
        logger.error(f"Database error in get_recent_games: {str(e)}")
        raise HTTPException(status_code=500, detail="Database error")
    except Exception as e:
        logger.error(f"Unexpected error in get_recent_games: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")