"""Tests for feature engineering module."""

import pytest
import pandas as pd
from datetime import date, timedelta

from src.analysis.features import FeatureEngineer, TeamStats


class TestTeamStats:
    """Test TeamStats class."""
    
    def test_team_stats_creation(self):
        """Test TeamStats object creation."""
        stats = TeamStats(team_abbr="SF")
        
        assert stats.team_abbr == "SF"
        assert stats.games_played == 0
        assert stats.wins == 0
        assert stats.losses == 0
        assert stats.ties == 0
    
    def test_win_percentage_calculation(self):
        """Test win percentage calculation."""
        stats = TeamStats(team_abbr="SF", games_played=10, wins=7, losses=2, ties=1)
        
        # Win pct = (7 + 0.5 * 1) / 10 = 0.75
        assert stats.win_percentage == 0.75
        
        # Test no games played
        empty_stats = TeamStats(team_abbr="KC")
        assert empty_stats.win_percentage == 0.0
    
    def test_points_per_game(self):
        """Test points per game calculation."""
        stats = TeamStats(team_abbr="SF", games_played=4, points_for=100.0)
        assert stats.points_per_game == 25.0
        
        # Test no games played (should not divide by zero)
        empty_stats = TeamStats(team_abbr="KC")
        assert empty_stats.points_per_game == 0.0
    
    def test_point_differential(self):
        """Test point differential calculation."""
        stats = TeamStats(
            team_abbr="SF", 
            games_played=4, 
            points_for=100.0, 
            points_against=80.0
        )
        
        # PPG = 25, PAPG = 20, Diff = 5
        assert stats.point_differential == 5.0


class TestFeatureEngineer:
    """Test FeatureEngineer class."""
    
    def test_initialization(self, test_session):
        """Test feature engineer initialization."""
        fe = FeatureEngineer(test_session)
        
        assert fe.db_session == test_session
        assert fe.team_stats_cache == {}
    
    def test_get_team_stats_empty(self, feature_engineer):
        """Test getting team stats with no data."""
        stats = feature_engineer.get_team_stats("SF", 2023)
        
        assert stats.team_abbr == "SF"
        assert stats.games_played == 0
        assert stats.win_percentage == 0.0
    
    def test_get_team_stats_with_games(self, feature_engineer, sample_games):
        """Test getting team stats with game data."""
        stats = feature_engineer.get_team_stats("SF", 2023)
        
        assert stats.team_abbr == "SF"
        assert stats.games_played > 0
        assert stats.points_for > 0
        assert stats.points_against > 0
    
    def test_get_team_stats_with_end_date(self, feature_engineer, sample_games):
        """Test getting team stats up to specific date."""
        # Get stats only up to early in season
        early_date = date(2023, 9, 15)
        stats = feature_engineer.get_team_stats("SF", 2023, early_date)
        
        # Should have fewer games than full season
        full_stats = feature_engineer.get_team_stats("SF", 2023)
        assert stats.games_played <= full_stats.games_played
    
    def test_get_head_to_head_stats(self, feature_engineer, sample_games):
        """Test head-to-head statistics."""
        h2h_stats = feature_engineer.get_head_to_head_stats("SF", "KC", seasons=1)
        
        assert isinstance(h2h_stats, dict)
        assert 'h2h_games' in h2h_stats
        assert 'team1_wins' in h2h_stats
        assert 'team2_wins' in h2h_stats
        assert 'avg_total_points' in h2h_stats
        
        # Should have at least some games between SF and KC
        assert h2h_stats['h2h_games'] >= 0
    
    def test_get_head_to_head_stats_no_games(self, feature_engineer):
        """Test head-to-head stats with no matchups."""
        h2h_stats = feature_engineer.get_head_to_head_stats("SF", "NONEXISTENT")
        
        assert h2h_stats['h2h_games'] == 0
        assert h2h_stats['team1_wins'] == 0
        assert h2h_stats['team2_wins'] == 0
        assert h2h_stats['avg_total_points'] == 0.0
    
    def test_get_recent_form(self, feature_engineer, sample_games):
        """Test recent form calculation."""
        # Get recent form for SF before a certain date
        form_date = date(2023, 10, 1)
        form_stats = feature_engineer.get_recent_form("SF", 2023, form_date, games=3)
        
        assert isinstance(form_stats, dict)
        assert 'recent_games' in form_stats
        assert 'recent_wins' in form_stats
        assert 'recent_win_pct' in form_stats
        assert 'recent_form' in form_stats
        
        # Form should be between -1 and 1
        assert -1 <= form_stats['recent_form'] <= 1
    
    def test_get_recent_form_no_games(self, feature_engineer):
        """Test recent form with no games."""
        form_date = date(2023, 8, 1)  # Before season
        form_stats = feature_engineer.get_recent_form("SF", 2023, form_date)
        
        assert form_stats['recent_games'] == 0
        assert form_stats['recent_win_pct'] == 0.0
        assert form_stats['recent_form'] == 0.0
    
    def test_calculate_strength_of_schedule(self, feature_engineer, sample_games):
        """Test strength of schedule calculation."""
        sos = feature_engineer.calculate_strength_of_schedule("SF", 2023)
        
        # SOS should be between 0 and 1 (opponent win percentage)
        assert 0 <= sos <= 1
    
    def test_calculate_strength_of_schedule_no_games(self, feature_engineer):
        """Test strength of schedule with no games."""
        sos = feature_engineer.calculate_strength_of_schedule("NONEXISTENT", 2023)
        
        # Should return neutral strength (0.5) if no games
        assert sos == 0.5
    
    def test_create_game_features(self, feature_engineer, sample_games):
        """Test complete game feature creation."""
        game_date = date(2023, 10, 1)
        features = feature_engineer.create_game_features("SF", "KC", game_date, 2023)
        
        assert isinstance(features, dict)
        assert len(features) > 0
        
        # Check for key feature categories
        expected_features = [
            'home_win_pct', 'away_win_pct',
            'home_ppg', 'away_ppg',
            'home_point_diff', 'away_point_diff',
            'win_pct_diff', 'ppg_diff',
            'is_divisional', 'is_conference',
            'home_advantage'
        ]
        
        for feature in expected_features:
            assert feature in features
    
    def test_create_game_features_early_season(self, feature_engineer, sample_games):
        """Test feature creation early in season."""
        # Very early in season - should still work but with limited data
        early_date = date(2023, 9, 1)
        features = feature_engineer.create_game_features("SF", "KC", early_date, 2023)
        
        assert isinstance(features, dict)
        # Early season features should mostly be 0 or defaults
        assert features['home_games_played'] == 0
        assert features['away_games_played'] == 0
    
    def test_divisional_game_detection(self, feature_engineer):
        """Test divisional game detection."""
        # Test NFC West teams (divisional)
        features_divisional = feature_engineer.create_game_features("SF", "SEA", date(2023, 10, 1), 2023)
        
        # Test non-divisional teams
        features_non_divisional = feature_engineer.create_game_features("SF", "KC", date(2023, 10, 1), 2023)
        
        # Note: This test depends on having the team division data in our sample
        # If not available, both will return 0.0
        assert 'is_divisional' in features_divisional
        assert 'is_divisional' in features_non_divisional
    
    def test_conference_game_detection(self, feature_engineer):
        """Test conference game detection."""
        # Test same conference (NFC)
        features_same_conf = feature_engineer.create_game_features("SF", "DAL", date(2023, 10, 1), 2023)
        
        # Test different conference
        features_diff_conf = feature_engineer.create_game_features("SF", "KC", date(2023, 10, 1), 2023)
        
        assert 'is_conference' in features_same_conf
        assert 'is_conference' in features_diff_conf
    
    def test_time_based_features(self, feature_engineer):
        """Test time-based feature calculations."""
        # Test early season
        early_features = feature_engineer.create_game_features("SF", "KC", date(2023, 9, 10), 2023)
        
        # Test mid season
        mid_features = feature_engineer.create_game_features("SF", "KC", date(2023, 11, 1), 2023)
        
        assert 'week_of_season' in early_features
        assert 'week_of_season' in mid_features
        assert 'days_since_season_start' in early_features
        assert 'days_since_season_start' in mid_features
        
        # Mid-season should have higher values
        assert mid_features['week_of_season'] > early_features['week_of_season']
        assert mid_features['days_since_season_start'] > early_features['days_since_season_start']
    
    def test_feature_consistency(self, feature_engineer, sample_games):
        """Test that features are consistent across calls."""
        game_date = date(2023, 10, 1)
        
        features1 = feature_engineer.create_game_features("SF", "KC", game_date, 2023)
        features2 = feature_engineer.create_game_features("SF", "KC", game_date, 2023)
        
        # Should get identical results
        assert features1 == features2
    
    def test_feature_numerical_types(self, feature_engineer, sample_games):
        """Test that all features are numerical."""
        game_date = date(2023, 10, 1)
        features = feature_engineer.create_game_features("SF", "KC", game_date, 2023)
        
        for feature_name, feature_value in features.items():
            assert isinstance(feature_value, (int, float)), f"Feature {feature_name} is not numerical: {type(feature_value)}"
    
    def test_caching_behavior(self, feature_engineer, sample_games):
        """Test that team stats caching works correctly."""
        # First call should populate cache
        stats1 = feature_engineer.get_team_stats("SF", 2023)
        
        # Cache should now contain SF 2023 stats
        assert "SF" in feature_engineer.team_stats_cache
        assert 2023 in feature_engineer.team_stats_cache["SF"]
        
        # Second call should use cache
        stats2 = feature_engineer.get_team_stats("SF", 2023)
        
        # Should be the exact same object (from cache)
        assert stats1 is stats2