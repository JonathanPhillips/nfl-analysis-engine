"""Play data models compatible with nfl_data_py structure."""

from typing import Optional
from decimal import Decimal
from sqlalchemy import Column, String, Integer, Boolean, Text, Numeric, ForeignKey, UniqueConstraint
from sqlalchemy.orm import relationship
from pydantic import BaseModel as PydanticBaseModel, Field, field_validator, ConfigDict
from src.models.base import BaseModel as SQLBaseModel, BasePydanticModel


class PlayModel(SQLBaseModel):
    """SQLAlchemy model for NFL plays.
    
    Compatible with nfl_data_py play-by-play data structure.
    Reference: https://github.com/nflverse/nfl_data_py
    """
    __tablename__ = "plays"
    
    # Primary identifiers
    play_id = Column(String(30), nullable=False, index=True)
    game_id = Column(String(20), ForeignKey('games.game_id'), nullable=False, index=True)
    
    # Game context
    season = Column(Integer, nullable=False, index=True)
    week = Column(Integer, index=True)
    posteam = Column(String(3), ForeignKey('teams.team_abbr'), index=True)  # Possession team
    defteam = Column(String(3), ForeignKey('teams.team_abbr'), index=True)  # Defense team
    
    # Game situation
    qtr = Column(Integer)  # Quarter (1-5, 5 for OT)
    game_seconds_remaining = Column(Integer)
    half_seconds_remaining = Column(Integer)
    game_half = Column(String(10))  # 'Half1', 'Half2', 'Overtime'
    
    # Field position
    yardline_100 = Column(Integer)  # Yards from opponent's goal line
    ydstogo = Column(Integer)  # Yards to go for first down
    down = Column(Integer)  # Down (1-4)
    
    # Play details
    play_type = Column(String(20), index=True)  # 'pass', 'run', 'punt', 'field_goal', etc.
    desc = Column(Text)  # Play description
    yards_gained = Column(Integer)
    
    # Score before play
    posteam_score = Column(Integer)
    defteam_score = Column(Integer)
    score_differential = Column(Integer)
    
    # Advanced metrics (from nflfastR)
    ep = Column(Numeric(6, 3))  # Expected Points
    epa = Column(Numeric(6, 3))  # Expected Points Added
    wp = Column(Numeric(8, 6))  # Win Probability
    wpa = Column(Numeric(8, 6))  # Win Probability Added
    
    # Passing metrics
    cpoe = Column(Numeric(6, 3))  # Completion Probability Over Expected
    pass_location = Column(String(20))  # 'left', 'middle', 'right'
    air_yards = Column(Integer)
    yards_after_catch = Column(Integer)
    
    # Player involvement
    passer_player_id = Column(String(20), ForeignKey('players.player_id'))
    receiver_player_id = Column(String(20), ForeignKey('players.player_id'))
    rusher_player_id = Column(String(20), ForeignKey('players.player_id'))
    
    # Play result flags
    touchdown = Column(Boolean, default=False)
    pass_touchdown = Column(Boolean, default=False)
    rush_touchdown = Column(Boolean, default=False)
    interception = Column(Boolean, default=False)
    fumble = Column(Boolean, default=False)
    safety = Column(Boolean, default=False)
    penalty = Column(Boolean, default=False)
    first_down = Column(Boolean, default=False)  # Whether play resulted in first down
    
    # Table constraints - unique play within each game
    __table_args__ = (
        UniqueConstraint('game_id', 'play_id', name='uq_play_game_play_id'),
    )
    
    # Relationships
    game = relationship("GameModel", back_populates="plays")
    poss_team = relationship("TeamModel", foreign_keys=[posteam], back_populates="offensive_plays")
    def_team = relationship("TeamModel", foreign_keys=[defteam], back_populates="defensive_plays")
    passer = relationship("PlayerModel", foreign_keys=[passer_player_id])
    receiver = relationship("PlayerModel", foreign_keys=[receiver_player_id])
    rusher = relationship("PlayerModel", foreign_keys=[rusher_player_id])
    
    def __repr__(self):
        return f"<Play {self.play_id}: {self.posteam} {self.play_type} for {self.yards_gained} yards>"


class PlayBase(BasePydanticModel):
    """Base Pydantic model for play data."""
    play_id: str = Field(..., min_length=1, max_length=30, description="nflfastR play ID")
    game_id: str = Field(..., min_length=1, max_length=20, description="Game ID")
    season: int = Field(..., ge=1920, le=2030, description="NFL season year")
    
    @field_validator('play_id', 'game_id')
    @classmethod
    def validate_ids(cls, v):
        """Validate ID format."""
        if not v.strip():
            raise ValueError('ID cannot be empty or whitespace')
        return v.strip()


class PlayCreate(PlayBase):
    """Pydantic model for creating plays."""
    week: Optional[int] = Field(None, ge=1, le=22, description="Week number")
    posteam: Optional[str] = Field(None, min_length=2, max_length=3, description="Possession team")
    defteam: Optional[str] = Field(None, min_length=2, max_length=3, description="Defense team")
    
    # Game situation
    qtr: Optional[int] = Field(None, ge=1, le=5, description="Quarter (1-5, 5 for OT)")
    game_seconds_remaining: Optional[int] = Field(None, ge=0, le=3600, description="Game seconds remaining")
    half_seconds_remaining: Optional[int] = Field(None, ge=0, le=1800, description="Half seconds remaining")
    game_half: Optional[str] = Field(None, max_length=10, description="Game half")
    
    # Field position
    yardline_100: Optional[int] = Field(None, ge=1, le=99, description="Yards from opponent goal")
    ydstogo: Optional[int] = Field(None, ge=1, le=99, description="Yards to go")
    down: Optional[int] = Field(None, ge=1, le=4, description="Down")
    
    # Play details
    play_type: Optional[str] = Field(None, max_length=20, description="Play type")
    desc: Optional[str] = Field(None, description="Play description")
    yards_gained: Optional[int] = Field(None, ge=-99, le=99, description="Yards gained on play")
    
    # Score before play
    posteam_score: Optional[int] = Field(None, ge=0, le=100, description="Possession team score")
    defteam_score: Optional[int] = Field(None, ge=0, le=100, description="Defense team score")
    score_differential: Optional[int] = Field(None, ge=-100, le=100, description="Score differential")
    
    # Advanced metrics
    ep: Optional[float] = Field(None, ge=-10.0, le=10.0, description="Expected Points")
    epa: Optional[float] = Field(None, ge=-15.0, le=15.0, description="Expected Points Added")
    wp: Optional[float] = Field(None, ge=0.0, le=1.0, description="Win Probability")
    wpa: Optional[float] = Field(None, ge=-1.0, le=1.0, description="Win Probability Added")
    
    # Passing metrics
    cpoe: Optional[float] = Field(None, ge=-1.0, le=1.0, description="Completion Probability Over Expected")
    pass_location: Optional[str] = Field(None, max_length=20, description="Pass location")
    air_yards: Optional[int] = Field(None, ge=-20, le=80, description="Air yards")
    yards_after_catch: Optional[int] = Field(None, ge=0, le=99, description="Yards after catch")
    
    # Player involvement
    passer_player_id: Optional[str] = Field(None, max_length=20, description="Passer player ID")
    receiver_player_id: Optional[str] = Field(None, max_length=20, description="Receiver player ID")
    rusher_player_id: Optional[str] = Field(None, max_length=20, description="Rusher player ID")
    
    # Play result flags
    touchdown: Optional[bool] = Field(False, description="Touchdown scored")
    pass_touchdown: Optional[bool] = Field(False, description="Passing touchdown")
    rush_touchdown: Optional[bool] = Field(False, description="Rushing touchdown")
    interception: Optional[bool] = Field(False, description="Interception thrown")
    fumble: Optional[bool] = Field(False, description="Fumble occurred")
    safety: Optional[bool] = Field(False, description="Safety scored")
    penalty: Optional[bool] = Field(False, description="Penalty occurred")
    
    @field_validator('posteam', 'defteam')
    @classmethod
    def validate_team_abbr(cls, v):
        """Validate team abbreviation format."""
        if v is not None:
            v = v.strip()
            if not v.isupper():
                raise ValueError('Team abbreviation must be uppercase')
        return v
    
    @field_validator('play_type')
    @classmethod
    def validate_play_type(cls, v):
        """Validate play type."""
        if v is not None:
            valid_types = {
                'pass', 'run', 'punt', 'field_goal', 'kickoff', 'extra_point',
                'two_point_conversion', 'qb_kneel', 'qb_spike', 'timeout',
                'no_play', 'end_period', 'penalty'
            }
            if v.lower() not in valid_types and v.strip():
                # Allow other play types but normalize common ones
                return v.lower()
            return v.lower() if v else v
        return v
    
    @field_validator('pass_location')
    @classmethod
    def validate_pass_location(cls, v):
        """Validate pass location."""
        if v is not None:
            valid_locations = {'left', 'middle', 'right'}
            if v.lower() not in valid_locations:
                raise ValueError(f'Pass location must be one of: {", ".join(valid_locations)}')
            return v.lower()
        return v
    
    @field_validator('game_half')
    @classmethod
    def validate_game_half(cls, v):
        """Validate game half."""
        if v is not None:
            valid_halves = {'half1', 'half2', 'overtime'}
            if v.lower() not in valid_halves:
                raise ValueError(f'Game half must be one of: {", ".join(valid_halves)}')
            return v.lower()
        return v


class PlayUpdate(PydanticBaseModel):
    """Pydantic model for updating plays."""
    week: Optional[int] = Field(None, ge=1, le=22)
    posteam: Optional[str] = Field(None, min_length=2, max_length=3)
    defteam: Optional[str] = Field(None, min_length=2, max_length=3)
    qtr: Optional[int] = Field(None, ge=1, le=5)
    game_seconds_remaining: Optional[int] = Field(None, ge=0, le=3600)
    half_seconds_remaining: Optional[int] = Field(None, ge=0, le=1800)
    game_half: Optional[str] = Field(None, max_length=10)
    yardline_100: Optional[int] = Field(None, ge=1, le=99)
    ydstogo: Optional[int] = Field(None, ge=1, le=99)
    down: Optional[int] = Field(None, ge=1, le=4)
    play_type: Optional[str] = Field(None, max_length=20)
    desc: Optional[str] = None
    yards_gained: Optional[int] = Field(None, ge=-99, le=99)
    posteam_score: Optional[int] = Field(None, ge=0, le=100)
    defteam_score: Optional[int] = Field(None, ge=0, le=100)
    score_differential: Optional[int] = Field(None, ge=-100, le=100)
    ep: Optional[float] = Field(None, ge=-10.0, le=10.0)
    epa: Optional[float] = Field(None, ge=-15.0, le=15.0)
    wp: Optional[float] = Field(None, ge=0.0, le=1.0)
    wpa: Optional[float] = Field(None, ge=-1.0, le=1.0)
    cpoe: Optional[float] = Field(None, ge=-1.0, le=1.0)
    pass_location: Optional[str] = Field(None, max_length=20)
    air_yards: Optional[int] = Field(None, ge=-20, le=80)
    yards_after_catch: Optional[int] = Field(None, ge=0, le=99)
    passer_player_id: Optional[str] = Field(None, max_length=20)
    receiver_player_id: Optional[str] = Field(None, max_length=20)
    rusher_player_id: Optional[str] = Field(None, max_length=20)
    touchdown: Optional[bool] = None
    pass_touchdown: Optional[bool] = None
    rush_touchdown: Optional[bool] = None
    interception: Optional[bool] = None
    fumble: Optional[bool] = None
    safety: Optional[bool] = None
    penalty: Optional[bool] = None
    
    @field_validator('posteam', 'defteam')
    @classmethod
    def validate_team_abbr(cls, v):
        """Validate team abbreviation format."""
        if v is not None and not v.isupper():
            raise ValueError('Team abbreviation must be uppercase')
        return v


class PlayResponse(PlayBase):
    """Pydantic model for play responses."""
    id: int
    week: Optional[int] = None
    posteam: Optional[str] = None
    defteam: Optional[str] = None
    qtr: Optional[int] = None
    game_seconds_remaining: Optional[int] = None
    half_seconds_remaining: Optional[int] = None
    game_half: Optional[str] = None
    yardline_100: Optional[int] = None
    ydstogo: Optional[int] = None
    down: Optional[int] = None
    play_type: Optional[str] = None
    desc: Optional[str] = None
    yards_gained: Optional[int] = None
    posteam_score: Optional[int] = None
    defteam_score: Optional[int] = None
    score_differential: Optional[int] = None
    ep: Optional[float] = None
    epa: Optional[float] = None
    wp: Optional[float] = None
    wpa: Optional[float] = None
    cpoe: Optional[float] = None
    pass_location: Optional[str] = None
    air_yards: Optional[int] = None
    yards_after_catch: Optional[int] = None
    passer_player_id: Optional[str] = None
    receiver_player_id: Optional[str] = None
    rusher_player_id: Optional[str] = None
    touchdown: Optional[bool] = None
    pass_touchdown: Optional[bool] = None
    rush_touchdown: Optional[bool] = None
    interception: Optional[bool] = None
    fumble: Optional[bool] = None
    safety: Optional[bool] = None
    penalty: Optional[bool] = None
    
    model_config = ConfigDict(from_attributes=True)


# Utility functions for play data analysis
def calculate_play_success(epa: Optional[float], play_type: Optional[str]) -> Optional[bool]:
    """Determine if a play was successful based on EPA.
    
    Args:
        epa: Expected Points Added
        play_type: Type of play
        
    Returns:
        True if play was successful, False if not, None if cannot determine
    """
    if epa is None:
        return None
    
    # EPA > 0 generally indicates success
    if play_type in ['pass', 'run']:
        return epa > 0
    elif play_type in ['punt', 'field_goal']:
        # Different success criteria for special teams
        return epa > -0.5
    else:
        return epa > 0


def get_down_distance_situation(down: Optional[int], ydstogo: Optional[int]) -> Optional[str]:
    """Categorize down and distance situation.
    
    Args:
        down: Down number
        ydstogo: Yards to go
        
    Returns:
        Situation category string
    """
    if down is None or ydstogo is None:
        return None
    
    if down == 1:
        return "1st_down"
    elif down == 2:
        if ydstogo <= 3:
            return "2nd_short"
        elif ydstogo >= 8:
            return "2nd_long"
        else:
            return "2nd_medium"
    elif down == 3:
        if ydstogo <= 3:
            return "3rd_short"
        elif ydstogo >= 8:
            return "3rd_long"
        else:
            return "3rd_medium"
    elif down == 4:
        return "4th_down"
    else:
        return "unknown"


def calculate_field_position_value(yardline_100: Optional[int]) -> Optional[str]:
    """Categorize field position value.
    
    Args:
        yardline_100: Yards from opponent's goal line
        
    Returns:
        Field position category
    """
    if yardline_100 is None:
        return None
    
    if yardline_100 <= 20:
        return "red_zone"
    elif yardline_100 <= 40:
        return "plus_territory"
    elif yardline_100 <= 60:
        return "midfield"
    elif yardline_100 <= 80:
        return "minus_territory"
    else:
        return "own_territory"


def is_explosive_play(yards_gained: Optional[int], play_type: Optional[str]) -> bool:
    """Determine if play was explosive based on yards gained.
    
    Args:
        yards_gained: Yards gained on play
        play_type: Type of play
        
    Returns:
        True if explosive play
    """
    if yards_gained is None or play_type is None:
        return False
    
    # Standard explosive play definitions
    if play_type == 'pass':
        return yards_gained >= 20
    elif play_type == 'run':
        return yards_gained >= 15
    else:
        return False


def get_play_clock_situation(game_seconds_remaining: Optional[int], qtr: Optional[int]) -> Optional[str]:
    """Categorize game clock situation.
    
    Args:
        game_seconds_remaining: Seconds remaining in game
        qtr: Quarter
        
    Returns:
        Clock situation category
    """
    if game_seconds_remaining is None or qtr is None:
        return None
    
    if qtr <= 2:  # First half
        if game_seconds_remaining <= 120:  # 2 minutes
            return "first_half_two_minute"
        else:
            return "first_half_normal"
    else:  # Second half
        if game_seconds_remaining <= 120:  # 2 minutes
            return "second_half_two_minute"
        elif game_seconds_remaining <= 300:  # 5 minutes
            return "second_half_late"
        else:
            return "second_half_normal"


def calculate_leverage_index(wp: Optional[float], wpa: Optional[float]) -> Optional[float]:
    """Calculate leverage index for the play situation.
    
    Leverage index measures how much the play outcome affects win probability.
    
    Args:
        wp: Win probability before play
        wpa: Win probability added by play
        
    Returns:
        Leverage index (higher = more critical situation)
    """
    if wp is None or wpa is None or wp <= 0 or wp >= 1:
        return None
    
    # Leverage is highest when win probability is near 50%
    # and the play has high WPA potential
    leverage = abs(wpa) / (wp * (1 - wp))
    return min(leverage, 10.0)  # Cap at reasonable maximum