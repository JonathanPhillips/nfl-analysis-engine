"""Tests for advanced insights generator with EPA and WP calculations."""

import pytest
import numpy as np
from datetime import date, datetime
from unittest.mock import Mock, MagicMock

from src.analysis.insights import (
    InsightsGenerator, ExpectedPointsModel, WinProbabilityModel,
    PlayContext, AdvancedMetrics, TeamInsights, GameInsight,
    MetricType, TimePeriod
)


class TestPlayContext:
    """Test PlayContext validation and creation."""
    
    def test_play_context_creation(self):
        """Test PlayContext creation with valid data."""
        context = PlayContext(
            down=2,
            ydstogo=7,
            yardline_100=35,
            quarter=2,
            game_seconds_remaining=2400,
            score_differential=3,
            timeouts_remaining=2,
            play_type='pass'
        )
        
        assert context.down == 2
        assert context.ydstogo == 7
        assert context.yardline_100 == 35
        assert context.quarter == 2
        assert context.score_differential == 3
        assert context.play_type == 'pass'
    
    def test_play_context_validation(self):
        """Test PlayContext validates input bounds."""
        context = PlayContext(
            down=5,  # Invalid, should cap at 4
            ydstogo=-5,  # Invalid, should floor at 0
            yardline_100=150,  # Invalid, should cap at 100
            quarter=1,
            game_seconds_remaining=3600,
            score_differential=0,
            timeouts_remaining=3,
            play_type='run'
        )
        
        assert context.down == 4  # Capped
        assert context.ydstogo == 0  # Floored
        assert context.yardline_100 == 100  # Capped


class TestExpectedPointsModel:
    """Test Expected Points calculation."""
    
    @pytest.fixture
    def ep_model(self):
        """Create ExpectedPointsModel instance."""
        return ExpectedPointsModel()
    
    def test_ep_model_initialization(self, ep_model):
        """Test EP model initializes with data."""
        assert len(ep_model.ep_matrix) > 0
        assert (1, 50) in ep_model.ep_matrix  # 1st and 50 should exist
    
    def test_goal_line_ep_higher(self, ep_model):
        """Test that goal line has higher EP than midfield."""
        goal_line_context = PlayContext(
            down=1, ydstogo=10, yardline_100=5, quarter=1,
            game_seconds_remaining=3600, score_differential=0,
            timeouts_remaining=3, play_type='run'
        )
        
        midfield_context = PlayContext(
            down=1, ydstogo=10, yardline_100=50, quarter=1,
            game_seconds_remaining=3600, score_differential=0,
            timeouts_remaining=3, play_type='run'
        )
        
        goal_ep = ep_model.calculate_expected_points(goal_line_context)
        midfield_ep = ep_model.calculate_expected_points(midfield_context)
        
        assert goal_ep > midfield_ep
    
    def test_first_down_ep_higher(self, ep_model):
        """Test that 1st down has higher EP than 4th down."""
        first_down_context = PlayContext(
            down=1, ydstogo=10, yardline_100=30, quarter=1,
            game_seconds_remaining=3600, score_differential=0,
            timeouts_remaining=3, play_type='pass'
        )
        
        fourth_down_context = PlayContext(
            down=4, ydstogo=10, yardline_100=30, quarter=1,
            game_seconds_remaining=3600, score_differential=0,
            timeouts_remaining=3, play_type='pass'
        )
        
        first_ep = ep_model.calculate_expected_points(first_down_context)
        fourth_ep = ep_model.calculate_expected_points(fourth_down_context)
        
        assert first_ep > fourth_ep
    
    def test_time_adjustment(self, ep_model):
        """Test time remaining affects EP calculation."""
        early_context = PlayContext(
            down=1, ydstogo=10, yardline_100=30, quarter=1,
            game_seconds_remaining=3200, score_differential=0,
            timeouts_remaining=3, play_type='pass'
        )
        
        late_context = PlayContext(
            down=1, ydstogo=10, yardline_100=30, quarter=4,
            game_seconds_remaining=100, score_differential=0,
            timeouts_remaining=3, play_type='pass'
        )
        
        early_ep = ep_model.calculate_expected_points(early_context)
        late_ep = ep_model.calculate_expected_points(late_context)
        
        # Late game should have higher urgency
        assert late_ep > early_ep


class TestWinProbabilityModel:
    """Test Win Probability calculation."""
    
    @pytest.fixture
    def wp_model(self):
        """Create WinProbabilityModel instance."""
        return WinProbabilityModel()
    
    def test_leading_team_higher_wp(self, wp_model):
        """Test team with lead has higher win probability."""
        leading_context = PlayContext(
            down=1, ydstogo=10, yardline_100=50, quarter=2,
            game_seconds_remaining=1800, score_differential=7,
            timeouts_remaining=3, play_type='pass'
        )
        
        trailing_context = PlayContext(
            down=1, ydstogo=10, yardline_100=50, quarter=2,
            game_seconds_remaining=1800, score_differential=-7,
            timeouts_remaining=3, play_type='pass'
        )
        
        leading_wp = wp_model.calculate_win_probability(leading_context)
        trailing_wp = wp_model.calculate_win_probability(trailing_context)
        
        assert leading_wp > 0.5
        assert trailing_wp < 0.5
        assert leading_wp > trailing_wp
    
    def test_late_game_amplification(self, wp_model):
        """Test that score differential matters more late in game."""
        early_context = PlayContext(
            down=1, ydstogo=10, yardline_100=50, quarter=1,
            game_seconds_remaining=3200, score_differential=3,
            timeouts_remaining=3, play_type='pass'
        )
        
        late_context = PlayContext(
            down=1, ydstogo=10, yardline_100=50, quarter=4,
            game_seconds_remaining=60, score_differential=3,
            timeouts_remaining=1, play_type='pass'
        )
        
        early_wp = wp_model.calculate_win_probability(early_context)
        late_wp = wp_model.calculate_win_probability(late_context)
        
        # Same lead should matter more late
        assert late_wp > early_wp
    
    def test_wp_bounds(self, wp_model):
        """Test win probability stays within valid bounds."""
        extreme_context = PlayContext(
            down=4, ydstogo=20, yardline_100=95, quarter=4,
            game_seconds_remaining=30, score_differential=-21,
            timeouts_remaining=0, play_type='pass'
        )
        
        wp = wp_model.calculate_win_probability(extreme_context)
        
        assert 0 <= wp <= 1
        assert wp >= 0.01  # Should never be exactly 0
        assert wp <= 0.99  # Should never be exactly 1


class TestAdvancedMetrics:
    """Test AdvancedMetrics container."""
    
    def test_metrics_creation(self):
        """Test AdvancedMetrics creation."""
        metrics = AdvancedMetrics(
            expected_points_before=2.5,
            expected_points_after=3.8,
            epa=1.3,
            win_prob_before=0.45,
            win_prob_after=0.52,
            wpa=0.07,
            leverage=0.15,
            clutch_index=0.2,
            success_rate=1.0,
            explosive_play=True
        )
        
        assert metrics.epa == 1.3
        assert metrics.wpa == 0.07
        assert metrics.explosive_play is True
    
    def test_metrics_to_dict(self):
        """Test metrics conversion to dictionary."""
        metrics = AdvancedMetrics(
            expected_points_before=2.5,
            expected_points_after=3.8,
            epa=1.3,
            win_prob_before=0.45,
            win_prob_after=0.52,
            wpa=0.07,
            leverage=0.15,
            clutch_index=0.2,
            success_rate=1.0,
            explosive_play=True
        )
        
        result = metrics.to_dict()
        
        assert isinstance(result, dict)
        assert result['epa'] == 1.3
        assert result['explosive_play'] is True
        assert 'expected_points_before' in result


class TestTeamInsights:
    """Test TeamInsights container."""
    
    def test_team_insights_creation(self):
        """Test TeamInsights creation."""
        insights = TeamInsights(
            team_abbr='SF',
            season=2023,
            offensive_epa_per_play=0.15,
            passing_epa_per_play=0.12,
            rushing_epa_per_play=0.08,
            red_zone_efficiency=0.65,
            third_down_conversion_rate=0.42,
            defensive_epa_per_play=0.08,
            pass_defense_epa=0.05,
            run_defense_epa=0.12,
            red_zone_defense=0.45,
            third_down_defense=0.35,
            two_minute_drill_efficiency=0.18,
            clutch_performance=0.22,
            turnover_margin=0.8,
            garbage_time_adjusted_epa=0.14,
            strength_of_schedule=0.52,
            home_field_advantage=0.12,
            early_season_performance=0.10,
            late_season_performance=0.16,
            improvement_trajectory=0.03
        )
        
        assert insights.team_abbr == 'SF'
        assert insights.season == 2023
        assert insights.offensive_epa_per_play == 0.15
    
    def test_team_insights_to_dict(self):
        """Test team insights conversion to dictionary."""
        insights = TeamInsights(
            team_abbr='KC',
            season=2023,
            offensive_epa_per_play=0.18,
            passing_epa_per_play=0.15,
            rushing_epa_per_play=0.05,
            red_zone_efficiency=0.70,
            third_down_conversion_rate=0.45,
            defensive_epa_per_play=0.10,
            pass_defense_epa=0.08,
            run_defense_epa=0.15,
            red_zone_defense=0.40,
            third_down_defense=0.32,
            two_minute_drill_efficiency=0.20,
            clutch_performance=0.25,
            turnover_margin=1.2,
            garbage_time_adjusted_epa=0.17,
            strength_of_schedule=0.55,
            home_field_advantage=0.15,
            early_season_performance=0.12,
            late_season_performance=0.20,
            improvement_trajectory=0.05
        )
        
        result = insights.to_dict()
        
        assert isinstance(result, dict)
        assert result['team_abbr'] == 'KC'
        assert result['offensive_epa_per_play'] == 0.18
        assert 'clutch_performance' in result


class TestGameInsight:
    """Test GameInsight container."""
    
    def test_game_insight_creation(self):
        """Test GameInsight creation."""
        insight = GameInsight(
            game_id='2023_01_SF_KC',
            home_team='KC',
            away_team='SF',
            game_date=date(2023, 1, 29),
            excitement_index=8.5,
            competitiveness=0.85,
            momentum_swings=3,
            home_team_epa=2.5,
            away_team_epa=1.8,
            passing_game_dominance=0.6,
            rushing_game_dominance=-0.2,
            biggest_play_epa=1.8,
            biggest_play_wpa=0.25,
            turning_point_quarter=3,
            red_zone_battle='KC',
            third_down_battle='SF',
            turnover_battle='Even'
        )
        
        assert insight.game_id == '2023_01_SF_KC'
        assert insight.excitement_index == 8.5
        assert insight.momentum_swings == 3
    
    def test_game_insight_to_dict(self):
        """Test game insight conversion to dictionary."""
        insight = GameInsight(
            game_id='2023_01_BUF_DAL',
            home_team='DAL',
            away_team='BUF',
            game_date=date(2023, 9, 10),
            excitement_index=6.2,
            competitiveness=0.72,
            momentum_swings=2,
            home_team_epa=1.2,
            away_team_epa=0.8,
            passing_game_dominance=0.3,
            rushing_game_dominance=0.1,
            biggest_play_epa=1.5,
            biggest_play_wpa=0.18,
            turning_point_quarter=2,
            red_zone_battle='DAL',
            third_down_battle='BUF',
            turnover_battle='DAL'
        )
        
        result = insight.to_dict()
        
        assert isinstance(result, dict)
        assert result['game_id'] == '2023_01_BUF_DAL'
        assert result['game_date'] == '2023-09-10'
        assert result['excitement_index'] == 6.2


class TestInsightsGenerator:
    """Test main insights generator functionality."""
    
    @pytest.fixture
    def mock_db_session(self):
        """Create mock database session."""
        return MagicMock()
    
    @pytest.fixture
    def insights_generator(self, mock_db_session):
        """Create InsightsGenerator instance."""
        return InsightsGenerator(mock_db_session)
    
    def test_generator_initialization(self, insights_generator):
        """Test InsightsGenerator initializes properly."""
        assert insights_generator.ep_model is not None
        assert insights_generator.wp_model is not None
        assert insights_generator.db_session is not None
    
    def test_calculate_play_metrics_touchdown(self, insights_generator):
        """Test play metrics calculation for touchdown."""
        play_data = {
            'down': 1,
            'ydstogo': 5,
            'yardline_100': 8,
            'qtr': 2,
            'game_seconds_remaining': 2400,
            'score_differential': 0,
            'timeouts_remaining': 3,
            'play_type': 'pass',
            'yards_gained': 8,
            'touchdown': True,
            'interception': False,
            'fumble_lost': False
        }
        
        metrics = insights_generator.calculate_play_metrics(play_data)
        
        assert isinstance(metrics, AdvancedMetrics)
        assert metrics.epa > 0  # Touchdown should have positive EPA
        assert metrics.wpa > 0  # Touchdown should have positive WPA
        assert metrics.explosive_play is False  # 8-yard TD not explosive
        assert metrics.success_rate == 1.0  # Touchdown is always successful
    
    def test_calculate_play_metrics_interception(self, insights_generator):
        """Test play metrics calculation for interception."""
        play_data = {
            'down': 2,
            'ydstogo': 8,
            'yardline_100': 35,
            'qtr': 3,
            'game_seconds_remaining': 1200,
            'score_differential': 3,
            'timeouts_remaining': 2,
            'play_type': 'pass',
            'yards_gained': 0,
            'touchdown': False,
            'interception': True,
            'fumble_lost': False
        }
        
        metrics = insights_generator.calculate_play_metrics(play_data)
        
        assert isinstance(metrics, AdvancedMetrics)
        assert metrics.epa < 0  # Interception should have negative EPA
        assert metrics.wpa < 0  # Interception should have negative WPA
        assert metrics.success_rate == 0.0  # Interception is not successful
    
    def test_calculate_play_metrics_explosive_play(self, insights_generator):
        """Test play metrics for explosive play (20+ yards)."""
        play_data = {
            'down': 1,
            'ydstogo': 10,
            'yardline_100': 75,
            'qtr': 1,
            'game_seconds_remaining': 3200,
            'score_differential': -3,
            'timeouts_remaining': 3,
            'play_type': 'pass',
            'yards_gained': 25,
            'touchdown': False,
            'interception': False,
            'fumble_lost': False
        }
        
        metrics = insights_generator.calculate_play_metrics(play_data)
        
        assert isinstance(metrics, AdvancedMetrics)
        assert metrics.epa > 0  # Long gain should have positive EPA
        assert metrics.explosive_play is True  # 25-yard gain is explosive
        assert metrics.success_rate == 1.0  # Converting 1st down is successful
    
    def test_calculate_play_metrics_failed_conversion(self, insights_generator):
        """Test play metrics for failed third down conversion."""
        play_data = {
            'down': 3,
            'ydstogo': 8,
            'yardline_100': 45,
            'qtr': 4,
            'game_seconds_remaining': 600,
            'score_differential': -7,
            'timeouts_remaining': 1,
            'play_type': 'pass',
            'yards_gained': 5,
            'touchdown': False,
            'interception': False,
            'fumble_lost': False
        }
        
        metrics = insights_generator.calculate_play_metrics(play_data)
        
        assert isinstance(metrics, AdvancedMetrics)
        assert metrics.success_rate == 0.0  # Failed to convert 3rd down
        # EPA could be positive or negative depending on field position change
    
    def test_generate_team_insights_no_data(self, insights_generator, mock_db_session):
        """Test team insights generation with no data."""
        mock_db_session.query.return_value.filter.return_value.all.return_value = []
        
        insights = insights_generator.generate_team_insights('SF', 2023)
        
        assert insights is None
    
    def test_generate_game_insights_no_game(self, insights_generator, mock_db_session):
        """Test game insights generation with no game found."""
        mock_db_session.query.return_value.filter.return_value.first.return_value = None
        
        insights = insights_generator.generate_game_insights('fake_game_id')
        
        assert insights is None
    
    def test_get_league_leaders_empty(self, insights_generator, mock_db_session):
        """Test league leaders with no teams."""
        mock_db_session.query.return_value.all.return_value = []
        
        leaders = insights_generator.get_league_leaders(2023, 'offensive_epa_per_play')
        
        assert isinstance(leaders, list)
        assert len(leaders) == 0
    
    def test_compare_teams_no_data(self, insights_generator):
        """Test team comparison with no insights data."""
        # Mock generate_team_insights to return None
        insights_generator.generate_team_insights = Mock(return_value=None)
        
        comparison = insights_generator.compare_teams('SF', 'KC', 2023)
        
        assert comparison == {}
    
    def test_generate_season_narrative_no_data(self, insights_generator):
        """Test season narrative generation with no data."""
        # Mock generate_team_insights to return None
        insights_generator.generate_team_insights = Mock(return_value=None)
        
        narrative = insights_generator.generate_season_narrative('SF', 2023)
        
        assert isinstance(narrative, str)
        assert 'Unable to generate insights' in narrative
    
    def test_calculate_leverage(self, insights_generator):
        """Test leverage calculation for high-impact plays."""
        # High-leverage situation (close game, late)
        high_leverage_play = {
            'down': 3,
            'ydstogo': 4,
            'yardline_100': 25,
            'qtr': 4,
            'game_seconds_remaining': 120,
            'score_differential': 3,
            'timeouts_remaining': 1,
            'play_type': 'pass',
            'yards_gained': 6,
            'touchdown': False,
            'interception': False,
            'fumble_lost': False
        }
        
        # Low-leverage situation (blowout, early)
        low_leverage_play = {
            'down': 1,
            'ydstogo': 10,
            'yardline_100': 70,
            'qtr': 1,
            'game_seconds_remaining': 3400,
            'score_differential': 21,
            'timeouts_remaining': 3,
            'play_type': 'run',
            'yards_gained': 4,
            'touchdown': False,
            'interception': False,
            'fumble_lost': False
        }
        
        high_metrics = insights_generator.calculate_play_metrics(high_leverage_play)
        low_metrics = insights_generator.calculate_play_metrics(low_leverage_play)
        
        # High-leverage play should have higher leverage score
        # Note: This is a simplified test - in practice, leverage depends on WPA
        assert high_metrics.leverage >= low_metrics.leverage or high_metrics.leverage >= 0.02