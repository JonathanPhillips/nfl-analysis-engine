"""Players API endpoints."""

from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Request, Query
from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError
import logging

from ...models.player import PlayerModel as Player
from ..dependencies import get_db_session

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/")
async def get_players(
    request: Request,
    limit: int = Query(50, ge=1, le=1000, description="Number of players to return"),
    offset: int = Query(0, ge=0, description="Number of players to skip"),
    team_abbr: Optional[str] = Query(None, description="Filter by team abbreviation"),
    position: Optional[str] = Query(None, description="Filter by position"),
    active_only: bool = Query(True, description="Return only active players"),
    db: Session = Depends(get_db_session)
):
    """Get list of NFL players with filtering options."""
    try:
        query = db.query(Player)
        
        # Apply filters
        if team_abbr:
            query = query.filter(Player.team_abbr == team_abbr.upper())
        
        if position:
            query = query.filter(Player.position == position.upper())
        
        if active_only:
            query = query.filter(Player.status == 'active')
        
        # Get total count
        total = query.count()
        
        # Apply pagination
        players = query.offset(offset).limit(limit).all()
        
        return {
            "players": [
                {
                    "id": player.id,
                    "player_id": player.player_id,
                    "full_name": player.full_name,
                    "first_name": player.first_name,
                    "last_name": player.last_name,
                    "team_abbr": player.team_abbr,
                    "position": player.position,
                    "jersey_number": player.jersey_number,
                    "status": player.status,
                    "height": player.height,
                    "weight": player.weight,
                    "age": player.age,
                    "rookie_year": player.rookie_year
                } for player in players
            ],
            "total": total,
            "limit": limit,
            "offset": offset
        }
    
    except SQLAlchemyError as e:
        logger.error(f"Database error in get_players: {str(e)}")
        raise HTTPException(status_code=500, detail="Database error")
    except Exception as e:
        logger.error(f"Unexpected error in get_players: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/{player_id}")
async def get_player(
    player_id: str,
    db: Session = Depends(get_db_session)
):
    """Get a specific player by ID."""
    try:
        player = db.query(Player).filter(Player.player_id == player_id).first()
        
        if not player:
            raise HTTPException(status_code=404, detail=f"Player {player_id} not found")
        
        return {
            "id": player.id,
            "player_id": player.player_id,
            "full_name": player.full_name,
            "first_name": player.first_name,
            "last_name": player.last_name,
            "team_abbr": player.team_abbr,
            "position": player.position,
            "jersey_number": player.jersey_number,
            "status": player.status,
            "height": player.height,
            "weight": player.weight,
            "age": player.age,
            "rookie_year": player.rookie_year,
            "created_at": player.created_at,
            "updated_at": player.updated_at
        }
    
    except HTTPException:
        raise
    except SQLAlchemyError as e:
        logger.error(f"Database error in get_player: {str(e)}")
        raise HTTPException(status_code=500, detail="Database error")
    except Exception as e:
        logger.error(f"Unexpected error in get_player: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/{player_id}/stats")
async def get_player_stats(
    player_id: str,
    season: Optional[int] = Query(None, description="Season year"),
    db: Session = Depends(get_db_session)
):
    """Get player statistics for a specific season."""
    try:
        player = db.query(Player).filter(Player.player_id == player_id).first()
        
        if not player:
            raise HTTPException(status_code=404, detail=f"Player {player_id} not found")
        
        # For now, return basic player info with placeholder stats
        # TODO: Implement actual statistics calculation from plays
        stats = {
            "player": {
                "id": player.id,
                "player_id": player.player_id,
                "full_name": player.full_name,
                "team_abbr": player.team_abbr,
                "position": player.position
            },
            "season": season,
            "games_played": 0,
            "stats": {},
            "message": "Statistics calculation not yet implemented"
        }
        
        return stats
    
    except HTTPException:
        raise
    except SQLAlchemyError as e:
        logger.error(f"Database error in get_player_stats: {str(e)}")
        raise HTTPException(status_code=500, detail="Database error")
    except Exception as e:
        logger.error(f"Unexpected error in get_player_stats: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")