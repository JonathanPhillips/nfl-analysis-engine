"""Comprehensive tests for Player model."""

import pytest
from pydantic import ValidationError
from src.models.player import (
    PlayerModel, PlayerBase, PlayerCreate, PlayerUpdate, PlayerResponse,
    parse_height_string, format_height_display, calculate_years_experience
)
# Import models to ensure relationships are resolved
from src.models import TeamModel


class TestPlayerModel:
    """Test SQLAlchemy PlayerModel."""
    
    def test_player_model_table_name(self):
        """Test that table name is correctly set."""
        assert PlayerModel.__tablename__ == "players"
    
    def test_player_model_repr(self):
        """Test string representation of player model."""
        player = PlayerModel(
            player_id="00-0000001",
            full_name="Tom Brady",
            position="QB"
        )
        expected = "<Player 00-0000001: Tom Brady (QB)>"
        assert repr(player) == expected
    
    def test_player_model_required_fields(self):
        """Test that required fields are present."""
        required_fields = {'player_id', 'full_name'}
        model_columns = {col.name for col in PlayerModel.__table__.columns}
        assert required_fields.issubset(model_columns)
    
    def test_player_model_optional_fields(self):
        """Test that optional fields are present."""
        optional_fields = {
            'gsis_id', 'first_name', 'last_name', 'position', 'position_group',
            'height', 'weight', 'age', 'team_abbr', 'jersey_number',
            'rookie_year', 'years_exp', 'college', 'status'
        }
        model_columns = {col.name for col in PlayerModel.__table__.columns}
        assert optional_fields.issubset(model_columns)


class TestPlayerBase:
    """Test PlayerBase Pydantic model."""
    
    def test_valid_player_creation(self):
        """Test creating a valid player."""
        player_data = {
            "player_id": "00-0000001",
            "full_name": "Tom Brady",
            "position": "QB",
            "team_abbr": "TB"
        }
        
        player = PlayerBase(**player_data)
        assert player.player_id == "00-0000001"
        assert player.full_name == "Tom Brady"
        assert player.position == "QB"
        assert player.team_abbr == "TB"
    
    def test_minimal_valid_player(self):
        """Test creating player with minimal required fields."""
        player_data = {
            "player_id": "00-0000002",
            "full_name": "Aaron Rodgers"
        }
        
        player = PlayerBase(**player_data)
        assert player.player_id == "00-0000002"
        assert player.full_name == "Aaron Rodgers"
        assert player.position is None
        assert player.team_abbr is None
    
    def test_player_id_validation_empty(self):
        """Test player ID cannot be empty."""
        with pytest.raises(ValidationError) as exc_info:
            PlayerBase(
                player_id="",
                full_name="Test Player"
            )
        
        errors = exc_info.value.errors()
        # Check for string_too_short error (Pydantic v2 behavior)
        assert any(error['type'] == 'string_too_short' for error in errors)
    
    def test_player_id_validation_whitespace(self):
        """Test player ID strips whitespace."""
        player = PlayerBase(
            player_id="  00-0000001  ",
            full_name="Test Player"
        )
        assert player.player_id == "00-0000001"
    
    def test_team_abbr_validation_uppercase(self):
        """Test team abbreviation must be uppercase."""
        with pytest.raises(ValidationError) as exc_info:
            PlayerBase(
                player_id="00-0000001",
                full_name="Test Player",
                team_abbr="sf"  # lowercase should fail
            )
        
        errors = exc_info.value.errors()
        assert any("must be uppercase" in str(error['msg']) for error in errors)
    
    def test_team_abbr_validation_none(self):
        """Test team abbreviation can be None."""
        player = PlayerBase(
            player_id="00-0000001",
            full_name="Test Player",
            team_abbr=None
        )
        assert player.team_abbr is None
    
    def test_position_validation_uppercase(self):
        """Test position is converted to uppercase."""
        player = PlayerBase(
            player_id="00-0000001",
            full_name="Test Player",
            position="qb"
        )
        assert player.position == "QB"
    
    def test_position_validation_valid_positions(self):
        """Test various valid positions."""
        valid_positions = ['QB', 'RB', 'WR', 'TE', 'K', 'P', 'DE', 'LB', 'CB', 'S']
        
        for position in valid_positions:
            player = PlayerBase(
                player_id=f"00-000000{position}",
                full_name="Test Player",
                position=position
            )
            assert player.position == position
    
    def test_field_length_validations(self):
        """Test field length validations."""
        # Player ID too long
        with pytest.raises(ValidationError):
            PlayerBase(
                player_id="0" * 25,  # Too long
                full_name="Test Player"
            )
        
        # Full name too long
        with pytest.raises(ValidationError):
            PlayerBase(
                player_id="00-0000001",
                full_name="A" * 105  # Too long
            )


class TestPlayerCreate:
    """Test PlayerCreate Pydantic model."""
    
    def test_player_create_with_all_fields(self):
        """Test creating player with all optional fields."""
        player_data = {
            "player_id": "00-0000001",
            "full_name": "Tom Brady",
            "gsis_id": "00-0000001",
            "first_name": "Tom",
            "last_name": "Brady",
            "position": "QB",
            "position_group": "offense",
            "height": 76,  # 6'4"
            "weight": 225,
            "age": 45,
            "team_abbr": "TB",
            "jersey_number": 12,
            "rookie_year": 2000,
            "years_exp": 23,
            "college": "Michigan",
            "status": "retired"
        }
        
        player = PlayerCreate(**player_data)
        assert player.height == 76
        assert player.weight == 225
        assert player.jersey_number == 12
        assert player.rookie_year == 2000
        assert player.status == "retired"
    
    def test_height_validation(self):
        """Test height validation constraints."""
        base_data = {
            "player_id": "00-0000001",
            "full_name": "Test Player"
        }
        
        # Valid height
        player = PlayerCreate(**base_data, height=72)  # 6'0"
        assert player.height == 72
        
        # Too short
        with pytest.raises(ValidationError):
            PlayerCreate(**base_data, height=50)
        
        # Too tall
        with pytest.raises(ValidationError):
            PlayerCreate(**base_data, height=90)
    
    def test_weight_validation(self):
        """Test weight validation constraints."""
        base_data = {
            "player_id": "00-0000001",
            "full_name": "Test Player"
        }
        
        # Valid weight
        player = PlayerCreate(**base_data, weight=200)
        assert player.weight == 200
        
        # Too light
        with pytest.raises(ValidationError):
            PlayerCreate(**base_data, weight=100)
        
        # Too heavy
        with pytest.raises(ValidationError):
            PlayerCreate(**base_data, weight=500)
    
    def test_jersey_number_validation(self):
        """Test jersey number validation."""
        base_data = {
            "player_id": "00-0000001",
            "full_name": "Test Player"
        }
        
        # Valid jersey numbers
        for jersey in [0, 1, 50, 99]:
            player = PlayerCreate(**base_data, jersey_number=jersey)
            assert player.jersey_number == jersey
        
        # Invalid jersey numbers
        for jersey in [-1, 100]:
            with pytest.raises(ValidationError):
                PlayerCreate(**base_data, jersey_number=jersey)
    
    def test_age_validation(self):
        """Test age validation constraints."""
        base_data = {
            "player_id": "00-0000001",
            "full_name": "Test Player"
        }
        
        # Valid ages
        for age in [18, 25, 40, 50]:
            player = PlayerCreate(**base_data, age=age)
            assert player.age == age
        
        # Invalid ages
        for age in [17, 51]:
            with pytest.raises(ValidationError):
                PlayerCreate(**base_data, age=age)
    
    def test_status_validation(self):
        """Test status validation."""
        base_data = {
            "player_id": "00-0000001",
            "full_name": "Test Player"
        }
        
        # Valid statuses (should be converted to lowercase)
        valid_statuses = ['ACTIVE', 'active', 'Injured', 'RETIRED', 'suspended']
        expected_statuses = ['active', 'active', 'injured', 'retired', 'suspended']
        
        for status, expected in zip(valid_statuses, expected_statuses):
            player = PlayerCreate(**base_data, status=status)
            assert player.status == expected
        
        # Invalid status
        with pytest.raises(ValidationError):
            PlayerCreate(**base_data, status="invalid_status")
    
    def test_position_group_validation(self):
        """Test position group validation."""
        base_data = {
            "player_id": "00-0000001",
            "full_name": "Test Player"
        }
        
        # Valid position groups
        valid_groups = ['offense', 'DEFENSE', 'Special_Teams']
        expected_groups = ['offense', 'defense', 'special_teams']
        
        for group, expected in zip(valid_groups, expected_groups):
            player = PlayerCreate(**base_data, position_group=group)
            assert player.position_group == expected
        
        # Invalid position group
        with pytest.raises(ValidationError):
            PlayerCreate(**base_data, position_group="invalid_group")
    
    def test_rookie_year_validation(self):
        """Test rookie year validation."""
        base_data = {
            "player_id": "00-0000001",
            "full_name": "Test Player"
        }
        
        # Valid rookie years
        for year in [1920, 2000, 2024, 2030]:
            player = PlayerCreate(**base_data, rookie_year=year)
            assert player.rookie_year == year
        
        # Invalid rookie years
        for year in [1919, 2031]:
            with pytest.raises(ValidationError):
                PlayerCreate(**base_data, rookie_year=year)
    
    def test_years_exp_validation(self):
        """Test years of experience validation."""
        base_data = {
            "player_id": "00-0000001",
            "full_name": "Test Player"
        }
        
        # Valid years of experience
        for years in [0, 10, 20, 30]:
            player = PlayerCreate(**base_data, years_exp=years)
            assert player.years_exp == years
        
        # Invalid years of experience
        for years in [-1, 31]:
            with pytest.raises(ValidationError):
                PlayerCreate(**base_data, years_exp=years)


class TestPlayerUpdate:
    """Test PlayerUpdate Pydantic model."""
    
    def test_partial_update(self):
        """Test partial player update."""
        update_data = {
            "full_name": "Tom Brady Jr.",
            "team_abbr": "NE",
            "jersey_number": 11
        }
        
        update = PlayerUpdate(**update_data)
        assert update.full_name == "Tom Brady Jr."
        assert update.team_abbr == "NE"
        assert update.jersey_number == 11
        assert update.position is None  # Not provided, should be None
    
    def test_empty_update(self):
        """Test empty update (all fields None)."""
        update = PlayerUpdate()
        assert update.full_name is None
        assert update.position is None
        assert update.team_abbr is None
    
    def test_team_abbr_validation_in_update(self):
        """Test team abbreviation validation in updates."""
        # Valid uppercase
        update = PlayerUpdate(team_abbr="SF")
        assert update.team_abbr == "SF"
        
        # Invalid lowercase
        with pytest.raises(ValidationError):
            PlayerUpdate(team_abbr="sf")
    
    def test_status_validation_in_update(self):
        """Test status validation in updates."""
        # Valid status
        update = PlayerUpdate(status="INJURED")
        assert update.status == "injured"
        
        # Invalid status
        with pytest.raises(ValidationError):
            PlayerUpdate(status="invalid")


class TestPlayerResponse:
    """Test PlayerResponse Pydantic model."""
    
    def test_player_response_with_id(self):
        """Test player response includes ID."""
        response_data = {
            "id": 1,
            "player_id": "00-0000001",
            "full_name": "Tom Brady",
            "position": "QB",
            "team_abbr": "TB",
            "height": 76,
            "weight": 225
        }
        
        response = PlayerResponse(**response_data)
        assert response.id == 1
        assert response.player_id == "00-0000001"
        assert response.height == 76
        assert response.weight == 225


class TestPlayerUtilityFunctions:
    """Test utility functions for player data."""
    
    def test_parse_height_string_valid_formats(self):
        """Test parsing various height string formats."""
        test_cases = [
            ("6-2", 74),      # 6 feet 2 inches
            ("6'2\"", 74),    # With quotes
            ("6'2", 74),      # With apostrophe
            ("72", 72),       # Just inches
            ("5-11", 71),     # 5 feet 11 inches
            ("6-0", 72),      # 6 feet even
        ]
        
        for height_str, expected in test_cases:
            result = parse_height_string(height_str)
            assert result == expected, f"Failed for {height_str}"
    
    def test_parse_height_string_invalid_formats(self):
        """Test parsing invalid height strings."""
        invalid_cases = ["", "abc", "6-", "-2", "6-15"]
        
        for invalid_str in invalid_cases:
            result = parse_height_string(invalid_str)
            assert result is None, f"Should return None for {invalid_str}"
        
        # Test None separately
        result = parse_height_string(None)
        assert result is None
    
    def test_format_height_display(self):
        """Test formatting height for display."""
        test_cases = [
            (74, "6-2"),      # 6 feet 2 inches
            (72, "6-0"),      # 6 feet even
            (71, "5-11"),     # 5 feet 11 inches
            (84, "7-0"),      # 7 feet even
            (None, None)      # None input
        ]
        
        for height_inches, expected in test_cases:
            result = format_height_display(height_inches)
            assert result == expected
    
    def test_calculate_years_experience(self):
        """Test calculating years of experience."""
        # Test with default current year (2024)
        test_cases = [
            (2020, 4),     # 4 years experience
            (2024, 0),     # Rookie
            (2000, 24),    # Veteran
            (2025, 0),     # Future rookie (min 0)
            (None, None)   # No rookie year
        ]
        
        for rookie_year, expected in test_cases:
            result = calculate_years_experience(rookie_year)
            assert result == expected
    
    def test_calculate_years_experience_custom_year(self):
        """Test calculating years of experience with custom current year."""
        result = calculate_years_experience(2020, current_year=2023)
        assert result == 3
        
        result = calculate_years_experience(2023, current_year=2023)
        assert result == 0


class TestPlayerModelIntegration:
    """Integration tests combining SQLAlchemy and Pydantic models."""
    
    def test_player_create_to_sqlalchemy_model(self):
        """Test converting PlayerCreate to SQLAlchemy model."""
        player_create = PlayerCreate(
            player_id="00-0000001",
            full_name="Tom Brady",
            position="QB",
            team_abbr="TB",
            height=76,
            weight=225,
            jersey_number=12
        )
        
        # Convert to SQLAlchemy model data (exclude relationship fields)
        player_data = player_create.model_dump(exclude={'team'})
        
        # Create model without triggering database relationships
        player_model = PlayerModel()
        for key, value in player_data.items():
            setattr(player_model, key, value)
        
        assert player_model.player_id == "00-0000001"
        assert player_model.full_name == "Tom Brady"
        assert player_model.position == "QB"
        assert player_model.height == 76
    
    def test_sqlalchemy_to_pydantic_response(self):
        """Test converting SQLAlchemy model to Pydantic response."""
        # Create SQLAlchemy model instance without triggering relationships
        player_model = PlayerModel()
        player_model.id = 1
        player_model.player_id = "00-0000001"
        player_model.full_name = "Tom Brady"
        player_model.position = "QB"
        player_model.team_abbr = "TB"
        
        # Convert to Pydantic response
        # Note: In real usage, this would use from_attributes=True
        response_data = {
            "id": player_model.id,
            "player_id": player_model.player_id,
            "full_name": player_model.full_name,
            "position": player_model.position,
            "team_abbr": player_model.team_abbr
        }
        
        response = PlayerResponse(**response_data)
        assert response.id == 1
        assert response.player_id == "00-0000001"
        assert response.full_name == "Tom Brady"