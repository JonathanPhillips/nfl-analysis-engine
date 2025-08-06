"""Data management API endpoints."""

from typing import Optional, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError
import logging

from ...data.data_loader import DataLoader
from ...data.pipeline import DataValidationPipeline, PipelineConfig
from ..dependencies import get_db_session

logger = logging.getLogger(__name__)

router = APIRouter()

# Global data loader instance
data_loader = None


def get_data_loader() -> DataLoader:
    """Get or create data loader instance."""
    global data_loader
    if data_loader is None:
        data_loader = DataLoader()
    return data_loader


@router.get("/status")
async def get_data_status(
    db: Session = Depends(get_db_session)
):
    """Get current data loading status and database statistics."""
    try:
        loader = get_data_loader()
        
        # Get load status
        status = loader.get_load_status()
        
        # Get database counts
        from ...models.team import TeamModel as Team
        from ...models.player import PlayerModel as Player
        from ...models.game import GameModel as Game
        from ...models.play import PlayModel as Play
        
        db_stats = {
            "teams": db.query(Team).count(),
            "players": db.query(Player).count(),
            "games": db.query(Game).count(),
            "plays": db.query(Play).count()
        }
        
        return {
            "status": "success",
            "data_loading": status,
            "database_counts": db_stats,
            "last_updated": status.get("last_updated", "Never")
        }
    
    except SQLAlchemyError as e:
        logger.error(f"Database error in get_data_status: {str(e)}")
        raise HTTPException(status_code=500, detail="Database error")
    except Exception as e:
        logger.error(f"Unexpected error in get_data_status: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.post("/load/teams")
async def load_teams_data(
    background_tasks: BackgroundTasks,
    force_refresh: bool = False,
    db: Session = Depends(get_db_session)
):
    """Load teams data from nfl_data_py."""
    try:
        loader = get_data_loader()
        
        # Load teams data
        result = loader.load_teams(force_refresh=force_refresh)
        
        return {
            "status": "success",
            "message": f"Loaded {result.records_loaded} teams",
            "result": {
                "records_loaded": result.records_loaded,
                "records_updated": result.records_updated,
                "records_skipped": result.records_skipped,
                "duration_seconds": result.duration.total_seconds(),
                "errors": result.errors
            }
        }
    
    except Exception as e:
        logger.error(f"Error loading teams data: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to load teams data: {str(e)}")


@router.post("/load/players")
async def load_players_data(
    background_tasks: BackgroundTasks,
    seasons: Optional[str] = None,
    force_refresh: bool = False,
    db: Session = Depends(get_db_session)
):
    """Load players data from nfl_data_py for specified seasons."""
    try:
        loader = get_data_loader()
        
        # Parse seasons parameter
        season_list = None
        if seasons:
            try:
                season_list = [int(s.strip()) for s in seasons.split(',')]
            except ValueError:
                raise HTTPException(status_code=400, detail="Invalid seasons format. Use comma-separated integers.")
        
        # Load players data
        result = loader.load_players(seasons=season_list, force_refresh=force_refresh)
        
        return {
            "status": "success",
            "message": f"Loaded {result.records_loaded} players",
            "result": {
                "records_loaded": result.records_loaded,
                "records_updated": result.records_updated,
                "records_skipped": result.records_skipped,
                "duration_seconds": result.duration.total_seconds(),
                "errors": result.errors
            }
        }
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error loading players data: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to load players data: {str(e)}")


@router.post("/load/games")
async def load_games_data(
    background_tasks: BackgroundTasks,
    seasons: Optional[str] = None,
    force_refresh: bool = False,
    db: Session = Depends(get_db_session)
):
    """Load games data from nfl_data_py for specified seasons."""
    try:
        loader = get_data_loader()
        
        # Parse seasons parameter
        season_list = None
        if seasons:
            try:
                season_list = [int(s.strip()) for s in seasons.split(',')]
            except ValueError:
                raise HTTPException(status_code=400, detail="Invalid seasons format. Use comma-separated integers.")
        
        # Load games data
        result = loader.load_games(seasons=season_list, force_refresh=force_refresh)
        
        return {
            "status": "success",
            "message": f"Loaded {result.records_loaded} games",
            "result": {
                "records_loaded": result.records_loaded,
                "records_updated": result.records_updated,
                "records_skipped": result.records_skipped,
                "duration_seconds": result.duration.total_seconds(),
                "errors": result.errors
            }
        }
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error loading games data: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to load games data: {str(e)}")


@router.post("/validate")
async def validate_data(
    data_type: str,
    strict_mode: bool = False,
    db: Session = Depends(get_db_session)
):
    """Validate specific data type using the validation pipeline."""
    try:
        if data_type not in ['teams', 'players', 'games', 'plays']:
            raise HTTPException(status_code=400, detail="Invalid data type")
        
        # Create validation pipeline
        config = PipelineConfig(
            strict_validation=strict_mode,
            enable_cleaning=False,
            generate_report=True
        )
        pipeline = DataValidationPipeline(config)
        
        # Get data from database
        from ...models.team import TeamModel as Team
        from ...models.player import PlayerModel as Player  
        from ...models.game import GameModel as Game
        from ...models.play import PlayModel as Play
        
        model_map = {
            'teams': Team,
            'players': Player,
            'games': Game,
            'plays': Play
        }
        
        # Query data
        data_query = db.query(model_map[data_type]).limit(1000)
        records = data_query.all()
        
        if not records:
            return {
                "status": "success",
                "message": f"No {data_type} data found to validate",
                "validation_result": None
            }
        
        # Convert to DataFrame for validation
        import pandas as pd
        
        if data_type == 'teams':
            data_dict = [{
                'team_abbr': r.team_abbr,
                'team_name': r.team_name,
                'team_nick': r.team_nick,
                'team_conference': r.team_conference,
                'team_division': r.team_division
            } for r in records]
        elif data_type == 'players':
            data_dict = [{
                'player_id': r.player_id,
                'full_name': r.full_name,
                'team_abbr': r.team_abbr,
                'position': r.position,
                'height': r.height,
                'weight': r.weight,
                'age': r.age
            } for r in records]
        elif data_type == 'games':
            data_dict = [{
                'game_id': r.game_id,
                'season': r.season,
                'season_type': r.season_type,
                'home_team': r.home_team,
                'away_team': r.away_team,
                'week': r.week
            } for r in records]
        else:  # plays
            data_dict = [{
                'play_id': r.play_id,
                'game_id': r.game_id,
                'season': r.season,
                'posteam': r.posteam,
                'defteam': r.defteam,
                'play_type': r.play_type,
                'down': r.down,
                'qtr': r.qtr
            } for r in records]
        
        df = pd.DataFrame(data_dict)
        
        # Validate data
        validation_result = pipeline.validate_data(df, data_type)
        
        return {
            "status": "success",
            "data_type": data_type,
            "records_validated": len(records),
            "validation_result": validation_result.to_summary()
        }
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error validating {data_type} data: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to validate {data_type} data: {str(e)}")


@router.get("/cache/info")
async def get_cache_info():
    """Get information about data cache."""
    try:
        loader = get_data_loader()
        
        # Get cache info from client
        cache_info = loader.client.get_cache_info()
        
        return {
            "status": "success",
            "cache_enabled": cache_info["cache_enabled"],
            "cache_stats": cache_info if cache_info["cache_enabled"] else None
        }
    
    except Exception as e:
        logger.error(f"Error getting cache info: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to get cache info")


@router.delete("/cache")
async def clear_cache():
    """Clear the data cache."""
    try:
        loader = get_data_loader()
        loader.client.clear_cache()
        
        return {
            "status": "success",
            "message": "Cache cleared successfully"
        }
    
    except Exception as e:
        logger.error(f"Error clearing cache: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to clear cache")