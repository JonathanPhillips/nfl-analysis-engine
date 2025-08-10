"""Teams API endpoints."""

from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Request, Query
from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError
import logging
from pydantic import BaseModel, Field

from ...models.team import TeamModel as Team, TeamResponse
from ..dependencies import get_db_session

logger = logging.getLogger(__name__)

router = APIRouter()


class TeamList(BaseModel):
    """Schema for paginated team list response."""
    teams: List[TeamResponse] = Field(..., description="List of teams")
    total: int = Field(..., description="Total number of teams")
    limit: int = Field(..., description="Maximum number of teams returned")
    offset: int = Field(..., description="Number of teams skipped")


@router.get("/", response_model=TeamList)
async def get_teams(
    request: Request,
    limit: int = Query(32, ge=1, le=100, description="Number of teams to return"),
    offset: int = Query(0, ge=0, description="Number of teams to skip"),
    db: Session = Depends(get_db_session)
):
    """Get list of NFL teams."""
    try:
        query = db.query(Team)
        
        # Get total count
        total = query.count()
        
        # Apply pagination
        teams = query.offset(offset).limit(limit).all()
        
        return TeamList(
            teams=[TeamResponse.model_validate(team) for team in teams],
            total=total,
            limit=limit,
            offset=offset
        )
    
    except SQLAlchemyError as e:
        logger.error(f"Database error in get_teams: {str(e)}")
        raise HTTPException(status_code=500, detail="Database error")
    except Exception as e:
        logger.error(f"Unexpected error in get_teams: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/{team_abbr}", response_model=TeamResponse)
async def get_team(
    team_abbr: str,
    db: Session = Depends(get_db_session)
):
    """Get a specific team by abbreviation."""
    try:
        team = db.query(Team).filter(Team.team_abbr == team_abbr.upper()).first()
        
        if not team:
            raise HTTPException(status_code=404, detail=f"Team {team_abbr} not found")
        
        return TeamResponse.model_validate(team)
    
    except HTTPException:
        raise
    except SQLAlchemyError as e:
        logger.error(f"Database error in get_team: {str(e)}")
        raise HTTPException(status_code=500, detail="Database error")
    except Exception as e:
        logger.error(f"Unexpected error in get_team: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/{team_abbr}/stats")
async def get_team_stats(
    team_abbr: str,
    season: Optional[int] = Query(None, description="Season year"),
    db: Session = Depends(get_db_session)
):
    """Get team statistics for a specific season."""
    try:
        team = db.query(Team).filter(Team.team_abbr == team_abbr.upper()).first()
        
        if not team:
            raise HTTPException(status_code=404, detail=f"Team {team_abbr} not found")
        
        # For now, return basic team info with placeholder stats
        # TODO: Implement actual statistics calculation from games and plays
        stats = {
            "team": TeamResponse.model_validate(team),
            "season": season,
            "games_played": 0,
            "wins": 0,
            "losses": 0,
            "ties": 0,
            "points_for": 0,
            "points_against": 0,
            "message": "Statistics calculation not yet implemented"
        }
        
        return stats
    
    except HTTPException:
        raise
    except SQLAlchemyError as e:
        logger.error(f"Database error in get_team_stats: {str(e)}")
        raise HTTPException(status_code=500, detail="Database error")
    except Exception as e:
        logger.error(f"Unexpected error in get_team_stats: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")


class TeamUpdate(BaseModel):
    """Schema for team update requests."""
    team_name: Optional[str] = Field(None, description="Team name")
    team_nick: Optional[str] = Field(None, description="Team nickname")
    team_conf: Optional[str] = Field(None, description="Conference (AFC/NFC)")
    team_division: Optional[str] = Field(None, description="Division (North/South/East/West)")
    team_color: Optional[str] = Field(None, description="Primary team color")
    team_color2: Optional[str] = Field(None, description="Secondary team color")
    team_logo_espn: Optional[str] = Field(None, description="ESPN logo URL")
    team_logo_wikipedia: Optional[str] = Field(None, description="Wikipedia logo URL")


@router.put("/{team_id}", response_model=TeamResponse)
async def update_team(
    team_id: int,
    team_update: TeamUpdate,
    db: Session = Depends(get_db_session)
):
    """Update a team by ID."""
    try:
        team = db.query(Team).filter(Team.id == team_id).first()
        
        if not team:
            raise HTTPException(status_code=404, detail=f"Team with ID {team_id} not found")
        
        # Update fields that were provided
        update_data = team_update.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            if hasattr(team, field):
                setattr(team, field, value)
        
        db.commit()
        db.refresh(team)
        
        logger.info(f"Updated team {team.team_abbr} (ID: {team_id})")
        return TeamResponse.model_validate(team)
    
    except HTTPException:
        raise
    except SQLAlchemyError as e:
        logger.error(f"Database error in update_team: {str(e)}")
        db.rollback()
        raise HTTPException(status_code=500, detail="Database error")
    except Exception as e:
        logger.error(f"Unexpected error in update_team: {str(e)}")
        db.rollback()
        raise HTTPException(status_code=500, detail="Internal server error")


@router.delete("/{team_id}")
async def delete_team(
    team_id: int,
    db: Session = Depends(get_db_session)
):
    """Delete a team by ID."""
    try:
        team = db.query(Team).filter(Team.id == team_id).first()
        
        if not team:
            raise HTTPException(status_code=404, detail=f"Team with ID {team_id} not found")
        
        team_abbr = team.team_abbr
        db.delete(team)
        db.commit()
        
        logger.info(f"Deleted team {team_abbr} (ID: {team_id})")
        return {"message": f"Team {team_abbr} deleted successfully"}
    
    except HTTPException:
        raise
    except SQLAlchemyError as e:
        logger.error(f"Database error in delete_team: {str(e)}")
        db.rollback()
        raise HTTPException(status_code=500, detail="Database error")
    except Exception as e:
        logger.error(f"Unexpected error in delete_team: {str(e)}")
        db.rollback()
        raise HTTPException(status_code=500, detail="Internal server error")