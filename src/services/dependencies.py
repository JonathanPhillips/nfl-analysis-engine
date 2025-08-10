"""Service layer dependencies for dependency injection."""

from typing import Generator
from sqlalchemy.orm import Session

from .team_service import TeamService
from .game_service import GameService
from .player_service import PlayerService
from .play_service import PlayService
from .prediction_service import PredictionService
from ..api.dependencies import get_db_session


def get_team_service(db: Session = None) -> TeamService:
    """Get team service instance.
    
    Args:
        db: Database session (injected if None)
        
    Returns:
        TeamService instance
    """
    if db is None:
        # This would be used in dependency injection
        raise ValueError("Database session is required")
    return TeamService(db)


def get_game_service(db: Session = None) -> GameService:
    """Get game service instance.
    
    Args:
        db: Database session (injected if None)
        
    Returns:
        GameService instance
    """
    if db is None:
        raise ValueError("Database session is required")
    return GameService(db)


def get_player_service(db: Session = None) -> PlayerService:
    """Get player service instance.
    
    Args:
        db: Database session (injected if None)
        
    Returns:
        PlayerService instance
    """
    if db is None:
        raise ValueError("Database session is required")
    return PlayerService(db)


def get_play_service(db: Session = None) -> PlayService:
    """Get play service instance.
    
    Args:
        db: Database session (injected if None)
        
    Returns:
        PlayService instance
    """
    if db is None:
        raise ValueError("Database session is required")
    return PlayService(db)


def get_prediction_service(db: Session = None, model_dir: str = "models") -> PredictionService:
    """Get prediction service instance.
    
    Args:
        db: Database session (injected if None)
        model_dir: Directory containing ML models
        
    Returns:
        PredictionService instance
    """
    if db is None:
        raise ValueError("Database session is required")
    return PredictionService(db, model_dir)


# FastAPI dependency functions for injection
from fastapi import Depends

def team_service_dependency(db: Session = Depends(get_db_session)) -> TeamService:
    """FastAPI dependency for team service."""
    return get_team_service(db)


def game_service_dependency(db: Session = Depends(get_db_session)) -> GameService:
    """FastAPI dependency for game service."""
    return get_game_service(db)


def player_service_dependency(db: Session = Depends(get_db_session)) -> PlayerService:
    """FastAPI dependency for player service."""
    return get_player_service(db)


def play_service_dependency(db: Session = Depends(get_db_session)) -> PlayService:
    """FastAPI dependency for play service."""
    return get_play_service(db)


def prediction_service_dependency(db: Session = Depends(get_db_session)) -> PredictionService:
    """FastAPI dependency for prediction service."""
    return get_prediction_service(db, "models")