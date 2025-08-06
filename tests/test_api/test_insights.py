"""Tests for insights API endpoints."""

import pytest
from fastapi.testclient import TestClient
from datetime import date
from unittest.mock import Mock, patch

from src.api.main import app
from src.models.team import TeamModel
from src.models.game import GameModel
from src.analysis.insights import TeamInsights, GameInsight, AdvancedMetrics


class TestInsightsAPI:
    """Test insights API endpoints."""
    
    def setup_method(self):
        """Set up test client."""
        self.client = TestClient(app)
    
    @pytest.fixture
    def mock_insights_generator(self):
        """Mock insights generator."""
        with patch('src.api.insights.InsightsGenerator') as mock:
            yield mock.return_value
    
    @pytest.fixture
    def sample_play_data(self):
        """Sample play data for testing."""
        return {
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
    
    @pytest.fixture
    def sample_team_insights(self):
        """Sample team insights data."""
        return TeamInsights(
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
    
    @pytest.fixture
    def sample_game_insights(self):
        """Sample game insights data."""
        return GameInsight(
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
    
    @pytest.fixture
    def sample_advanced_metrics(self):
        """Sample advanced metrics data."""
        return AdvancedMetrics(
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
    
    def test_calculate_play_metrics_success(self, mock_insights_generator, sample_play_data, sample_advanced_metrics):
        """Test successful play metrics calculation."""
        mock_insights_generator.calculate_play_metrics.return_value = sample_advanced_metrics
        
        response = self.client.post("/api/v1/insights/play-metrics", json=sample_play_data)
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"
        assert "data" in data
        assert data["data"]["epa"] == 1.3
        assert data["data"]["explosive_play"] is True
        mock_insights_generator.calculate_play_metrics.assert_called_once()
    
    def test_calculate_play_metrics_error(self, mock_insights_generator, sample_play_data):
        """Test play metrics calculation error handling."""
        mock_insights_generator.calculate_play_metrics.side_effect = ValueError("Invalid play data")
        
        response = self.client.post("/api/v1/insights/play-metrics", json=sample_play_data)
        
        assert response.status_code == 400
        data = response.json()
        assert "Error calculating play metrics" in data["detail"]
    
    def test_get_team_insights_success(self, mock_insights_generator, sample_team_insights):
        """Test successful team insights retrieval."""
        mock_insights_generator.generate_team_insights.return_value = sample_team_insights
        
        response = self.client.get("/api/v1/insights/team/SF/2023")
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"
        assert "SF" in data["message"]
        assert "data" in data
        assert data["data"]["team_abbr"] == "SF"
        assert data["data"]["season"] == 2023
        mock_insights_generator.generate_team_insights.assert_called_once_with("SF", 2023)
    
    def test_get_team_insights_not_found(self, mock_insights_generator):
        """Test team insights not found."""
        mock_insights_generator.generate_team_insights.return_value = None
        
        response = self.client.get("/api/v1/insights/team/INVALID/2023")
        
        assert response.status_code == 404
        data = response.json()
        assert "No insights found" in data["detail"]
    
    def test_get_team_insights_error(self, mock_insights_generator):
        """Test team insights error handling."""
        mock_insights_generator.generate_team_insights.side_effect = Exception("Database error")
        
        response = self.client.get("/api/v1/insights/team/SF/2023")
        
        assert response.status_code == 500
        data = response.json()
        assert "Error generating team insights" in data["detail"]
    
    def test_get_game_insights_success(self, mock_insights_generator, sample_game_insights):
        """Test successful game insights retrieval."""
        mock_insights_generator.generate_game_insights.return_value = sample_game_insights
        
        response = self.client.get("/api/v1/insights/game/2023_01_SF_KC")
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"
        assert "data" in data
        assert data["data"]["game_id"] == "2023_01_SF_KC"
        assert data["data"]["excitement_index"] == 8.5
        mock_insights_generator.generate_game_insights.assert_called_once_with("2023_01_SF_KC")
    
    def test_get_game_insights_not_found(self, mock_insights_generator):
        """Test game insights not found."""
        mock_insights_generator.generate_game_insights.return_value = None
        
        response = self.client.get("/api/v1/insights/game/invalid_game")
        
        assert response.status_code == 404
        data = response.json()
        assert "No insights found" in data["detail"]
    
    def test_get_league_leaders_success(self, mock_insights_generator):
        """Test successful league leaders retrieval."""
        sample_leaders = [
            {
                'team_abbr': 'KC',
                'team_name': 'Kansas City Chiefs',
                'metric': 'offensive_epa_per_play',
                'value': 0.25
            },
            {
                'team_abbr': 'SF',
                'team_name': 'San Francisco 49ers',
                'metric': 'offensive_epa_per_play',
                'value': 0.22
            }
        ]
        mock_insights_generator.get_league_leaders.return_value = sample_leaders
        
        response = self.client.get("/api/v1/insights/league-leaders/2023?metric=offensive_epa_per_play")
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"
        assert "data" in data
        assert data["data"]["season"] == 2023
        assert data["data"]["metric"] == "offensive_epa_per_play"
        assert len(data["data"]["leaders"]) == 2
        assert data["data"]["leaders"][0]["team_abbr"] == "KC"
        mock_insights_generator.get_league_leaders.assert_called_once_with(2023, "offensive_epa_per_play", 10)
    
    def test_get_league_leaders_with_limit(self, mock_insights_generator):
        """Test league leaders with custom limit."""
        mock_insights_generator.get_league_leaders.return_value = []
        
        response = self.client.get("/api/v1/insights/league-leaders/2023?metric=defensive_epa_per_play&limit=5")
        
        assert response.status_code == 200
        mock_insights_generator.get_league_leaders.assert_called_once_with(2023, "defensive_epa_per_play", 5)
    
    def test_compare_teams_success(self, mock_insights_generator):
        """Test successful team comparison."""
        sample_comparison = {
            'team1': 'SF',
            'team2': 'KC',
            'season': 2023,
            'advantages': {
                'SF': ['red_zone_efficiency'],
                'KC': ['offensive_epa_per_play']
            },
            'metrics_comparison': {
                'offensive_epa_per_play': {
                    'SF': 0.15,
                    'KC': 0.25,
                    'advantage': 'KC',
                    'difference': 0.10
                }
            }
        }
        mock_insights_generator.compare_teams.return_value = sample_comparison
        
        response = self.client.get("/api/v1/insights/compare/SF/KC/2023")
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"
        assert "SF vs KC" in data["message"]
        assert data["data"]["team1"] == "SF"
        assert data["data"]["team2"] == "KC"
        mock_insights_generator.compare_teams.assert_called_once_with("SF", "KC", 2023)
    
    def test_compare_teams_not_found(self, mock_insights_generator):
        """Test team comparison when data not available."""
        mock_insights_generator.compare_teams.return_value = {}
        
        response = self.client.get("/api/v1/insights/compare/SF/INVALID/2023")
        
        assert response.status_code == 404
        data = response.json()
        assert "Unable to compare" in data["detail"]
    
    def test_get_season_narrative_success(self, mock_insights_generator):
        """Test successful season narrative generation."""
        sample_narrative = "The San Francisco 49ers had an outstanding 2023 season..."
        mock_insights_generator.generate_season_narrative.return_value = sample_narrative
        
        response = self.client.get("/api/v1/insights/narrative/SF/2023")
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"
        assert data["data"]["team"] == "SF"
        assert data["data"]["season"] == 2023
        assert data["data"]["narrative"] == sample_narrative
        mock_insights_generator.generate_season_narrative.assert_called_once_with("SF", 2023)
    
    def test_get_available_metrics_success(self):
        """Test available metrics endpoint."""
        response = self.client.get("/api/v1/insights/available-metrics")
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"
        assert "data" in data
        assert "offensive_metrics" in data["data"]
        assert "defensive_metrics" in data["data"]
        assert "situational_metrics" in data["data"]
        
        # Check specific metrics exist
        offensive_metrics = data["data"]["offensive_metrics"]
        metric_names = [m["name"] for m in offensive_metrics]
        assert "offensive_epa_per_play" in metric_names
        assert "passing_epa_per_play" in metric_names
        assert "red_zone_efficiency" in metric_names
    
    def test_case_insensitive_team_abbreviations(self, mock_insights_generator, sample_team_insights):
        """Test that team abbreviations are case insensitive."""
        mock_insights_generator.generate_team_insights.return_value = sample_team_insights
        
        # Test lowercase
        response = self.client.get("/api/v1/insights/team/sf/2023")
        assert response.status_code == 200
        mock_insights_generator.generate_team_insights.assert_called_with("SF", 2023)
        
        # Test mixed case
        response = self.client.get("/api/v1/insights/compare/sf/kc/2023")
        assert response.status_code == 404  # Will fail because compare returns {}
        mock_insights_generator.compare_teams.assert_called_with("SF", "KC", 2023)
    
    def test_invalid_play_metrics_data(self):
        """Test play metrics with invalid data."""
        invalid_data = {
            "down": 5,  # Invalid down
            "ydstogo": -5,  # Invalid yards to go
            "yardline_100": 150  # Invalid yard line
        }
        
        response = self.client.post("/api/v1/insights/play-metrics", json=invalid_data)
        
        # Should return 400 due to validation or calculation error
        assert response.status_code == 400
    
    def test_league_leaders_limit_validation(self):
        """Test league leaders limit parameter validation."""
        # Test limit too high
        response = self.client.get("/api/v1/insights/league-leaders/2023?metric=offensive_epa_per_play&limit=50")
        assert response.status_code == 422  # Validation error
        
        # Test limit too low
        response = self.client.get("/api/v1/insights/league-leaders/2023?metric=offensive_epa_per_play&limit=0")
        assert response.status_code == 422  # Validation error
    
    def test_missing_required_parameters(self):
        """Test endpoints with missing required parameters."""
        # Missing metric for league leaders
        response = self.client.get("/api/v1/insights/league-leaders/2023")
        assert response.status_code == 422
        
        # Empty play data
        response = self.client.post("/api/v1/insights/play-metrics", json={})
        assert response.status_code == 422


class TestInsightsIntegration:
    """Integration tests for insights functionality."""
    
    def setup_method(self):
        """Set up test client."""
        self.client = TestClient(app)
    
    @pytest.mark.integration
    def test_full_insights_workflow(self):
        """Test complete insights workflow with mocked data."""
        # This would require actual database setup
        # For now, just test that endpoints exist
        
        # Test available metrics (no auth required)
        response = self.client.get("/api/v1/insights/available-metrics")
        assert response.status_code == 200
        
        # Other endpoints would fail without database, but structure is tested
        response = self.client.get("/api/v1/insights/team/SF/2023")
        # Expect 500 due to database connection in test env
        assert response.status_code in [404, 500]
    
    @pytest.mark.integration
    @patch('src.api.insights.InsightsGenerator')
    def test_insights_error_handling(self, mock_generator_class):
        """Test insights error handling in integration context."""
        # Mock generator to raise database connection error
        mock_generator = Mock()
        mock_generator.generate_team_insights.side_effect = ConnectionError("Database unavailable")
        mock_generator_class.return_value = mock_generator
        
        response = self.client.get("/api/v1/insights/team/SF/2023")
        
        assert response.status_code == 500
        data = response.json()
        assert "Error generating team insights" in data["detail"]