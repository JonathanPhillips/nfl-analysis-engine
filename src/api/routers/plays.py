"""Plays API endpoints."""

from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Request, Query
from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError
import logging

from ...models.play import PlayModel as Play
from ..dependencies import get_db_session

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/")
async def get_plays(
    request: Request,
    limit: int = Query(100, ge=1, le=1000, description="Number of plays to return"),
    offset: int = Query(0, ge=0, description="Number of plays to skip"),
    game_id: Optional[str] = Query(None, description="Filter by game ID"),
    season: Optional[int] = Query(None, description="Filter by season"),
    play_type: Optional[str] = Query(None, description="Filter by play type"),
    posteam: Optional[str] = Query(None, description="Filter by possession team"),
    db: Session = Depends(get_db_session)
):
    """Get list of NFL plays with filtering options."""
    try:
        query = db.query(Play)
        
        # Apply filters
        if game_id:
            query = query.filter(Play.game_id == game_id)
        
        if season:
            query = query.filter(Play.season == season)
        
        if play_type:
            query = query.filter(Play.play_type == play_type.lower())
        
        if posteam:
            query = query.filter(Play.posteam == posteam.upper())
        
        # Order by game, then by play sequence
        query = query.order_by(Play.game_id, Play.play_id)
        
        # Get total count
        total = query.count()
        
        # Apply pagination
        plays = query.offset(offset).limit(limit).all()
        
        return {
            "plays": [
                {
                    "id": play.id,
                    "play_id": play.play_id,
                    "game_id": play.game_id,
                    "season": play.season,
                    "week": play.week,
                    "posteam": play.posteam,
                    "defteam": play.defteam,
                    "play_type": play.play_type,
                    "qtr": play.qtr,
                    "down": play.down,
                    "ydstogo": play.ydstogo,
                    "yardline_100": play.yardline_100,
                    "yards_gained": play.yards_gained,
                    "touchdown": play.touchdown,
                    "first_down": play.first_down,
                    "fourth_down_converted": play.fourth_down_converted,
                    "fourth_down_failed": play.fourth_down_failed,
                    "incomplete_pass": play.incomplete_pass,
                    "interception": play.interception,
                    "fumble": play.fumble,
                    "safety": play.safety,
                    "penalty": play.penalty,
                    "ep": play.ep,
                    "epa": play.epa,
                    "wp": play.wp,
                    "wpa": play.wpa
                } for play in plays
            ],
            "total": total,
            "limit": limit,
            "offset": offset
        }
    
    except SQLAlchemyError as e:
        logger.error(f"Database error in get_plays: {str(e)}")
        raise HTTPException(status_code=500, detail="Database error")
    except Exception as e:
        logger.error(f"Unexpected error in get_plays: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/{play_id}")
async def get_play(
    play_id: str,
    db: Session = Depends(get_db_session)
):
    """Get a specific play by ID."""
    try:
        play = db.query(Play).filter(Play.play_id == play_id).first()
        
        if not play:
            raise HTTPException(status_code=404, detail=f"Play {play_id} not found")
        
        return {
            "id": play.id,
            "play_id": play.play_id,
            "game_id": play.game_id,
            "season": play.season,
            "week": play.week,
            "posteam": play.posteam,
            "defteam": play.defteam,
            "play_type": play.play_type,
            "desc": play.desc,
            "qtr": play.qtr,
            "down": play.down,
            "ydstogo": play.ydstogo,
            "yardline_100": play.yardline_100,
            "yards_gained": play.yards_gained,
            "touchdown": play.touchdown,
            "first_down": play.first_down,
            "fourth_down_converted": play.fourth_down_converted,
            "fourth_down_failed": play.fourth_down_failed,
            "incomplete_pass": play.incomplete_pass,
            "interception": play.interception,
            "fumble": play.fumble,
            "safety": play.safety,
            "penalty": play.penalty,
            "penalty_yards": play.penalty_yards,
            "ep": play.ep,
            "epa": play.epa,
            "wp": play.wp,
            "wpa": play.wpa,
            "passer_player_id": play.passer_player_id,
            "receiver_player_id": play.receiver_player_id,
            "rusher_player_id": play.rusher_player_id,
            "created_at": play.created_at,
            "updated_at": play.updated_at
        }
    
    except HTTPException:
        raise
    except SQLAlchemyError as e:
        logger.error(f"Database error in get_play: {str(e)}")
        raise HTTPException(status_code=500, detail="Database error")
    except Exception as e:
        logger.error(f"Unexpected error in get_play: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/game/{game_id}")
async def get_game_plays(
    game_id: str,
    limit: int = Query(500, ge=1, le=1000, description="Number of plays to return"),
    db: Session = Depends(get_db_session)
):
    """Get all plays for a specific game."""
    try:
        plays = (db.query(Play)
                .filter(Play.game_id == game_id)
                .order_by(Play.play_id)
                .limit(limit)
                .all())
        
        if not plays:
            raise HTTPException(status_code=404, detail=f"No plays found for game {game_id}")
        
        return {
            "game_id": game_id,
            "plays": [
                {
                    "play_id": play.play_id,
                    "desc": play.desc,
                    "qtr": play.qtr,
                    "down": play.down,
                    "ydstogo": play.ydstogo,
                    "yardline_100": play.yardline_100,
                    "posteam": play.posteam,
                    "play_type": play.play_type,
                    "yards_gained": play.yards_gained,
                    "touchdown": play.touchdown,
                    "first_down": play.first_down,
                    "epa": play.epa,
                    "wp": play.wp
                } for play in plays
            ],
            "total_plays": len(plays)
        }
    
    except HTTPException:
        raise
    except SQLAlchemyError as e:
        logger.error(f"Database error in get_game_plays: {str(e)}")
        raise HTTPException(status_code=500, detail="Database error")
    except Exception as e:
        logger.error(f"Unexpected error in get_game_plays: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")