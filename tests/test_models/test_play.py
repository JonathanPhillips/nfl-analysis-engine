"""Comprehensive tests for Play model."""

import pytest
from decimal import Decimal
from pydantic import ValidationError
from src.models.play import (
    PlayModel, PlayBase, PlayCreate, PlayUpdate, PlayResponse,
    calculate_play_success, get_down_distance_situation, 
    calculate_field_position_value, is_explosive_play,
    get_play_clock_situation, calculate_leverage_index
)
# Import models to ensure relationships are resolved
from src.models import TeamModel, GameModel


class TestPlayModel:
    """Test SQLAlchemy PlayModel."""
    
    def test_play_model_table_name(self):
        """Test that table name is correctly set."""
        assert PlayModel.__tablename__ == "plays"
    
    def test_play_model_repr(self):
        """Test string representation of play model."""
        play = PlayModel(
            play_id="2024_01_SF_DAL_1",
            game_id="2024_01_SF_DAL",
            season=2024,
            posteam="SF",
            play_type="pass",
            yards_gained=15
        )
        expected = "<Play 2024_01_SF_DAL_1: SF pass for 15 yards>"
        assert repr(play) == expected
    
    def test_play_model_required_fields(self):
        """Test that required fields are present."""
        required_fields = {
            'play_id', 'game_id', 'season'
        }
        model_columns = {col.name for col in PlayModel.__table__.columns}
        assert required_fields.issubset(model_columns)
    
    def test_play_model_optional_fields(self):
        """Test that optional fields are present."""
        optional_fields = {
            'week', 'posteam', 'defteam', 'qtr', 'game_seconds_remaining',
            'half_seconds_remaining', 'game_half', 'yardline_100', 'ydstogo',
            'down', 'play_type', 'desc', 'yards_gained', 'posteam_score',
            'defteam_score', 'score_differential', 'ep', 'epa', 'wp', 'wpa',
            'cpoe', 'pass_location', 'air_yards', 'yards_after_catch',
            'passer_player_id', 'receiver_player_id', 'rusher_player_id',
            'touchdown', 'pass_touchdown', 'rush_touchdown', 'interception',
            'fumble', 'safety', 'penalty'
        }
        model_columns = {col.name for col in PlayModel.__table__.columns}
        assert optional_fields.issubset(model_columns)


class TestPlayBase:
    """Test PlayBase Pydantic model."""
    
    def test_valid_play_creation(self):
        """Test creating a valid play."""
        play_data = {
            "play_id": "2024_01_SF_DAL_1",
            "game_id": "2024_01_SF_DAL",
            "season": 2024
        }
        
        play = PlayBase(**play_data)
        assert play.play_id == "2024_01_SF_DAL_1"
        assert play.game_id == "2024_01_SF_DAL"
        assert play.season == 2024
    
    def test_play_id_validation_empty(self):
        """Test play ID cannot be empty."""
        with pytest.raises(ValidationError) as exc_info:
            PlayBase(
                play_id="",
                game_id="2024_01_SF_DAL",
                season=2024
            )
        
        errors = exc_info.value.errors()
        assert any(error['type'] == 'string_too_short' for error in errors)
    
    def test_play_id_validation_whitespace(self):
        """Test play ID strips whitespace."""
        play = PlayBase(
            play_id="  2024_01_SF_DAL_1  ",
            game_id="2024_01_SF_DAL",
            season=2024
        )
        assert play.play_id == "2024_01_SF_DAL_1"
    
    def test_game_id_validation_empty(self):
        """Test game ID cannot be empty."""
        with pytest.raises(ValidationError) as exc_info:
            PlayBase(
                play_id="2024_01_SF_DAL_1",
                game_id="",
                season=2024
            )
        
        errors = exc_info.value.errors()
        assert any(error['type'] == 'string_too_short' for error in errors)
    
    def test_season_validation(self):
        """Test season validation constraints."""
        base_data = {
            "play_id": "2024_01_SF_DAL_1",
            "game_id": "2024_01_SF_DAL"
        }
        
        # Valid seasons
        for season in [1920, 2000, 2024, 2030]:
            play = PlayBase(**base_data, season=season)
            assert play.season == season
        
        # Invalid seasons
        for season in [1919, 2031]:
            with pytest.raises(ValidationError):
                PlayBase(**base_data, season=season)


class TestPlayCreate:
    """Test PlayCreate Pydantic model."""
    
    def test_play_create_with_all_fields(self):
        """Test creating play with all optional fields."""
        play_data = {
            "play_id": "2024_01_SF_DAL_1",
            "game_id": "2024_01_SF_DAL",
            "season": 2024,
            "week": 1,
            "posteam": "SF",
            "defteam": "DAL",
            "qtr": 1,
            "game_seconds_remaining": 3540,
            "half_seconds_remaining": 1740,
            "game_half": "half1",
            "yardline_100": 75,
            "ydstogo": 10,
            "down": 1,
            "play_type": "pass",
            "desc": "J.Garoppolo pass complete short left to D.Samuel for 15 yards",
            "yards_gained": 15,
            "posteam_score": 0,
            "defteam_score": 0,
            "score_differential": 0,
            "ep": 0.92,
            "epa": 1.45,
            "wp": 0.52,
            "wpa": 0.03,
            "cpoe": 0.15,
            "pass_location": "left",
            "air_yards": 12,
            "yards_after_catch": 3,
            "passer_player_id": "00-0036355",
            "receiver_player_id": "00-0033857",
            "touchdown": False,
            "pass_touchdown": False,
            "interception": False
        }
        
        play = PlayCreate(**play_data)
        assert play.week == 1
        assert play.posteam == "SF"
        assert play.defteam == "DAL"
        assert play.qtr == 1
        assert play.yardline_100 == 75
        assert play.play_type == "pass"
        assert play.epa == 1.45
        assert play.pass_location == "left"
        assert play.touchdown is False
    
    def test_week_validation(self):
        """Test week validation constraints."""
        base_data = {
            "play_id": "2024_01_SF_DAL_1",
            "game_id": "2024_01_SF_DAL",
            "season": 2024
        }
        
        # Valid weeks
        for week in [1, 9, 18, 22]:
            play = PlayCreate(**base_data, week=week)
            assert play.week == week
        
        # Invalid weeks
        for week in [0, 23]:
            with pytest.raises(ValidationError):
                PlayCreate(**base_data, week=week)
    
    def test_quarter_validation(self):
        """Test quarter validation."""
        base_data = {
            "play_id": "2024_01_SF_DAL_1",
            "game_id": "2024_01_SF_DAL",
            "season": 2024
        }
        
        # Valid quarters
        for qtr in [1, 2, 3, 4, 5]:  # 5 for OT
            play = PlayCreate(**base_data, qtr=qtr)
            assert play.qtr == qtr
        
        # Invalid quarters
        for qtr in [0, 6]:
            with pytest.raises(ValidationError):
                PlayCreate(**base_data, qtr=qtr)
    
    def test_seconds_remaining_validation(self):
        """Test seconds remaining validation."""
        base_data = {
            "play_id": "2024_01_SF_DAL_1",
            "game_id": "2024_01_SF_DAL",
            "season": 2024
        }
        
        # Valid game seconds
        for seconds in [0, 1800, 3600]:
            play = PlayCreate(**base_data, game_seconds_remaining=seconds)
            assert play.game_seconds_remaining == seconds
        
        # Invalid game seconds
        with pytest.raises(ValidationError):
            PlayCreate(**base_data, game_seconds_remaining=3601)
        
        # Valid half seconds
        for seconds in [0, 900, 1800]:
            play = PlayCreate(**base_data, half_seconds_remaining=seconds)
            assert play.half_seconds_remaining == seconds
        
        # Invalid half seconds
        with pytest.raises(ValidationError):
            PlayCreate(**base_data, half_seconds_remaining=1801)
    
    def test_field_position_validation(self):
        """Test field position validation."""
        base_data = {
            "play_id": "2024_01_SF_DAL_1",
            "game_id": "2024_01_SF_DAL",
            "season": 2024
        }
        
        # Valid yardlines
        for yardline in [1, 50, 99]:
            play = PlayCreate(**base_data, yardline_100=yardline)
            assert play.yardline_100 == yardline
        
        # Invalid yardlines
        for yardline in [0, 100]:
            with pytest.raises(ValidationError):
                PlayCreate(**base_data, yardline_100=yardline)
        
        # Valid yards to go
        for ydstogo in [1, 10, 99]:
            play = PlayCreate(**base_data, ydstogo=ydstogo)
            assert play.ydstogo == ydstogo
        
        # Invalid yards to go
        for ydstogo in [0, 100]:
            with pytest.raises(ValidationError):
                PlayCreate(**base_data, ydstogo=ydstogo)
    
    def test_down_validation(self):
        """Test down validation."""
        base_data = {
            "play_id": "2024_01_SF_DAL_1",
            "game_id": "2024_01_SF_DAL",
            "season": 2024
        }
        
        # Valid downs
        for down in [1, 2, 3, 4]:
            play = PlayCreate(**base_data, down=down)
            assert play.down == down
        
        # Invalid downs
        for down in [0, 5]:
            with pytest.raises(ValidationError):
                PlayCreate(**base_data, down=down)
    
    def test_yards_gained_validation(self):
        """Test yards gained validation."""
        base_data = {
            "play_id": "2024_01_SF_DAL_1",
            "game_id": "2024_01_SF_DAL",
            "season": 2024
        }
        
        # Valid yards gained
        for yards in [-99, -10, 0, 15, 99]:
            play = PlayCreate(**base_data, yards_gained=yards)
            assert play.yards_gained == yards
        
        # Invalid yards gained
        for yards in [-100, 100]:
            with pytest.raises(ValidationError):
                PlayCreate(**base_data, yards_gained=yards)
    
    def test_score_validation(self):
        """Test score validation."""
        base_data = {
            "play_id": "2024_01_SF_DAL_1",
            "game_id": "2024_01_SF_DAL",
            "season": 2024
        }
        
        # Valid scores
        for score in [0, 21, 100]:
            play = PlayCreate(**base_data, posteam_score=score, defteam_score=score)
            assert play.posteam_score == score
            assert play.defteam_score == score
        
        # Invalid scores
        with pytest.raises(ValidationError):
            PlayCreate(**base_data, posteam_score=101)
    
    def test_advanced_metrics_validation(self):
        """Test advanced metrics validation."""
        base_data = {
            "play_id": "2024_01_SF_DAL_1",
            "game_id": "2024_01_SF_DAL",
            "season": 2024
        }
        
        # Valid EP/EPA
        for ep in [-10.0, 0.0, 5.2, 10.0]:
            play = PlayCreate(**base_data, ep=ep)
            assert play.ep == ep
        
        for epa in [-15.0, 0.0, 7.5, 15.0]:
            play = PlayCreate(**base_data, epa=epa)
            assert play.epa == epa
        
        # Invalid EP/EPA
        with pytest.raises(ValidationError):
            PlayCreate(**base_data, ep=10.1)
        
        with pytest.raises(ValidationError):
            PlayCreate(**base_data, epa=-15.1)
        
        # Valid WP/WPA
        for wp in [0.0, 0.5, 1.0]:
            play = PlayCreate(**base_data, wp=wp)
            assert play.wp == wp
        
        for wpa in [-1.0, 0.0, 0.5, 1.0]:
            play = PlayCreate(**base_data, wpa=wpa)
            assert play.wpa == wpa
        
        # Invalid WP/WPA
        with pytest.raises(ValidationError):
            PlayCreate(**base_data, wp=1.1)
        
        with pytest.raises(ValidationError):
            PlayCreate(**base_data, wpa=-1.1)
    
    def test_passing_metrics_validation(self):
        """Test passing metrics validation."""
        base_data = {
            "play_id": "2024_01_SF_DAL_1",
            "game_id": "2024_01_SF_DAL",
            "season": 2024
        }
        
        # Valid CPOE
        for cpoe in [-1.0, 0.0, 0.5, 1.0]:
            play = PlayCreate(**base_data, cpoe=cpoe)
            assert play.cpoe == cpoe
        
        # Invalid CPOE
        with pytest.raises(ValidationError):
            PlayCreate(**base_data, cpoe=1.1)
        
        # Valid air yards
        for air_yards in [-20, 0, 25, 80]:
            play = PlayCreate(**base_data, air_yards=air_yards)
            assert play.air_yards == air_yards
        
        # Invalid air yards
        for air_yards in [-21, 81]:
            with pytest.raises(ValidationError):
                PlayCreate(**base_data, air_yards=air_yards)
        
        # Valid YAC
        for yac in [0, 15, 99]:
            play = PlayCreate(**base_data, yards_after_catch=yac)
            assert play.yards_after_catch == yac
        
        # Invalid YAC
        with pytest.raises(ValidationError):
            PlayCreate(**base_data, yards_after_catch=100)
    
    def test_team_abbr_validation(self):
        """Test team abbreviation validation."""
        base_data = {
            "play_id": "2024_01_SF_DAL_1",
            "game_id": "2024_01_SF_DAL",
            "season": 2024
        }
        
        # Valid uppercase teams
        play = PlayCreate(**base_data, posteam="SF", defteam="DAL")
        assert play.posteam == "SF"
        assert play.defteam == "DAL"
        
        # Invalid lowercase teams
        with pytest.raises(ValidationError):
            PlayCreate(**base_data, posteam="sf")
        
        with pytest.raises(ValidationError):
            PlayCreate(**base_data, defteam="dal")
    
    def test_play_type_validation(self):
        """Test play type validation."""
        base_data = {
            "play_id": "2024_01_SF_DAL_1",
            "game_id": "2024_01_SF_DAL",
            "season": 2024
        }
        
        # Valid play types (should be converted to lowercase)
        valid_types = ['PASS', 'pass', 'RUN', 'run', 'PUNT', 'punt']
        expected_types = ['pass', 'pass', 'run', 'run', 'punt', 'punt']
        
        for play_type, expected in zip(valid_types, expected_types):
            play = PlayCreate(**base_data, play_type=play_type)
            assert play.play_type == expected
        
        # Custom play type (should be normalized)
        play = PlayCreate(**base_data, play_type="CUSTOM_TYPE")
        assert play.play_type == "custom_type"
    
    def test_pass_location_validation(self):
        """Test pass location validation."""
        base_data = {
            "play_id": "2024_01_SF_DAL_1",
            "game_id": "2024_01_SF_DAL",
            "season": 2024
        }
        
        # Valid pass locations
        valid_locations = ['LEFT', 'left', 'MIDDLE', 'middle', 'RIGHT', 'right']
        expected_locations = ['left', 'left', 'middle', 'middle', 'right', 'right']
        
        for location, expected in zip(valid_locations, expected_locations):
            play = PlayCreate(**base_data, pass_location=location)
            assert play.pass_location == expected
        
        # Invalid pass location
        with pytest.raises(ValidationError):
            PlayCreate(**base_data, pass_location="invalid")
    
    def test_game_half_validation(self):
        """Test game half validation."""
        base_data = {
            "play_id": "2024_01_SF_DAL_1",
            "game_id": "2024_01_SF_DAL",
            "season": 2024
        }
        
        # Valid game halves
        valid_halves = ['HALF1', 'half1', 'HALF2', 'half2', 'OVERTIME', 'overtime']
        expected_halves = ['half1', 'half1', 'half2', 'half2', 'overtime', 'overtime']
        
        for half, expected in zip(valid_halves, expected_halves):
            play = PlayCreate(**base_data, game_half=half)
            assert play.game_half == expected
        
        # Invalid game half
        with pytest.raises(ValidationError):
            PlayCreate(**base_data, game_half="invalid")


class TestPlayUpdate:
    """Test PlayUpdate Pydantic model."""
    
    def test_partial_update(self):
        """Test partial play update."""
        update_data = {
            "yards_gained": 15,
            "epa": 1.45,
            "touchdown": True
        }
        
        update = PlayUpdate(**update_data)
        assert update.yards_gained == 15
        assert update.epa == 1.45
        assert update.touchdown is True
        assert update.week is None  # Not provided, should be None
    
    def test_empty_update(self):
        """Test empty update (all fields None)."""
        update = PlayUpdate()
        assert update.yards_gained is None
        assert update.epa is None
        assert update.touchdown is None
    
    def test_team_validation_in_update(self):
        """Test team validation in updates."""
        # Valid team
        update = PlayUpdate(posteam="SF")
        assert update.posteam == "SF"
        
        # Invalid team
        with pytest.raises(ValidationError):
            PlayUpdate(posteam="sf")


class TestPlayResponse:
    """Test PlayResponse Pydantic model."""
    
    def test_play_response_with_id(self):
        """Test play response includes ID."""
        response_data = {
            "id": 1,
            "play_id": "2024_01_SF_DAL_1",
            "game_id": "2024_01_SF_DAL",
            "season": 2024,
            "week": 1,
            "posteam": "SF",
            "yards_gained": 15,
            "epa": 1.45
        }
        
        response = PlayResponse(**response_data)
        assert response.id == 1
        assert response.play_id == "2024_01_SF_DAL_1"
        assert response.yards_gained == 15
        assert response.epa == 1.45


class TestPlayUtilityFunctions:
    """Test utility functions for play data."""
    
    def test_calculate_play_success(self):
        """Test play success calculation."""
        # Successful pass plays (EPA > 0)
        assert calculate_play_success(1.5, "pass") is True
        assert calculate_play_success(0.1, "run") is True
        
        # Unsuccessful plays (EPA <= 0)
        assert calculate_play_success(-0.5, "pass") is False
        assert calculate_play_success(-1.0, "run") is False
        
        # Special teams plays (different threshold)
        assert calculate_play_success(-0.3, "punt") is True
        assert calculate_play_success(-0.6, "field_goal") is False
        
        # Missing EPA
        assert calculate_play_success(None, "pass") is None
        assert calculate_play_success(1.5, None) is True  # Uses default criteria
    
    def test_get_down_distance_situation(self):
        """Test down and distance situation categorization."""
        # First down
        assert get_down_distance_situation(1, 10) == "1st_down"
        assert get_down_distance_situation(1, 5) == "1st_down"
        
        # Second down situations
        assert get_down_distance_situation(2, 3) == "2nd_short"
        assert get_down_distance_situation(2, 6) == "2nd_medium"
        assert get_down_distance_situation(2, 10) == "2nd_long"
        
        # Third down situations
        assert get_down_distance_situation(3, 2) == "3rd_short"
        assert get_down_distance_situation(3, 5) == "3rd_medium"
        assert get_down_distance_situation(3, 12) == "3rd_long"
        
        # Fourth down
        assert get_down_distance_situation(4, 1) == "4th_down"
        assert get_down_distance_situation(4, 15) == "4th_down"
        
        # Missing data
        assert get_down_distance_situation(None, 10) is None
        assert get_down_distance_situation(3, None) is None
        
        # Invalid down
        assert get_down_distance_situation(5, 10) == "unknown"
    
    def test_calculate_field_position_value(self):
        """Test field position value categorization."""
        # Red zone (1-20 yards from goal)
        assert calculate_field_position_value(10) == "red_zone"
        assert calculate_field_position_value(20) == "red_zone"
        
        # Plus territory (21-40 yards from goal)
        assert calculate_field_position_value(25) == "plus_territory"
        assert calculate_field_position_value(40) == "plus_territory"
        
        # Midfield (41-60 yards from goal)
        assert calculate_field_position_value(45) == "midfield"
        assert calculate_field_position_value(60) == "midfield"
        
        # Minus territory (61-80 yards from goal)
        assert calculate_field_position_value(65) == "minus_territory"
        assert calculate_field_position_value(80) == "minus_territory"
        
        # Own territory (81-99 yards from goal)
        assert calculate_field_position_value(85) == "own_territory"
        assert calculate_field_position_value(99) == "own_territory"
        
        # Missing data
        assert calculate_field_position_value(None) is None
    
    def test_is_explosive_play(self):
        """Test explosive play detection."""
        # Explosive pass plays (20+ yards)
        assert is_explosive_play(20, "pass") is True
        assert is_explosive_play(35, "pass") is True
        
        # Non-explosive pass plays
        assert is_explosive_play(19, "pass") is False
        assert is_explosive_play(10, "pass") is False
        
        # Explosive run plays (15+ yards)
        assert is_explosive_play(15, "run") is True
        assert is_explosive_play(25, "run") is True
        
        # Non-explosive run plays
        assert is_explosive_play(14, "run") is False
        assert is_explosive_play(5, "run") is False
        
        # Other play types (not explosive)
        assert is_explosive_play(30, "punt") is False
        assert is_explosive_play(50, "field_goal") is False
        
        # Missing data
        assert is_explosive_play(None, "pass") is False
        assert is_explosive_play(20, None) is False
    
    def test_get_play_clock_situation(self):
        """Test play clock situation categorization."""
        # First half situations
        assert get_play_clock_situation(1800, 1) == "first_half_normal"  # 30 minutes
        assert get_play_clock_situation(300, 2) == "first_half_normal"   # 5 minutes
        assert get_play_clock_situation(100, 2) == "first_half_two_minute"  # Under 2 minutes
        
        # Second half situations  
        assert get_play_clock_situation(1200, 3) == "second_half_normal"  # 20 minutes
        assert get_play_clock_situation(250, 4) == "second_half_late"     # 4+ minutes
        assert get_play_clock_situation(100, 4) == "second_half_two_minute"  # Under 2 minutes
        
        # Overtime
        assert get_play_clock_situation(600, 5) == "second_half_normal"
        
        # Missing data
        assert get_play_clock_situation(None, 4) is None
        assert get_play_clock_situation(120, None) is None
    
    def test_calculate_leverage_index(self):
        """Test leverage index calculation."""
        # High leverage situation (close game, 50/50 win probability)
        leverage = calculate_leverage_index(0.5, 0.1)
        assert leverage is not None
        assert leverage > 0
        
        # Test specific calculations
        # For 50/50 game: |0.05| / (0.5 * 0.5) = 0.05 / 0.25 = 0.2
        leverage_close = calculate_leverage_index(0.5, 0.05)
        assert leverage_close == 0.2
        
        # For 90/10 game: |0.05| / (0.9 * 0.1) = 0.05 / 0.09 = ~0.556
        leverage_blowout = calculate_leverage_index(0.9, 0.05)
        assert abs(leverage_blowout - 0.5555555555555556) < 0.0001
        
        # Test that very close games (50/50) with same WPA have lower leverage
        # than more extreme situations because denominator is larger
        # This is counterintuitive but mathematically correct given the formula
        assert leverage_close < leverage_blowout
        
        # Edge cases with extreme win probabilities
        assert calculate_leverage_index(0.0, 0.1) is None  # WP = 0
        assert calculate_leverage_index(1.0, 0.1) is None  # WP = 1
        
        # Missing data
        assert calculate_leverage_index(None, 0.1) is None
        assert calculate_leverage_index(0.5, None) is None
        
        # Leverage should be capped at 10.0
        leverage_capped = calculate_leverage_index(0.5, 5.0)  # Extreme WPA
        assert leverage_capped <= 10.0


class TestPlayModelIntegration:
    """Integration tests combining SQLAlchemy and Pydantic models."""
    
    def test_play_create_to_sqlalchemy_model(self):
        """Test converting PlayCreate to SQLAlchemy model."""
        play_create = PlayCreate(
            play_id="2024_01_SF_DAL_1",
            game_id="2024_01_SF_DAL",
            season=2024,
            week=1,
            posteam="SF",
            defteam="DAL",
            qtr=1,
            down=1,
            ydstogo=10,
            play_type="pass",
            yards_gained=15,
            epa=1.45
        )
        
        # Convert to SQLAlchemy model data (exclude relationship fields)
        play_data = play_create.model_dump(exclude={
            'game', 'poss_team', 'def_team', 'passer', 'receiver', 'rusher'
        })
        
        # Create model without triggering database relationships
        play_model = PlayModel()
        for key, value in play_data.items():
            setattr(play_model, key, value)
        
        assert play_model.play_id == "2024_01_SF_DAL_1"
        assert play_model.season == 2024
        assert play_model.posteam == "SF"
        assert play_model.play_type == "pass"
        assert play_model.epa == 1.45
    
    def test_sqlalchemy_to_pydantic_response(self):
        """Test converting SQLAlchemy model to Pydantic response."""
        # Create SQLAlchemy model instance without triggering relationships
        play_model = PlayModel()
        play_model.id = 1
        play_model.play_id = "2024_01_SF_DAL_1"
        play_model.game_id = "2024_01_SF_DAL"
        play_model.season = 2024
        play_model.week = 1
        play_model.posteam = "SF"
        play_model.play_type = "pass"
        play_model.yards_gained = 15
        play_model.epa = 1.45
        
        # Convert to Pydantic response
        response_data = {
            "id": play_model.id,
            "play_id": play_model.play_id,
            "game_id": play_model.game_id,
            "season": play_model.season,
            "week": play_model.week,
            "posteam": play_model.posteam,
            "play_type": play_model.play_type,
            "yards_gained": play_model.yards_gained,
            "epa": play_model.epa
        }
        
        response = PlayResponse(**response_data)
        assert response.id == 1
        assert response.play_id == "2024_01_SF_DAL_1"
        assert response.posteam == "SF"
        assert response.epa == 1.45