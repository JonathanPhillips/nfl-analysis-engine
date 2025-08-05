"""Comprehensive tests for Game model."""

import pytest
from datetime import date, time
from pydantic import ValidationError
from src.models.game import (
    GameModel, GameBase, GameCreate, GameUpdate, GameResponse,
    calculate_result, calculate_total_score, get_season_week_range,
    format_game_description, is_game_overtime
)
# Import models to ensure relationships are resolved
from src.models import TeamModel


class TestGameModel:
    """Test SQLAlchemy GameModel."""
    
    def test_game_model_table_name(self):
        """Test that table name is correctly set."""
        assert GameModel.__tablename__ == "games"
    
    def test_game_model_repr(self):
        """Test string representation of game model."""
        game = GameModel(
            game_id="2024_01_SF_DAL",
            away_team="SF",
            home_team="DAL",
            game_date=date(2024, 1, 15)
        )
        expected = "<Game 2024_01_SF_DAL: SF @ DAL (2024-01-15)>"
        assert repr(game) == expected
    
    def test_game_model_required_fields(self):
        """Test that required fields are present."""
        required_fields = {
            'game_id', 'season', 'season_type', 'game_date', 
            'home_team', 'away_team'
        }
        model_columns = {col.name for col in GameModel.__table__.columns}
        assert required_fields.issubset(model_columns)
    
    def test_game_model_optional_fields(self):
        """Test that optional fields are present."""
        optional_fields = {
            'old_game_id', 'week', 'kickoff_time', 'home_score', 'away_score',
            'result', 'total_score', 'roof', 'surface', 'temp', 'wind',
            'home_spread', 'total_line', 'home_moneyline', 'away_moneyline',
            'game_finished'
        }
        model_columns = {col.name for col in GameModel.__table__.columns}
        assert optional_fields.issubset(model_columns)


class TestGameBase:
    """Test GameBase Pydantic model."""
    
    def test_valid_game_creation(self):
        """Test creating a valid game."""
        game_data = {
            "game_id": "2024_01_SF_DAL",
            "season": 2024,
            "season_type": "REG",
            "game_date": date(2024, 1, 15),
            "home_team": "DAL",
            "away_team": "SF"
        }
        
        game = GameBase(**game_data)
        assert game.game_id == "2024_01_SF_DAL"
        assert game.season == 2024
        assert game.season_type == "REG"
        assert game.home_team == "DAL"
        assert game.away_team == "SF"
    
    def test_game_id_validation_empty(self):
        """Test game ID cannot be empty."""
        with pytest.raises(ValidationError) as exc_info:
            GameBase(
                game_id="",
                season=2024,
                season_type="REG",
                game_date=date(2024, 1, 15),
                home_team="DAL",
                away_team="SF"
            )
        
        errors = exc_info.value.errors()
        assert any(error['type'] == 'string_too_short' for error in errors)
    
    def test_game_id_validation_whitespace(self):
        """Test game ID strips whitespace."""
        game = GameBase(
            game_id="  2024_01_SF_DAL  ",
            season=2024,
            season_type="REG",
            game_date=date(2024, 1, 15),
            home_team="DAL",
            away_team="SF"
        )
        assert game.game_id == "2024_01_SF_DAL"
    
    def test_season_validation(self):
        """Test season validation constraints."""
        base_data = {
            "game_id": "2024_01_SF_DAL",
            "season_type": "REG",
            "game_date": date(2024, 1, 15),
            "home_team": "DAL",
            "away_team": "SF"
        }
        
        # Valid seasons
        for season in [1920, 2000, 2024, 2030]:
            game = GameBase(**base_data, season=season)
            assert game.season == season
        
        # Invalid seasons
        for season in [1919, 2031]:
            with pytest.raises(ValidationError):
                GameBase(**base_data, season=season)
    
    def test_season_type_validation(self):
        """Test season type validation."""
        base_data = {
            "game_id": "2024_01_SF_DAL",
            "season": 2024,
            "game_date": date(2024, 1, 15),
            "home_team": "DAL",
            "away_team": "SF"
        }
        
        # Valid season types (should be converted to uppercase)
        valid_types = ['REG', 'reg', 'POST', 'post', 'PRE', 'pre']
        expected_types = ['REG', 'REG', 'POST', 'POST', 'PRE', 'PRE']
        
        for season_type, expected in zip(valid_types, expected_types):
            game = GameBase(**base_data, season_type=season_type)
            assert game.season_type == expected
        
        # Invalid season type
        with pytest.raises(ValidationError):
            GameBase(**base_data, season_type="INVALID")
    
    def test_team_abbr_validation_uppercase(self):
        """Test team abbreviations must be uppercase."""
        base_data = {
            "game_id": "2024_01_SF_DAL",
            "season": 2024,
            "season_type": "REG",
            "game_date": date(2024, 1, 15)
        }
        
        # Invalid lowercase home team
        with pytest.raises(ValidationError):
            GameBase(**base_data, home_team="dal", away_team="SF")
        
        # Invalid lowercase away team
        with pytest.raises(ValidationError):
            GameBase(**base_data, home_team="DAL", away_team="sf")


class TestGameCreate:
    """Test GameCreate Pydantic model."""
    
    def test_game_create_with_all_fields(self):
        """Test creating game with all optional fields."""
        game_data = {
            "game_id": "2024_01_SF_DAL",
            "season": 2024,
            "season_type": "REG",
            "game_date": date(2024, 1, 15),
            "home_team": "DAL",
            "away_team": "SF",
            "old_game_id": "2024011500",
            "week": 1,
            "kickoff_time": time(13, 0),  # 1:00 PM
            "home_score": 24,
            "away_score": 21,
            "result": 1,  # Home team won
            "total_score": 45,
            "roof": "dome",
            "surface": "fieldturf",
            "temp": 72,
            "wind": 5,
            "home_spread": -3.0,
            "total_line": 47.5,
            "home_moneyline": -150,
            "away_moneyline": 130,
            "game_finished": True
        }
        
        game = GameCreate(**game_data)
        assert game.week == 1
        assert game.home_score == 24
        assert game.away_score == 21
        assert game.roof == "dome"
        assert game.surface == "fieldturf"
        assert game.game_finished is True
    
    def test_score_validation(self):
        """Test score validation constraints."""
        base_data = {
            "game_id": "2024_01_SF_DAL",
            "season": 2024,
            "season_type": "REG",
            "game_date": date(2024, 1, 15),
            "home_team": "DAL",
            "away_team": "SF"
        }
        
        # Valid scores
        game = GameCreate(**base_data, home_score=35, away_score=28)
        assert game.home_score == 35
        assert game.away_score == 28
        
        # Invalid negative score
        with pytest.raises(ValidationError):
            GameCreate(**base_data, home_score=-1)
        
        # Invalid too high score
        with pytest.raises(ValidationError):
            GameCreate(**base_data, home_score=101)
    
    def test_week_validation(self):
        """Test week validation constraints."""
        base_data = {
            "game_id": "2024_01_SF_DAL",
            "season": 2024,
            "game_date": date(2024, 1, 15),
            "home_team": "DAL",
            "away_team": "SF"
        }
        
        # Valid weeks (simplified validation)
        for week in [1, 9, 18, 19, 22]:
            game = GameCreate(**base_data, season_type="REG", week=week)
            assert game.week == week
        
        # Invalid weeks (out of range)
        for week in [0, 23]:
            with pytest.raises(ValidationError):
                GameCreate(**base_data, season_type="REG", week=week)
    
    def test_temperature_validation(self):
        """Test temperature validation."""
        base_data = {
            "game_id": "2024_01_SF_DAL",
            "season": 2024,
            "season_type": "REG",
            "game_date": date(2024, 1, 15),
            "home_team": "DAL",
            "away_team": "SF"
        }
        
        # Valid temperatures
        for temp in [-10, 32, 72, 100]:
            game = GameCreate(**base_data, temp=temp)
            assert game.temp == temp
        
        # Invalid temperatures
        for temp in [-25, 125]:
            with pytest.raises(ValidationError):
                GameCreate(**base_data, temp=temp)
    
    def test_wind_validation(self):
        """Test wind speed validation."""
        base_data = {
            "game_id": "2024_01_SF_DAL",
            "season": 2024,
            "season_type": "REG",
            "game_date": date(2024, 1, 15),
            "home_team": "DAL",
            "away_team": "SF"
        }
        
        # Valid wind speeds
        for wind in [0, 10, 25, 50]:
            game = GameCreate(**base_data, wind=wind)
            assert game.wind == wind
        
        # Invalid wind speeds
        for wind in [-1, 51]:
            with pytest.raises(ValidationError):
                GameCreate(**base_data, wind=wind)
    
    def test_roof_validation(self):
        """Test roof type validation."""
        base_data = {
            "game_id": "2024_01_SF_DAL",
            "season": 2024,
            "season_type": "REG",
            "game_date": date(2024, 1, 15),
            "home_team": "DAL",
            "away_team": "SF"
        }
        
        # Valid roof types (should be converted to lowercase)
        valid_roofs = ['DOME', 'dome', 'Outdoors', 'CLOSED', 'open']
        expected_roofs = ['dome', 'dome', 'outdoors', 'closed', 'open']
        
        for roof, expected in zip(valid_roofs, expected_roofs):
            game = GameCreate(**base_data, roof=roof)
            assert game.roof == expected
        
        # Invalid roof type
        with pytest.raises(ValidationError):
            GameCreate(**base_data, roof="invalid_roof")
    
    def test_surface_validation(self):
        """Test surface validation."""
        base_data = {
            "game_id": "2024_01_SF_DAL",
            "season": 2024,
            "season_type": "REG",
            "game_date": date(2024, 1, 15),
            "home_team": "DAL",
            "away_team": "SF"
        }
        
        # Valid surfaces
        valid_surfaces = ['GRASS', 'FieldTurf', 'Artificial']
        expected_surfaces = ['grass', 'fieldturf', 'artificial']
        
        for surface, expected in zip(valid_surfaces, expected_surfaces):
            game = GameCreate(**base_data, surface=surface)
            assert game.surface == expected
    
    def test_spread_validation(self):
        """Test point spread validation."""
        base_data = {
            "game_id": "2024_01_SF_DAL",
            "season": 2024,
            "season_type": "REG",
            "game_date": date(2024, 1, 15),
            "home_team": "DAL",
            "away_team": "SF"
        }
        
        # Valid spreads
        for spread in [-14.5, -3.0, 0.0, 7.5, 21.0]:
            game = GameCreate(**base_data, home_spread=spread)
            assert game.home_spread == spread
        
        # Invalid spreads
        for spread in [-35.0, 35.0]:
            with pytest.raises(ValidationError):
                GameCreate(**base_data, home_spread=spread)
    
    def test_total_line_validation(self):
        """Test over/under total validation."""
        base_data = {
            "game_id": "2024_01_SF_DAL",
            "season": 2024,
            "season_type": "REG",
            "game_date": date(2024, 1, 15),
            "home_team": "DAL",
            "away_team": "SF"
        }
        
        # Valid totals
        for total in [35.5, 47.0, 55.5]:
            game = GameCreate(**base_data, total_line=total)
            assert game.total_line == total
        
        # Invalid totals
        for total in [15.0, 85.0]:
            with pytest.raises(ValidationError):
                GameCreate(**base_data, total_line=total)


class TestGameUpdate:
    """Test GameUpdate Pydantic model."""
    
    def test_partial_update(self):
        """Test partial game update."""
        update_data = {
            "home_score": 28,
            "away_score": 21,
            "game_finished": True
        }
        
        update = GameUpdate(**update_data)
        assert update.home_score == 28
        assert update.away_score == 21
        assert update.game_finished is True
        assert update.week is None  # Not provided, should be None
    
    def test_empty_update(self):
        """Test empty update (all fields None)."""
        update = GameUpdate()
        assert update.home_score is None
        assert update.away_score is None
        assert update.game_finished is None
    
    def test_roof_validation_in_update(self):
        """Test roof validation in updates."""
        # Valid roof
        update = GameUpdate(roof="DOME")
        assert update.roof == "dome"
        
        # Invalid roof
        with pytest.raises(ValidationError):
            GameUpdate(roof="invalid")


class TestGameResponse:
    """Test GameResponse Pydantic model."""
    
    def test_game_response_with_id(self):
        """Test game response includes ID."""
        response_data = {
            "id": 1,
            "game_id": "2024_01_SF_DAL",
            "season": 2024,
            "season_type": "REG",
            "game_date": date(2024, 1, 15),
            "home_team": "DAL",
            "away_team": "SF",
            "home_score": 28,
            "away_score": 21
        }
        
        response = GameResponse(**response_data)
        assert response.id == 1
        assert response.game_id == "2024_01_SF_DAL"
        assert response.home_score == 28
        assert response.away_score == 21


class TestGameUtilityFunctions:
    """Test utility functions for game data."""
    
    def test_calculate_result(self):
        """Test calculating game result from scores."""
        # Home team wins
        assert calculate_result(28, 21) == 1
        assert calculate_result(14, 7) == 1
        
        # Away team wins
        assert calculate_result(21, 28) == 0
        assert calculate_result(10, 17) == 0
        
        # Tie (should return 0 for away team win in this implementation)
        assert calculate_result(21, 21) == 0
        
        # Missing scores
        assert calculate_result(None, 21) is None
        assert calculate_result(28, None) is None
        assert calculate_result(None, None) is None
    
    def test_calculate_total_score(self):
        """Test calculating total combined score."""
        assert calculate_total_score(28, 21) == 49
        assert calculate_total_score(0, 0) == 0
        assert calculate_total_score(35, 42) == 77
        
        # Missing scores
        assert calculate_total_score(None, 21) is None
        assert calculate_total_score(28, None) is None
        assert calculate_total_score(None, None) is None
    
    def test_get_season_week_range(self):
        """Test getting valid week ranges for season types."""
        assert get_season_week_range('REG') == (1, 18)
        assert get_season_week_range('POST') == (19, 22)
        assert get_season_week_range('PRE') == (1, 4)
        
        # Invalid season type
        with pytest.raises(ValueError):
            get_season_week_range('INVALID')
    
    def test_format_game_description(self):
        """Test formatting game descriptions."""
        game_date = date(2024, 1, 15)
        
        # Without scores
        desc = format_game_description('SF', 'DAL', game_date)
        assert desc == "SF @ DAL (2024-01-15)"
        
        # With scores - home team wins
        desc = format_game_description('SF', 'DAL', game_date, 28, 21)
        assert desc == "SF @ DAL (2024-01-15) - DAL wins 28-21"
        
        # With scores - away team wins
        desc = format_game_description('SF', 'DAL', game_date, 21, 28)
        assert desc == "SF @ DAL (2024-01-15) - SF wins 28-21"
        
        # With tie
        desc = format_game_description('SF', 'DAL', game_date, 21, 21)
        assert desc == "SF @ DAL (2024-01-15) - SF wins 21-21"  # Away team listed as winner in tie
    
    def test_is_game_overtime(self):
        """Test overtime detection heuristic."""
        # Common overtime scores
        assert is_game_overtime(27, 24) is True
        assert is_game_overtime(30, 27) is True
        assert is_game_overtime(24, 21) is True
        
        # High-scoring close games (likely overtime)
        assert is_game_overtime(35, 32) is True
        assert is_game_overtime(41, 38) is True
        
        # Normal games (not overtime)
        assert is_game_overtime(28, 14) is False
        assert is_game_overtime(21, 7) is False
        assert is_game_overtime(24, 17) is False
        
        # Missing scores
        assert is_game_overtime(None, 24) is False
        assert is_game_overtime(27, None) is False
        assert is_game_overtime(None, None) is False
        
        # Low-scoring games
        assert is_game_overtime(10, 7) is False
        assert is_game_overtime(14, 10) is False


class TestGameModelIntegration:
    """Integration tests combining SQLAlchemy and Pydantic models."""
    
    def test_game_create_to_sqlalchemy_model(self):
        """Test converting GameCreate to SQLAlchemy model."""
        game_create = GameCreate(
            game_id="2024_01_SF_DAL",
            season=2024,
            season_type="REG",
            game_date=date(2024, 1, 15),
            home_team="DAL",
            away_team="SF",
            week=1,
            home_score=28,
            away_score=21
        )
        
        # Convert to SQLAlchemy model data (exclude relationship fields)
        game_data = game_create.model_dump(exclude={'home_team_rel', 'away_team_rel'})
        
        # Create model without triggering database relationships
        game_model = GameModel()
        for key, value in game_data.items():
            setattr(game_model, key, value)
        
        assert game_model.game_id == "2024_01_SF_DAL"
        assert game_model.season == 2024
        assert game_model.home_team == "DAL"
        assert game_model.away_team == "SF"
        assert game_model.home_score == 28
    
    def test_sqlalchemy_to_pydantic_response(self):
        """Test converting SQLAlchemy model to Pydantic response."""
        # Create SQLAlchemy model instance without triggering relationships
        game_model = GameModel()
        game_model.id = 1
        game_model.game_id = "2024_01_SF_DAL"
        game_model.season = 2024
        game_model.season_type = "REG"
        game_model.game_date = date(2024, 1, 15)
        game_model.home_team = "DAL"
        game_model.away_team = "SF"
        game_model.home_score = 28
        game_model.away_score = 21
        
        # Convert to Pydantic response
        response_data = {
            "id": game_model.id,
            "game_id": game_model.game_id,
            "season": game_model.season,
            "season_type": game_model.season_type,
            "game_date": game_model.game_date,
            "home_team": game_model.home_team,
            "away_team": game_model.away_team,
            "home_score": game_model.home_score,
            "away_score": game_model.away_score
        }
        
        response = GameResponse(**response_data)
        assert response.id == 1
        assert response.game_id == "2024_01_SF_DAL"
        assert response.home_score == 28
        assert response.away_score == 21