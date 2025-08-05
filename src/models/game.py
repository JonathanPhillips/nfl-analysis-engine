"""Game data models compatible with nfl_data_py structure."""

from typing import Optional
from datetime import date, time
from sqlalchemy import Column, String, Integer, Date, Time, Boolean, Float, ForeignKey
from sqlalchemy.orm import relationship
from pydantic import BaseModel as PydanticBaseModel, Field, field_validator, ConfigDict
from src.models.base import BaseModel as SQLBaseModel, BasePydanticModel


class GameModel(SQLBaseModel):
    """SQLAlchemy model for NFL games.
    
    Compatible with nfl_data_py game data structure.
    Reference: https://github.com/nflverse/nfl_data_py
    """
    __tablename__ = "games"
    
    # Primary identifiers
    game_id = Column(String(20), unique=True, nullable=False, index=True)
    old_game_id = Column(String(20), index=True)  # Legacy game ID for compatibility
    
    # Game scheduling
    season = Column(Integer, nullable=False, index=True)
    season_type = Column(String(10), nullable=False, index=True)  # 'REG', 'POST', 'PRE'
    week = Column(Integer, index=True)
    game_date = Column(Date, nullable=False, index=True)
    kickoff_time = Column(Time)
    
    # Teams
    home_team = Column(String(3), ForeignKey('teams.team_abbr'), nullable=False, index=True)
    away_team = Column(String(3), ForeignKey('teams.team_abbr'), nullable=False, index=True)
    
    # Game results
    home_score = Column(Integer)
    away_score = Column(Integer)
    result = Column(Integer)  # 1 if home team won, 0 if away team won
    total_score = Column(Integer)
    
    # Game conditions
    roof = Column(String(20))  # 'dome', 'outdoors', 'closed', 'open'
    surface = Column(String(20))  # 'grass', 'fieldturf', etc.
    temp = Column(Integer)  # Temperature in Fahrenheit
    wind = Column(Integer)  # Wind speed in mph
    
    # Betting information (if available)
    home_spread = Column(Float)  # Point spread (home team perspective)
    total_line = Column(Float)  # Over/under total
    home_moneyline = Column(Integer)  # Moneyline odds
    away_moneyline = Column(Integer)
    
    # Game status
    game_finished = Column(Boolean, default=False)
    
    # Relationships
    home_team_rel = relationship("TeamModel", foreign_keys=[home_team], back_populates="home_games")
    away_team_rel = relationship("TeamModel", foreign_keys=[away_team], back_populates="away_games")
    
    def __repr__(self):
        return f"<Game {self.game_id}: {self.away_team} @ {self.home_team} ({self.game_date})>"


class GameBase(BasePydanticModel):
    """Base Pydantic model for game data."""
    game_id: str = Field(..., min_length=1, max_length=20, description="nflfastR game ID")
    season: int = Field(..., ge=1920, le=2030, description="NFL season year")
    season_type: str = Field(..., description="Season type")
    game_date: date = Field(..., description="Game date")
    home_team: str = Field(..., min_length=2, max_length=3, description="Home team abbreviation")
    away_team: str = Field(..., min_length=2, max_length=3, description="Away team abbreviation")
    
    @field_validator('game_id')
    @classmethod
    def validate_game_id(cls, v):
        """Validate game ID format."""
        if not v.strip():
            raise ValueError('Game ID cannot be empty or whitespace')
        return v.strip()
    
    @field_validator('home_team', 'away_team')
    @classmethod
    def validate_team_abbr(cls, v):
        """Validate team abbreviation format."""
        v = v.strip()
        if not v.isupper():
            raise ValueError('Team abbreviation must be uppercase')
        return v
    
    @field_validator('season_type')
    @classmethod
    def validate_season_type(cls, v):
        """Validate season type."""
        valid_types = {'REG', 'POST', 'PRE'}
        if v.upper() not in valid_types:
            raise ValueError(f'Season type must be one of: {", ".join(valid_types)}')
        return v.upper()


class GameCreate(GameBase):
    """Pydantic model for creating games."""
    old_game_id: Optional[str] = Field(None, max_length=20, description="Legacy game ID")
    week: Optional[int] = Field(None, ge=1, le=22, description="Week number (1-18 for REG, 19-22 for POST)")
    kickoff_time: Optional[time] = Field(None, description="Kickoff time")
    
    # Game results (optional until game is finished)
    home_score: Optional[int] = Field(None, ge=0, le=100, description="Home team score")
    away_score: Optional[int] = Field(None, ge=0, le=100, description="Away team score")
    result: Optional[int] = Field(None, ge=0, le=1, description="1 if home won, 0 if away won")
    total_score: Optional[int] = Field(None, ge=0, le=200, description="Total combined score")
    
    # Game conditions
    roof: Optional[str] = Field(None, max_length=20, description="Stadium roof type")
    surface: Optional[str] = Field(None, max_length=20, description="Playing surface")
    temp: Optional[int] = Field(None, ge=-20, le=120, description="Temperature in Fahrenheit")
    wind: Optional[int] = Field(None, ge=0, le=50, description="Wind speed in mph")
    
    # Betting information
    home_spread: Optional[float] = Field(None, ge=-30.0, le=30.0, description="Point spread")
    total_line: Optional[float] = Field(None, ge=20.0, le=80.0, description="Over/under total")
    home_moneyline: Optional[int] = Field(None, ge=-1000, le=1000, description="Home moneyline odds")
    away_moneyline: Optional[int] = Field(None, ge=-1000, le=1000, description="Away moneyline odds")
    
    # Game status
    game_finished: Optional[bool] = Field(False, description="Whether game is finished")
    
    @field_validator('roof')
    @classmethod
    def validate_roof(cls, v):
        """Validate roof type."""
        if v is not None:
            valid_roofs = {'dome', 'outdoors', 'closed', 'open', 'retractable'}
            if v.lower() not in valid_roofs:
                raise ValueError(f'Roof type must be one of: {", ".join(valid_roofs)}')
            return v.lower()
        return v
    
    @field_validator('surface')
    @classmethod
    def validate_surface(cls, v):
        """Validate playing surface."""
        if v is not None:
            valid_surfaces = {'grass', 'fieldturf', 'artificial', 'turf', 'astroturf'}
            if v.lower() not in valid_surfaces:
                # Allow other surfaces but normalize common ones
                return v.lower()
            return v.lower()
        return v
    
    @field_validator('week', mode='after')
    @classmethod
    def validate_week(cls, v, info=None):
        """Validate week number based on season type."""
        # For now, just validate basic range - context validation can be done at model level
        if v is not None and not (1 <= v <= 22):
            raise ValueError('Week must be between 1 and 22')
        return v


class GameUpdate(PydanticBaseModel):
    """Pydantic model for updating games."""
    old_game_id: Optional[str] = Field(None, max_length=20)
    week: Optional[int] = Field(None, ge=1, le=22)
    kickoff_time: Optional[time] = None
    home_score: Optional[int] = Field(None, ge=0, le=100)
    away_score: Optional[int] = Field(None, ge=0, le=100)
    result: Optional[int] = Field(None, ge=0, le=1)
    total_score: Optional[int] = Field(None, ge=0, le=200)
    roof: Optional[str] = Field(None, max_length=20)
    surface: Optional[str] = Field(None, max_length=20)
    temp: Optional[int] = Field(None, ge=-20, le=120)
    wind: Optional[int] = Field(None, ge=0, le=50)
    home_spread: Optional[float] = Field(None, ge=-30.0, le=30.0)
    total_line: Optional[float] = Field(None, ge=20.0, le=80.0)
    home_moneyline: Optional[int] = Field(None, ge=-1000, le=1000)
    away_moneyline: Optional[int] = Field(None, ge=-1000, le=1000)
    game_finished: Optional[bool] = None
    
    @field_validator('roof')
    @classmethod
    def validate_roof(cls, v):
        """Validate roof type."""
        if v is not None:
            valid_roofs = {'dome', 'outdoors', 'closed', 'open', 'retractable'}
            if v.lower() not in valid_roofs:
                raise ValueError(f'Roof type must be one of: {", ".join(valid_roofs)}')
            return v.lower()
        return v


class GameResponse(GameBase):
    """Pydantic model for game responses."""
    id: int
    old_game_id: Optional[str] = None
    week: Optional[int] = None
    kickoff_time: Optional[time] = None
    home_score: Optional[int] = None
    away_score: Optional[int] = None
    result: Optional[int] = None
    total_score: Optional[int] = None
    roof: Optional[str] = None
    surface: Optional[str] = None
    temp: Optional[int] = None
    wind: Optional[int] = None
    home_spread: Optional[float] = None
    total_line: Optional[float] = None
    home_moneyline: Optional[int] = None
    away_moneyline: Optional[int] = None
    game_finished: Optional[bool] = None
    
    model_config = ConfigDict(from_attributes=True)


# Utility functions for game data
def calculate_result(home_score: Optional[int], away_score: Optional[int]) -> Optional[int]:
    """Calculate game result based on scores.
    
    Args:
        home_score: Home team score
        away_score: Away team score
        
    Returns:
        1 if home team won, 0 if away team won, None if scores not available
    """
    if home_score is None or away_score is None:
        return None
    
    return 1 if home_score > away_score else 0


def calculate_total_score(home_score: Optional[int], away_score: Optional[int]) -> Optional[int]:
    """Calculate total combined score.
    
    Args:
        home_score: Home team score
        away_score: Away team score
        
    Returns:
        Combined score or None if scores not available
    """
    if home_score is None or away_score is None:
        return None
    
    return home_score + away_score


def get_season_week_range(season_type: str) -> tuple[int, int]:
    """Get valid week range for season type.
    
    Args:
        season_type: Type of season ('REG', 'POST', 'PRE')
        
    Returns:
        Tuple of (min_week, max_week)
    """
    if season_type == 'REG':
        return (1, 18)
    elif season_type == 'POST':
        return (19, 22)
    elif season_type == 'PRE':
        return (1, 4)
    else:
        raise ValueError(f"Invalid season type: {season_type}")


def format_game_description(away_team: str, home_team: str, game_date: date, 
                          home_score: Optional[int] = None, 
                          away_score: Optional[int] = None) -> str:
    """Format a human-readable game description.
    
    Args:
        away_team: Away team abbreviation
        home_team: Home team abbreviation
        game_date: Game date
        home_score: Home team score (optional)
        away_score: Away team score (optional)
        
    Returns:
        Formatted game description
    """
    base_description = f"{away_team} @ {home_team} ({game_date.strftime('%Y-%m-%d')})"
    
    if home_score is not None and away_score is not None:
        winner = home_team if home_score > away_score else away_team
        base_description += f" - {winner} wins {max(home_score, away_score)}-{min(home_score, away_score)}"
    
    return base_description


def is_game_overtime(home_score: Optional[int], away_score: Optional[int]) -> bool:
    """Determine if game likely went to overtime based on score.
    
    This is a heuristic based on common NFL scoring patterns.
    
    Args:
        home_score: Home team score
        away_score: Away team score
        
    Returns:
        True if game likely went to overtime
    """
    if home_score is None or away_score is None:
        return False
    
    total_score = home_score + away_score
    score_diff = abs(home_score - away_score)
    
    # Common overtime indicators:
    # - Total score unusually high for close game
    # - Specific overtime-friendly scores
    overtime_scores = {
        (27, 24), (30, 27), (33, 30), (24, 21), (31, 28),
        (29, 26), (26, 23), (23, 20), (34, 31), (28, 25)
    }
    
    score_tuple = (max(home_score, away_score), min(home_score, away_score))
    
    return (score_tuple in overtime_scores or 
            (total_score > 45 and score_diff <= 7) or
            (score_diff == 3 and total_score > 50))