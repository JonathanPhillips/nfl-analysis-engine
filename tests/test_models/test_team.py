"""Comprehensive tests for Team model."""

import pytest
from pydantic import ValidationError
from src.models.team import (
    TeamModel, TeamBase, TeamCreate, TeamUpdate, TeamResponse,
    NFL_TEAMS, get_team_division
)


class TestTeamModel:
    """Test SQLAlchemy TeamModel."""
    
    def test_team_model_table_name(self):
        """Test that table name is correctly set."""
        assert TeamModel.__tablename__ == "teams"
    
    def test_team_model_repr(self):
        """Test string representation of team model."""
        team = TeamModel(
            team_abbr="SF",
            team_name="San Francisco",
            team_nick="49ers",
            team_conf="NFC",
            team_division="West"
        )
        expected = "<Team SF: San Francisco 49ers>"
        assert repr(team) == expected
    
    def test_team_model_required_fields(self):
        """Test that required fields are present."""
        required_fields = {
            'team_abbr', 'team_name', 'team_nick', 
            'team_conf', 'team_division'
        }
        
        model_columns = {col.name for col in TeamModel.__table__.columns}
        assert required_fields.issubset(model_columns)
    
    def test_team_model_optional_fields(self):
        """Test that optional fields are present."""
        optional_fields = {
            'team_color', 'team_color2', 'team_color3', 'team_color4',
            'team_logo_espn', 'team_logo_wikipedia', 'team_city', 'team_wordmark'
        }
        
        model_columns = {col.name for col in TeamModel.__table__.columns}
        assert optional_fields.issubset(model_columns)


class TestTeamBase:
    """Test TeamBase Pydantic model."""
    
    def test_valid_team_creation(self):
        """Test creating a valid team."""
        team_data = {
            "team_abbr": "SF",
            "team_name": "San Francisco",
            "team_nick": "49ers",
            "team_conf": "NFC",
            "team_division": "West"
        }
        
        team = TeamBase(**team_data)
        assert team.team_abbr == "SF"
        assert team.team_name == "San Francisco"
        assert team.team_nick == "49ers"
        assert team.team_conf == "NFC"
        assert team.team_division == "West"
    
    def test_team_abbr_validation_uppercase(self):
        """Test team abbreviation must be uppercase."""
        with pytest.raises(ValidationError) as exc_info:
            TeamBase(
                team_abbr="sf",  # lowercase should fail
                team_name="San Francisco",
                team_nick="49ers",
                team_conf="NFC",
                team_division="West"
            )
        
        errors = exc_info.value.errors()
        assert any("must be uppercase" in str(error['msg']) for error in errors)
    
    def test_team_abbr_length_validation(self):
        """Test team abbreviation length validation."""
        # Too short
        with pytest.raises(ValidationError):
            TeamBase(
                team_abbr="S",
                team_name="San Francisco",
                team_nick="49ers",
                team_conf="NFC",
                team_division="West"
            )
        
        # Too long
        with pytest.raises(ValidationError):
            TeamBase(
                team_abbr="SFGH",
                team_name="San Francisco",
                team_nick="49ers",
                team_conf="NFC",
                team_division="West"
            )
    
    def test_conference_validation(self):
        """Test conference validation."""
        # Invalid conference
        with pytest.raises(ValidationError) as exc_info:
            TeamBase(
                team_abbr="SF",
                team_name="San Francisco",
                team_nick="49ers",
                team_conf="XFC",  # Invalid conference
                team_division="West"
            )
        
        errors = exc_info.value.errors()
        # In Pydantic v2, pattern validation gives different error message
        assert any("string should match pattern" in str(error['msg']).lower() for error in errors)
    
    def test_division_validation(self):
        """Test division validation."""
        # Invalid division
        with pytest.raises(ValidationError) as exc_info:
            TeamBase(
                team_abbr="SF",
                team_name="San Francisco",
                team_nick="49ers",
                team_conf="NFC",
                team_division="Central"  # Invalid division
            )
        
        errors = exc_info.value.errors()
        # In Pydantic v2, pattern validation gives different error message
        assert any("pattern" in str(error['msg']).lower() and ("north|south|east|west" in str(error['msg']).lower()) for error in errors)
    
    def test_empty_required_fields(self):
        """Test that required fields cannot be empty."""
        with pytest.raises(ValidationError):
            TeamBase(
                team_abbr="",
                team_name="San Francisco",
                team_nick="49ers",
                team_conf="NFC",
                team_division="West"
            )


class TestTeamCreate:
    """Test TeamCreate Pydantic model."""
    
    def test_team_create_with_colors(self):
        """Test creating team with color fields."""
        team_data = {
            "team_abbr": "SF",
            "team_name": "San Francisco",
            "team_nick": "49ers",
            "team_conf": "NFC",
            "team_division": "West",
            "team_color": "#AA0000",
            "team_color2": "#B3995D",
            "team_city": "San Francisco"
        }
        
        team = TeamCreate(**team_data)
        assert team.team_color == "#AA0000"
        assert team.team_color2 == "#B3995D"
        assert team.team_city == "San Francisco"
    
    def test_invalid_hex_color(self):
        """Test invalid hex color validation."""
        with pytest.raises(ValidationError):
            TeamCreate(
                team_abbr="SF",
                team_name="San Francisco",
                team_nick="49ers",
                team_conf="NFC",
                team_division="West",
                team_color="red"  # Invalid hex format
            )
    
    def test_hex_color_case_insensitive(self):
        """Test hex colors accept both upper and lowercase."""
        team_data = {
            "team_abbr": "SF",
            "team_name": "San Francisco",
            "team_nick": "49ers",
            "team_conf": "NFC",
            "team_division": "West",
            "team_color": "#aa0000",  # lowercase
            "team_color2": "#B3995D"  # uppercase
        }
        
        team = TeamCreate(**team_data)
        assert team.team_color == "#aa0000"
        assert team.team_color2 == "#B3995D"


class TestTeamUpdate:
    """Test TeamUpdate Pydantic model."""
    
    def test_partial_update(self):
        """Test partial team update."""
        update_data = {
            "team_name": "Las Vegas",
            "team_city": "Las Vegas"
        }
        
        update = TeamUpdate(**update_data)
        assert update.team_name == "Las Vegas"
        assert update.team_city == "Las Vegas"
        assert update.team_conf is None  # Not provided, should be None
    
    def test_empty_update(self):
        """Test empty update (all fields None)."""
        update = TeamUpdate()
        assert update.team_name is None
        assert update.team_conf is None


class TestTeamResponse:
    """Test TeamResponse Pydantic model."""
    
    def test_team_response_with_id(self):
        """Test team response includes ID."""
        response_data = {
            "id": 1,
            "team_abbr": "SF",
            "team_name": "San Francisco",
            "team_nick": "49ers",
            "team_conf": "NFC",
            "team_division": "West",
            "team_color": "#AA0000"
        }
        
        response = TeamResponse(**response_data)
        assert response.id == 1
        assert response.team_abbr == "SF"
        assert response.team_color == "#AA0000"


class TestNFLTeamsConstant:
    """Test NFL_TEAMS constant and related functions."""
    
    def test_nfl_teams_structure(self):
        """Test NFL_TEAMS constant has correct structure."""
        assert "AFC" in NFL_TEAMS
        assert "NFC" in NFL_TEAMS
        
        for conference in ["AFC", "NFC"]:
            assert "North" in NFL_TEAMS[conference]
            assert "South" in NFL_TEAMS[conference]
            assert "East" in NFL_TEAMS[conference]
            assert "West" in NFL_TEAMS[conference]
    
    def test_nfl_teams_count(self):
        """Test NFL_TEAMS has correct number of teams."""
        total_teams = 0
        for conf_teams in NFL_TEAMS.values():
            for div_teams in conf_teams.values():
                total_teams += len(div_teams)
        
        assert total_teams == 32  # 32 NFL teams
    
    def test_each_division_has_four_teams(self):
        """Test each division has exactly 4 teams."""
        for conf_teams in NFL_TEAMS.values():
            for div_teams in conf_teams.values():
                assert len(div_teams) == 4
    
    def test_get_team_division_valid_teams(self):
        """Test get_team_division with valid team abbreviations."""
        test_cases = [
            ("SF", ("NFC", "West")),
            ("KC", ("AFC", "West")),
            ("NE", ("AFC", "East")),
            ("GB", ("NFC", "North")),
            ("BAL", ("AFC", "North")),
            ("NO", ("NFC", "South"))
        ]
        
        for team_abbr, expected in test_cases:
            result = get_team_division(team_abbr)
            assert result == expected
    
    def test_get_team_division_invalid_team(self):
        """Test get_team_division with invalid team abbreviation."""
        with pytest.raises(ValueError) as exc_info:
            get_team_division("XX")
        
        assert "Team abbreviation 'XX' not found" in str(exc_info.value)
    
    def test_all_nfl_teams_findable(self):
        """Test that all teams in NFL_TEAMS can be found by get_team_division."""
        for conf, divisions in NFL_TEAMS.items():
            for div, teams in divisions.items():
                for team in teams:
                    result_conf, result_div = get_team_division(team)
                    assert result_conf == conf
                    assert result_div == div


class TestTeamModelIntegration:
    """Integration tests combining SQLAlchemy and Pydantic models."""
    
    def test_team_create_to_sqlalchemy_model(self):
        """Test converting TeamCreate to SQLAlchemy model."""
        team_create = TeamCreate(
            team_abbr="SF",
            team_name="San Francisco",
            team_nick="49ers",
            team_conf="NFC",
            team_division="West",
            team_color="#AA0000",
            team_city="San Francisco"
        )
        
        # Convert to SQLAlchemy model data
        team_data = team_create.model_dump()
        team_model = TeamModel(**team_data)
        
        assert team_model.team_abbr == "SF"
        assert team_model.team_color == "#AA0000"
        assert team_model.team_city == "San Francisco"