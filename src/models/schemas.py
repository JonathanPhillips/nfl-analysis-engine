"""Pydantic schemas for API request/response models."""

from typing import List, Dict, Any, Optional, Union
from pydantic import BaseModel, Field, ConfigDict
from datetime import date


class BaseResponse(BaseModel):
    """Base response model with status and message."""
    status: str = Field(..., description="Response status")
    message: str = Field(..., description="Response message")
    

class AdvancedMetricsResponse(BaseResponse):
    """Response model for advanced play metrics."""
    data: Dict[str, Union[float, bool]] = Field(..., description="Advanced metrics data")


class TeamInsightsResponse(BaseResponse):
    """Response model for team insights."""
    data: Dict[str, Any] = Field(..., description="Team insights data")


class GameInsightResponse(BaseResponse):
    """Response model for game insights."""
    data: Dict[str, Any] = Field(..., description="Game insights data")


class LeagueLeadersResponse(BaseResponse):
    """Response model for league leaders."""
    data: Dict[str, Any] = Field(..., description="League leaders data")


class TeamComparisonResponse(BaseResponse):
    """Response model for team comparison."""
    data: Dict[str, Any] = Field(..., description="Team comparison data")


class SeasonNarrativeResponse(BaseResponse):
    """Response model for season narrative."""
    data: Dict[str, Any] = Field(..., description="Season narrative data")


# Request models for insights
class PlayMetricsRequest(BaseModel):
    """Request model for calculating play metrics."""
    down: int = Field(..., ge=1, le=4, description="Current down")
    ydstogo: int = Field(..., ge=0, description="Yards to go for first down")
    yardline_100: int = Field(..., ge=0, le=100, description="Distance to goal line")
    qtr: int = Field(..., ge=1, le=4, description="Quarter")
    game_seconds_remaining: int = Field(..., ge=0, le=3600, description="Seconds remaining in game")
    score_differential: int = Field(..., description="Score differential (positive if offense leading)")
    timeouts_remaining: int = Field(..., ge=0, le=3, description="Timeouts remaining")
    play_type: str = Field(..., description="Type of play")
    yards_gained: int = Field(0, description="Yards gained on play")
    touchdown: bool = Field(False, description="Whether play resulted in touchdown")
    interception: bool = Field(False, description="Whether play resulted in interception")
    fumble_lost: bool = Field(False, description="Whether play resulted in lost fumble")

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "down": 3,
                "ydstogo": 7,
                "yardline_100": 25,
                "qtr": 4,
                "game_seconds_remaining": 180,
                "score_differential": -3,
                "timeouts_remaining": 2,
                "play_type": "pass",
                "yards_gained": 12,
                "touchdown": False,
                "interception": False,
                "fumble_lost": False
            }
        }
    )


# Team schema
class TeamBase(BaseModel):
    """Base team schema."""
    team_abbr: str = Field(..., max_length=3, description="Team abbreviation")
    team_name: str = Field(..., description="Team city name")
    team_nick: str = Field(..., description="Team nickname")
    conference: str = Field(..., description="Conference (AFC/NFC)")
    division: str = Field(..., description="Division")


class TeamCreate(TeamBase):
    """Schema for creating a team."""
    pass


class TeamUpdate(BaseModel):
    """Schema for updating a team."""
    team_name: Optional[str] = None
    team_nick: Optional[str] = None
    conference: Optional[str] = None
    division: Optional[str] = None


class Team(TeamBase):
    """Schema for team response."""
    id: int
    is_active: bool = True

    model_config = ConfigDict(from_attributes=True)


# Player schema
class PlayerBase(BaseModel):
    """Base player schema."""
    player_id: str = Field(..., description="Unique player identifier")
    player_name: str = Field(..., description="Player full name")
    position: Optional[str] = Field(None, description="Player position")
    team_abbr: Optional[str] = Field(None, description="Current team abbreviation")
    height: Optional[int] = Field(None, description="Height in inches")
    weight: Optional[int] = Field(None, description="Weight in pounds")
    college: Optional[str] = Field(None, description="College attended")
    rookie_year: Optional[int] = Field(None, description="Rookie season year")
    years_pro: Optional[int] = Field(None, description="Years of professional experience")


class PlayerCreate(PlayerBase):
    """Schema for creating a player."""
    pass


class PlayerUpdate(BaseModel):
    """Schema for updating a player."""
    player_name: Optional[str] = None
    position: Optional[str] = None
    team_abbr: Optional[str] = None
    height: Optional[int] = None
    weight: Optional[int] = None
    college: Optional[str] = None
    rookie_year: Optional[int] = None
    years_pro: Optional[int] = None


class Player(PlayerBase):
    """Schema for player response."""
    id: int
    is_active: bool = True

    model_config = ConfigDict(from_attributes=True)


# Game schema
class GameBase(BaseModel):
    """Base game schema."""
    game_id: str = Field(..., description="Unique game identifier")
    season: int = Field(..., description="Season year")
    week: int = Field(..., description="Week number")
    game_type: str = Field(..., description="Game type (REG, POST, etc.)")
    game_date: date = Field(..., description="Game date")
    home_team: str = Field(..., description="Home team abbreviation")
    away_team: str = Field(..., description="Away team abbreviation")


class GameCreate(GameBase):
    """Schema for creating a game."""
    home_score: Optional[int] = None
    away_score: Optional[int] = None
    total_yards_home: Optional[int] = None
    total_yards_away: Optional[int] = None
    turnovers_home: Optional[int] = None
    turnovers_away: Optional[int] = None
    penalties_home: Optional[int] = None
    penalties_away: Optional[int] = None
    time_of_possession_home: Optional[str] = None
    time_of_possession_away: Optional[str] = None


class GameUpdate(BaseModel):
    """Schema for updating a game."""
    home_score: Optional[int] = None
    away_score: Optional[int] = None
    total_yards_home: Optional[int] = None
    total_yards_away: Optional[int] = None
    turnovers_home: Optional[int] = None
    turnovers_away: Optional[int] = None
    penalties_home: Optional[int] = None
    penalties_away: Optional[int] = None
    time_of_possession_home: Optional[str] = None
    time_of_possession_away: Optional[str] = None


class Game(GameBase):
    """Schema for game response."""
    id: int
    home_score: Optional[int] = None
    away_score: Optional[int] = None
    total_yards_home: Optional[int] = None
    total_yards_away: Optional[int] = None
    turnovers_home: Optional[int] = None
    turnovers_away: Optional[int] = None
    penalties_home: Optional[int] = None
    penalties_away: Optional[int] = None
    time_of_possession_home: Optional[str] = None
    time_of_possession_away: Optional[str] = None
    is_active: bool = True

    model_config = ConfigDict(from_attributes=True)


# Play schema
class PlayBase(BaseModel):
    """Base play schema."""
    play_id: str = Field(..., description="Unique play identifier")
    game_id: str = Field(..., description="Game identifier")
    season: int = Field(..., description="Season year")
    week: int = Field(..., description="Week number")
    down: Optional[int] = Field(None, description="Down number")
    ydstogo: Optional[int] = Field(None, description="Yards to go")
    yardline_100: Optional[int] = Field(None, description="Yards from goal line")
    qtr: Optional[int] = Field(None, description="Quarter")
    posteam: Optional[str] = Field(None, description="Possession team")
    defteam: Optional[str] = Field(None, description="Defensive team")


class PlayCreate(PlayBase):
    """Schema for creating a play."""
    desc: Optional[str] = None
    play_type: Optional[str] = None
    yards_gained: Optional[int] = None
    touchdown: Optional[bool] = None
    pass_attempt: Optional[bool] = None
    rush_attempt: Optional[bool] = None
    complete_pass: Optional[bool] = None
    passer_player_id: Optional[str] = None
    rusher_player_id: Optional[str] = None
    receiver_player_id: Optional[str] = None


class PlayUpdate(BaseModel):
    """Schema for updating a play."""
    desc: Optional[str] = None
    play_type: Optional[str] = None
    yards_gained: Optional[int] = None
    touchdown: Optional[bool] = None
    pass_attempt: Optional[bool] = None
    rush_attempt: Optional[bool] = None
    complete_pass: Optional[bool] = None
    passer_player_id: Optional[str] = None
    rusher_player_id: Optional[str] = None
    receiver_player_id: Optional[str] = None


class Play(PlayBase):
    """Schema for play response."""
    id: int
    desc: Optional[str] = None
    play_type: Optional[str] = None
    yards_gained: Optional[int] = None
    touchdown: Optional[bool] = None
    pass_attempt: Optional[bool] = None
    rush_attempt: Optional[bool] = None
    complete_pass: Optional[bool] = None
    passer_player_id: Optional[str] = None
    rusher_player_id: Optional[str] = None
    receiver_player_id: Optional[str] = None
    is_active: bool = True

    model_config = ConfigDict(from_attributes=True)


# Prediction schemas
class PredictionRequest(BaseModel):
    """Request model for game prediction."""
    home_team: str = Field(..., description="Home team abbreviation")
    away_team: str = Field(..., description="Away team abbreviation")
    game_date: date = Field(..., description="Game date")
    season: int = Field(..., description="Season year")

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "home_team": "KC",
                "away_team": "SF", 
                "game_date": "2024-02-11",
                "season": 2023
            }
        }
    )


class PredictionResponse(BaseResponse):
    """Response model for game prediction."""
    data: Dict[str, Any] = Field(..., description="Prediction data including probabilities and confidence")


# Vegas lines schemas
class VegasLineRequest(BaseModel):
    """Request model for Vegas line validation."""
    home_team: str = Field(..., description="Home team abbreviation")
    away_team: str = Field(..., description="Away team abbreviation")
    spread: float = Field(..., description="Point spread (positive favors home)")
    over_under: float = Field(..., description="Over/under total points")
    moneyline_home: Optional[int] = Field(None, description="Home team moneyline")
    moneyline_away: Optional[int] = Field(None, description="Away team moneyline")


class VegasLineResponse(BaseResponse):
    """Response model for Vegas line validation."""
    data: Dict[str, Any] = Field(..., description="Vegas line analysis and value betting recommendations")