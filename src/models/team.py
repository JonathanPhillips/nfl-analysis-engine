"""Team data models compatible with nfl_data_py structure."""

from typing import Optional, List
from sqlalchemy import Column, String, Integer, Float, ForeignKey
from sqlalchemy.orm import relationship
from pydantic import BaseModel as PydanticBaseModel, Field, field_validator, ConfigDict
from src.models.base import BaseModel as SQLBaseModel, BasePydanticModel


class TeamModel(SQLBaseModel):
    """SQLAlchemy model for NFL teams.
    
    Compatible with nfl_data_py team data structure.
    Reference: https://github.com/nflverse/nfl_data_py
    """
    __tablename__ = "teams"
    
    # Primary identifiers
    team_abbr = Column(String(3), unique=True, nullable=False, index=True)  # e.g., "SF", "KC"
    team_name = Column(String(50), nullable=False)  # e.g., "San Francisco"
    team_nick = Column(String(50), nullable=False)  # e.g., "49ers"
    team_conf = Column(String(3), nullable=False)   # "AFC" or "NFC"
    team_division = Column(String(10), nullable=False)  # "North", "South", "East", "West"
    
    # Team colors and branding
    team_color = Column(String(7))      # Primary color hex code
    team_color2 = Column(String(7))     # Secondary color hex code
    team_color3 = Column(String(7))     # Tertiary color hex code
    team_color4 = Column(String(7))     # Quaternary color hex code
    team_logo_espn = Column(String(255))  # ESPN logo URL
    team_logo_wikipedia = Column(String(255))  # Wikipedia logo URL
    
    # Geographic information
    team_city = Column(String(50))
    team_wordmark = Column(String(255))
    
    # Relationships
    players = relationship("PlayerModel", back_populates="team")
    
    def __repr__(self):
        return f"<Team {self.team_abbr}: {self.team_name} {self.team_nick}>"


class TeamBase(BasePydanticModel):
    """Base Pydantic model for team data."""
    team_abbr: str = Field(..., min_length=2, max_length=3, description="Team abbreviation")
    team_name: str = Field(..., min_length=1, max_length=50, description="Team city name")
    team_nick: str = Field(..., min_length=1, max_length=50, description="Team nickname")
    team_conf: str = Field(..., pattern="^(AFC|NFC)$", description="Conference")
    team_division: str = Field(..., pattern="^(North|South|East|West)$", description="Division")
    
    @field_validator('team_abbr')
    @classmethod
    def validate_team_abbr(cls, v):
        """Validate team abbreviation format."""
        if not v.isupper():
            raise ValueError('Team abbreviation must be uppercase')
        return v
    
    @field_validator('team_conf')
    @classmethod
    def validate_conference(cls, v):
        """Validate conference value."""
        if v not in ['AFC', 'NFC']:
            raise ValueError('Conference must be AFC or NFC')
        return v
    
    @field_validator('team_division')
    @classmethod
    def validate_division(cls, v):
        """Validate division value."""
        if v not in ['North', 'South', 'East', 'West']:
            raise ValueError('Division must be North, South, East, or West')
        return v


class TeamCreate(TeamBase):
    """Pydantic model for creating teams."""
    team_color: Optional[str] = Field(None, pattern="^#[0-9A-Fa-f]{6}$", description="Primary color hex")
    team_color2: Optional[str] = Field(None, pattern="^#[0-9A-Fa-f]{6}$", description="Secondary color hex")
    team_color3: Optional[str] = Field(None, pattern="^#[0-9A-Fa-f]{6}$", description="Tertiary color hex")
    team_color4: Optional[str] = Field(None, pattern="^#[0-9A-Fa-f]{6}$", description="Quaternary color hex")
    team_logo_espn: Optional[str] = Field(None, max_length=255, description="ESPN logo URL")
    team_logo_wikipedia: Optional[str] = Field(None, max_length=255, description="Wikipedia logo URL")
    team_city: Optional[str] = Field(None, max_length=50, description="Team city")
    team_wordmark: Optional[str] = Field(None, max_length=255, description="Team wordmark URL")


class TeamUpdate(PydanticBaseModel):
    """Pydantic model for updating teams."""
    team_name: Optional[str] = Field(None, min_length=1, max_length=50)
    team_nick: Optional[str] = Field(None, min_length=1, max_length=50)
    team_conf: Optional[str] = Field(None, pattern="^(AFC|NFC)$")
    team_division: Optional[str] = Field(None, pattern="^(North|South|East|West)$")
    team_color: Optional[str] = Field(None, pattern="^#[0-9A-Fa-f]{6}$")
    team_color2: Optional[str] = Field(None, pattern="^#[0-9A-Fa-f]{6}$")
    team_color3: Optional[str] = Field(None, pattern="^#[0-9A-Fa-f]{6}$")
    team_color4: Optional[str] = Field(None, pattern="^#[0-9A-Fa-f]{6}$")
    team_logo_espn: Optional[str] = Field(None, max_length=255)
    team_logo_wikipedia: Optional[str] = Field(None, max_length=255)
    team_city: Optional[str] = Field(None, max_length=50)
    team_wordmark: Optional[str] = Field(None, max_length=255)


class TeamResponse(TeamBase):
    """Pydantic model for team responses."""
    id: int
    team_color: Optional[str] = None
    team_color2: Optional[str] = None
    team_color3: Optional[str] = None
    team_color4: Optional[str] = None
    team_logo_espn: Optional[str] = None
    team_logo_wikipedia: Optional[str] = None
    team_city: Optional[str] = None
    team_wordmark: Optional[str] = None
    
    model_config = ConfigDict(from_attributes=True)


# Constants for validation and reference
NFL_TEAMS = {
    'AFC': {
        'North': ['BAL', 'CIN', 'CLE', 'PIT'],
        'South': ['HOU', 'IND', 'JAX', 'TEN'],
        'East': ['BUF', 'MIA', 'NE', 'NYJ'],
        'West': ['DEN', 'KC', 'LV', 'LAC']
    },
    'NFC': {
        'North': ['CHI', 'DET', 'GB', 'MIN'],
        'South': ['ATL', 'CAR', 'NO', 'TB'],
        'East': ['DAL', 'NYG', 'PHI', 'WAS'],
        'West': ['ARI', 'LAR', 'SF', 'SEA']
    }
}

def get_team_division(team_abbr: str) -> tuple[str, str]:
    """Get conference and division for a team abbreviation.
    
    Args:
        team_abbr: Team abbreviation (e.g., 'SF', 'KC')
        
    Returns:
        Tuple of (conference, division)
        
    Raises:
        ValueError: If team abbreviation is not found
    """
    for conf, divisions in NFL_TEAMS.items():
        for div, teams in divisions.items():
            if team_abbr in teams:
                return conf, div
    
    raise ValueError(f"Team abbreviation '{team_abbr}' not found in NFL teams")