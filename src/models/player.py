"""Player data models compatible with nfl_data_py structure."""

from typing import Optional
from sqlalchemy import Column, String, Integer, ForeignKey
from sqlalchemy.orm import relationship
from pydantic import BaseModel as PydanticBaseModel, Field, field_validator, ConfigDict
from src.models.base import BaseModel as SQLBaseModel, BasePydanticModel


class PlayerModel(SQLBaseModel):
    """SQLAlchemy model for NFL players.
    
    Compatible with nfl_data_py player data structure.
    Reference: https://github.com/nflverse/nfl_data_py
    """
    __tablename__ = "players"
    
    # Primary identifiers
    player_id = Column(String(20), unique=True, nullable=False, index=True)
    gsis_id = Column(String(20), index=True)  # GSIS ID for cross-reference
    full_name = Column(String(100), nullable=False, index=True)
    first_name = Column(String(50))
    last_name = Column(String(50))
    
    # Position and physical attributes
    position = Column(String(10), index=True)  # 'QB', 'RB', 'WR', etc.
    position_group = Column(String(20))  # 'offense', 'defense', 'special_teams'
    height = Column(Integer)  # Height in inches
    weight = Column(Integer)  # Weight in pounds
    age = Column(Integer)
    
    # Team association
    team_abbr = Column(String(3), ForeignKey('teams.team_abbr'), index=True)
    jersey_number = Column(Integer)
    
    # Career information
    rookie_year = Column(Integer)
    years_exp = Column(Integer)
    college = Column(String(100))
    
    # Status
    status = Column(String(20), default='active')  # 'active', 'injured', 'retired'
    
    # Relationships - using string to avoid circular import
    team = relationship("TeamModel", back_populates="players")
    
    def __repr__(self):
        return f"<Player {self.player_id}: {self.full_name} ({self.position})>"


class PlayerBase(BasePydanticModel):
    """Base Pydantic model for player data."""
    player_id: str = Field(..., min_length=1, max_length=20, description="nflfastR player ID")
    full_name: str = Field(..., min_length=1, max_length=100, description="Player full name")
    position: Optional[str] = Field(None, max_length=10, description="Player position")
    team_abbr: Optional[str] = Field(None, min_length=2, max_length=3, description="Team abbreviation")
    
    @field_validator('player_id')
    @classmethod
    def validate_player_id(cls, v):
        """Validate player ID format."""
        if not v.strip():
            raise ValueError('Player ID cannot be empty or whitespace')
        return v.strip()
    
    @field_validator('team_abbr')
    @classmethod
    def validate_team_abbr(cls, v):
        """Validate team abbreviation format."""
        if v is not None:
            v = v.strip()
            if not v.isupper():
                raise ValueError('Team abbreviation must be uppercase')
        return v
    
    @field_validator('position')
    @classmethod
    def validate_position(cls, v):
        """Validate position format."""
        if v is not None:
            v = v.strip().upper()
            # Common NFL positions
            valid_positions = {
                'QB', 'RB', 'FB', 'WR', 'TE', 'OL', 'C', 'G', 'T', 'OT', 'OG',
                'DL', 'DE', 'DT', 'NT', 'LB', 'ILB', 'OLB', 'MLB', 'DB', 'CB', 
                'S', 'SS', 'FS', 'K', 'P', 'LS', 'LS/TE', 'WR/PR', 'RB/KR'
            }
            if v and v not in valid_positions:
                # Allow it but log a warning - positions can vary
                pass
        return v


class PlayerCreate(PlayerBase):
    """Pydantic model for creating players."""
    gsis_id: Optional[str] = Field(None, max_length=20, description="GSIS player ID")
    first_name: Optional[str] = Field(None, max_length=50, description="First name")
    last_name: Optional[str] = Field(None, max_length=50, description="Last name")
    position_group: Optional[str] = Field(None, max_length=20, description="Position group")
    height: Optional[int] = Field(None, ge=60, le=84, description="Height in inches (5'0\" to 7'0\")")
    weight: Optional[int] = Field(None, ge=150, le=400, description="Weight in pounds")
    age: Optional[int] = Field(None, ge=18, le=50, description="Player age")
    jersey_number: Optional[int] = Field(None, ge=0, le=99, description="Jersey number")
    rookie_year: Optional[int] = Field(None, ge=1920, le=2030, description="Rookie year")
    years_exp: Optional[int] = Field(None, ge=0, le=30, description="Years of experience")
    college: Optional[str] = Field(None, max_length=100, description="College")
    status: Optional[str] = Field('active', max_length=20, description="Player status")
    
    @field_validator('status')
    @classmethod
    def validate_status(cls, v):
        """Validate player status."""
        if v is not None:
            valid_statuses = {'active', 'injured', 'retired', 'suspended', 'practice_squad'}
            if v.lower() not in valid_statuses:
                raise ValueError(f'Status must be one of: {", ".join(valid_statuses)}')
            return v.lower()
        return 'active'
    
    @field_validator('position_group')
    @classmethod
    def validate_position_group(cls, v):
        """Validate position group."""
        if v is not None:
            valid_groups = {'offense', 'defense', 'special_teams'}
            if v.lower() not in valid_groups:
                raise ValueError(f'Position group must be one of: {", ".join(valid_groups)}')
            return v.lower()
        return v


class PlayerUpdate(PydanticBaseModel):
    """Pydantic model for updating players."""
    full_name: Optional[str] = Field(None, min_length=1, max_length=100)
    first_name: Optional[str] = Field(None, max_length=50)
    last_name: Optional[str] = Field(None, max_length=50)
    position: Optional[str] = Field(None, max_length=10)
    position_group: Optional[str] = Field(None, max_length=20)
    team_abbr: Optional[str] = Field(None, min_length=2, max_length=3)
    height: Optional[int] = Field(None, ge=60, le=84)
    weight: Optional[int] = Field(None, ge=150, le=400)
    age: Optional[int] = Field(None, ge=18, le=50)
    jersey_number: Optional[int] = Field(None, ge=0, le=99)
    rookie_year: Optional[int] = Field(None, ge=1920, le=2030)
    years_exp: Optional[int] = Field(None, ge=0, le=30)
    college: Optional[str] = Field(None, max_length=100)
    status: Optional[str] = Field(None, max_length=20)
    
    @field_validator('team_abbr')
    @classmethod
    def validate_team_abbr(cls, v):
        """Validate team abbreviation format."""
        if v is not None and not v.isupper():
            raise ValueError('Team abbreviation must be uppercase')
        return v
    
    @field_validator('status')
    @classmethod
    def validate_status(cls, v):
        """Validate player status."""
        if v is not None:
            valid_statuses = {'active', 'injured', 'retired', 'suspended', 'practice_squad'}
            if v.lower() not in valid_statuses:
                raise ValueError(f'Status must be one of: {", ".join(valid_statuses)}')
            return v.lower()
        return v


class PlayerResponse(PlayerBase):
    """Pydantic model for player responses."""
    id: int
    gsis_id: Optional[str] = None
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    position_group: Optional[str] = None
    height: Optional[int] = None
    weight: Optional[int] = None
    age: Optional[int] = None
    jersey_number: Optional[int] = None
    rookie_year: Optional[int] = None
    years_exp: Optional[int] = None
    college: Optional[str] = None
    status: Optional[str] = None
    
    model_config = ConfigDict(from_attributes=True)


# Utility functions for player data
def parse_height_string(height_str: str) -> Optional[int]:
    """Parse height string like '6-2' or '6\'2\"' to inches.
    
    Args:
        height_str: Height string in various formats
        
    Returns:
        Height in inches or None if invalid
    """
    if not height_str:
        return None
    
    height_str = height_str.strip().replace('"', '').replace("'", '-')
    
    try:
        if '-' in height_str:
            parts = height_str.split('-')
            if len(parts) != 2:
                return None
            feet, inches = parts
            feet_int = int(feet)
            inches_int = int(inches)
            
            # Validate reasonable ranges
            if feet_int < 0 or feet_int > 8 or inches_int < 0 or inches_int >= 12:
                return None
                
            return feet_int * 12 + inches_int
        elif len(height_str) == 2 and height_str.isdigit():
            # Assume it's just inches if 2 digits
            return int(height_str)
        else:
            # Try direct conversion for total inches
            inches = int(height_str)
            # Validate reasonable range (5'0" to 7'0")
            if inches < 60 or inches > 84:
                return None
            return inches
    except (ValueError, AttributeError):
        return None


def format_height_display(height_inches: Optional[int]) -> Optional[str]:
    """Format height in inches to display string like '6-2'.
    
    Args:
        height_inches: Height in inches
        
    Returns:
        Formatted height string or None
    """
    if height_inches is None:
        return None
    
    feet = height_inches // 12
    inches = height_inches % 12
    return f"{feet}-{inches}"


def calculate_years_experience(rookie_year: Optional[int], current_year: int = 2024) -> Optional[int]:
    """Calculate years of experience based on rookie year.
    
    Args:
        rookie_year: Year player entered the league
        current_year: Current year for calculation
        
    Returns:
        Years of experience or None
    """
    if rookie_year is None:
        return None
    
    return max(0, current_year - rookie_year)