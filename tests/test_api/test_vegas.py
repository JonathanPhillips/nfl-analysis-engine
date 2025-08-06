"""Tests for Vegas lines API endpoints."""

import pytest
from fastapi.testclient import TestClient
from datetime import date, datetime, timedelta
from unittest.mock import Mock, patch, MagicMock

from src.api.main import create_app
from src.analysis.vegas import ValueBet, ValidationMetrics, BetType
from src.models.game import GameModel


# Use test_client fixture from conftest.py instead of creating our own


@pytest.fixture  
def mock_trained_predictor():
    """Mock trained predictor."""
    predictor = MagicMock()
    predictor.is_trained = True
    return predictor


@pytest.fixture
def mock_vegas_validator():
    """Mock Vegas validator."""
    validator = MagicMock()
    validator.predictor.is_trained = True
    return validator


@pytest.fixture
def sample_value_bets():
    """Create sample value bets."""
    return [
        ValueBet(
            game_id="2023_10_KC_SF",
            home_team="SF",
            away_team="KC", 
            game_date=date(2023, 10, 1),
            bet_type=BetType.MONEYLINE,
            recommendation="home",
            model_probability=0.65,
            vegas_probability=0.55,
            expected_value=0.08,
            confidence=0.30,
            reasoning="Model edge: 10%"
        ),
        ValueBet(
            game_id="2023_10_BUF_DAL",
            home_team="DAL",
            away_team="BUF",
            game_date=date(2023, 10, 2),
            bet_type=BetType.MONEYLINE,
            recommendation="away",
            model_probability=0.58,
            vegas_probability=0.45,
            expected_value=0.12,
            confidence=0.25,
            reasoning="Vegas undervalues away team"
        )
    ]


class TestValueBetsEndpoint:
    """Test value bets endpoint."""
    
    @patch('src.api.routers.vegas.get_vegas_validator')
    def test_get_value_bets_success(self, mock_get_validator, test_client, 
                                   mock_vegas_validator, sample_value_bets):
        """Test successful value bets retrieval."""
        mock_get_validator.return_value = mock_vegas_validator
        mock_vegas_validator.get_upcoming_value_bets.return_value = sample_value_bets
        
        response = test_client.get("/api/v1/vegas/value-bets?weeks_ahead=1&min_edge=0.05")
        
        assert response.status_code == 200
        data = response.json()
        
        assert len(data) == 2
        assert data[0]["home_team"] == "SF"
        assert data[0]["recommendation"] == "home"
        assert data[0]["expected_value"] == 0.08
        assert data[1]["home_team"] == "DAL"
        assert data[1]["recommendation"] == "away"
    
    @patch('src.api.routers.vegas.get_vegas_validator')
    def test_get_value_bets_untrained_model(self, mock_get_validator, test_client):
        """Test value bets with untrained model."""
        mock_validator = MagicMock()
        mock_validator.predictor.is_trained = False
        mock_get_validator.return_value = mock_validator
        
        response = test_client.get("/api/v1/vegas/value-bets")
        
        assert response.status_code == 400
        assert "Model must be trained" in response.json()["detail"]
    
    @patch('src.api.routers.vegas.get_vegas_validator')
    def test_get_value_bets_no_opportunities(self, mock_get_validator, test_client,
                                           mock_vegas_validator):
        """Test when no value bets are found."""
        mock_get_validator.return_value = mock_vegas_validator
        mock_vegas_validator.get_upcoming_value_bets.return_value = []
        
        response = test_client.get("/api/v1/vegas/value-bets")
        
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 0
    
    @patch('src.api.routers.vegas.get_vegas_validator')
    def test_get_value_bets_confidence_filter(self, mock_get_validator, test_client,
                                            mock_vegas_validator, sample_value_bets):
        """Test confidence filtering of value bets."""
        mock_get_validator.return_value = mock_vegas_validator
        mock_vegas_validator.get_upcoming_value_bets.return_value = sample_value_bets
        
        # Filter with high confidence threshold
        response = test_client.get("/api/v1/vegas/value-bets?min_confidence=0.35")
        
        assert response.status_code == 200
        data = response.json()
        # Should filter out bets with confidence < 0.35
        assert len(data) == 0  # Both sample bets have confidence < 0.35
    
    def test_get_value_bets_invalid_parameters(self, test_client):
        """Test with invalid query parameters."""
        # Invalid weeks_ahead
        response = test_client.get("/api/v1/vegas/value-bets?weeks_ahead=10")
        assert response.status_code == 422
        
        # Invalid min_edge
        response = test_client.get("/api/v1/vegas/value-bets?min_edge=0.5")
        assert response.status_code == 422
        
        # Invalid min_confidence
        response = test_client.get("/api/v1/vegas/value-bets?min_confidence=1.5")
        assert response.status_code == 422


class TestValidateModelEndpoint:
    """Test model validation endpoint."""
    
    @patch('src.api.routers.vegas.get_vegas_validator')
    @patch('src.api.routers.vegas.get_db_session')
    def test_validate_model_success(self, mock_get_db, mock_get_validator, test_client):
        """Test successful model validation."""
        # Mock database query
        mock_db = MagicMock()
        mock_get_db.return_value = mock_db
        
        # Mock completed games
        mock_game = GameModel(
            game_id="2023_01_KC_SF",
            season=2023,
            game_date=date(2023, 9, 10),
            home_team="SF",
            away_team="KC",
            home_score=24,
            away_score=21
        )
        mock_db.query.return_value.filter.return_value.all.return_value = [mock_game]
        
        # Mock validator
        mock_validator = MagicMock()
        mock_validator.predictor.is_trained = True
        
        # Mock prediction
        mock_prediction = Mock()
        mock_validator.predictor.predict_game.return_value = mock_prediction
        
        # Mock validation metrics
        mock_metrics = ValidationMetrics(
            total_predictions=1,
            agreement_rate=0.75,
            avg_probability_difference=0.08,
            calibration_error=0.05,
            value_bet_accuracy=0.62,
            kelly_criterion_roi=0.10,
            sharpe_ratio=1.2,
            max_drawdown=0.03
        )
        mock_validator.validate_predictions.return_value = mock_metrics
        mock_validator.create_mock_vegas_lines.return_value = []
        
        mock_get_validator.return_value = mock_validator
        
        response = test_client.post(
            "/api/v1/vegas/validate?start_date=2023-09-01&end_date=2023-09-30"
        )
        
        assert response.status_code == 200
        data = response.json()
        
        assert "metrics" in data
        assert data["metrics"]["agreement_rate"] == 0.75
        assert data["metrics"]["kelly_criterion_roi"] == 0.10
        assert "interpretation" in data
    
    @patch('src.api.routers.vegas.get_vegas_validator')
    def test_validate_model_untrained(self, mock_get_validator, test_client):
        """Test validation with untrained model."""
        mock_validator = MagicMock()
        mock_validator.predictor.is_trained = False
        mock_get_validator.return_value = mock_validator
        
        response = test_client.post(
            "/api/v1/vegas/validate?start_date=2023-09-01&end_date=2023-09-30"
        )
        
        assert response.status_code == 400
        assert "Model must be trained" in response.json()["detail"]
    
    @patch('src.api.routers.vegas.get_vegas_validator')
    @patch('src.api.routers.vegas.get_db_session')
    def test_validate_model_no_games(self, mock_get_db, mock_get_validator, test_client):
        """Test validation when no completed games exist."""
        mock_db = MagicMock()
        mock_db.query.return_value.filter.return_value.all.return_value = []
        mock_get_db.return_value = mock_db
        
        mock_validator = MagicMock()
        mock_validator.predictor.is_trained = True
        mock_get_validator.return_value = mock_validator
        
        response = test_client.post(
            "/api/v1/vegas/validate?start_date=2023-09-01&end_date=2023-09-30"
        )
        
        assert response.status_code == 404
        assert "No completed games found" in response.json()["detail"]


class TestOddsCalculatorEndpoint:
    """Test odds calculator endpoint."""
    
    @patch('src.api.routers.vegas.get_vegas_validator')
    def test_calculate_odds_success(self, mock_get_validator, test_client):
        """Test successful odds calculation."""
        mock_validator = MagicMock()
        mock_validator.probability_to_odds.return_value = -150
        mock_get_validator.return_value = mock_validator
        
        response = test_client.get("/api/v1/vegas/odds-calculator?probability=0.6")
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["probability"] == 0.6
        assert data["american_odds"] == -150
        assert "decimal_odds" in data
        assert "interpretation" in data
        assert data["interpretation"]["favorite_or_underdog"] == "Favorite"
    
    def test_calculate_odds_invalid_probability(self, test_client):
        """Test odds calculation with invalid probability."""
        # Probability too high
        response = test_client.get("/api/v1/vegas/odds-calculator?probability=1.1")
        assert response.status_code == 422
        
        # Probability too low
        response = test_client.get("/api/v1/vegas/odds-calculator?probability=0.001")
        assert response.status_code == 422


class TestProbabilityCalculatorEndpoint:
    """Test probability calculator endpoint."""
    
    @patch('src.api.routers.vegas.get_vegas_validator')
    def test_calculate_probability_success(self, mock_get_validator, test_client):
        """Test successful probability calculation."""
        mock_validator = MagicMock()
        mock_validator.odds_to_probability.return_value = 0.6
        mock_get_validator.return_value = mock_validator
        
        response = test_client.get("/api/v1/vegas/probability-calculator?american_odds=-150")
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["american_odds"] == -150
        assert data["implied_probability"] == 0.6
        assert data["percentage"] == "60.0%"
        assert "interpretation" in data
        assert data["interpretation"]["favorite_or_underdog"] == "Favorite"
    
    def test_calculate_probability_zero_odds(self, test_client):
        """Test probability calculation with zero odds."""
        response = test_client.get("/api/v1/vegas/probability-calculator?american_odds=0")
        
        assert response.status_code == 400
        assert "cannot be 0" in response.json()["detail"]
    
    def test_calculate_probability_invalid_odds(self, test_client):
        """Test probability calculation with invalid odds."""
        # Odds too high
        response = test_client.get("/api/v1/vegas/probability-calculator?american_odds=2000")
        assert response.status_code == 422
        
        # Odds too low  
        response = test_client.get("/api/v1/vegas/probability-calculator?american_odds=-2000")
        assert response.status_code == 422


class TestExpectedValueEndpoint:
    """Test expected value calculator endpoint."""
    
    @patch('src.api.routers.vegas.get_vegas_validator')
    def test_calculate_expected_value_success(self, mock_get_validator, test_client):
        """Test successful expected value calculation."""
        mock_validator = MagicMock()
        mock_validator.calculate_expected_value.return_value = 0.15
        mock_validator.kelly_criterion.return_value = 0.08
        mock_validator.odds_to_probability.return_value = 0.55
        mock_get_validator.return_value = mock_validator
        
        response = test_client.post(
            "/api/v1/vegas/expected-value"
            "?model_probability=0.65"
            "&american_odds=-120" 
            "&bet_size=10.0"
        )
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["model_probability"] == 0.65
        assert data["expected_value"] == 0.15
        assert data["kelly_fraction"] == 0.08
        assert "analysis" in data
        assert "has_edge" in data["analysis"]
    
    @patch('src.api.routers.vegas.get_vegas_validator')
    def test_calculate_expected_value_negative_ev(self, mock_get_validator, test_client):
        """Test expected value calculation with negative EV."""
        mock_validator = MagicMock()
        mock_validator.calculate_expected_value.return_value = -0.05
        mock_validator.kelly_criterion.return_value = 0.0
        mock_validator.odds_to_probability.return_value = 0.7
        mock_get_validator.return_value = mock_validator
        
        response = test_client.post(
            "/api/v1/vegas/expected-value"
            "?model_probability=0.45"
            "&american_odds=-200"
            "&bet_size=1.0"
        )
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["expected_value"] == -0.05
        assert data["analysis"]["has_edge"] == False
        assert "Avoid bet" in data["analysis"]["recommendation"]
    
    def test_expected_value_zero_odds(self, test_client):
        """Test expected value calculation with zero odds."""
        response = test_client.post(
            "/api/v1/vegas/expected-value"
            "?model_probability=0.6"
            "&american_odds=0"
            "&bet_size=1.0"
        )
        
        assert response.status_code == 400
        assert "cannot be 0" in response.json()["detail"]
    
    def test_expected_value_invalid_parameters(self, test_client):
        """Test expected value calculation with invalid parameters."""
        # Invalid probability
        response = test_client.post(
            "/api/v1/vegas/expected-value"
            "?model_probability=1.5"
            "&american_odds=-120"
            "&bet_size=1.0"
        )
        assert response.status_code == 422
        
        # Invalid bet size
        response = test_client.post(
            "/api/v1/vegas/expected-value"
            "?model_probability=0.6"
            "&american_odds=-120"
            "&bet_size=0.001"
        )
        assert response.status_code == 422


class TestVegasEndpointIntegration:
    """Integration tests for Vegas endpoints."""
    
    @patch('src.api.routers.vegas.get_vegas_validator')
    def test_odds_probability_roundtrip(self, mock_get_validator, test_client):
        """Test that odds and probability conversions are consistent."""
        mock_validator = MagicMock()
        
        # Mock probability to odds
        mock_validator.probability_to_odds.return_value = -150
        mock_get_validator.return_value = mock_validator
        
        odds_response = test_client.get("/api/v1/vegas/odds-calculator?probability=0.6")
        assert odds_response.status_code == 200
        
        # Mock odds to probability 
        mock_validator.odds_to_probability.return_value = 0.6
        
        prob_response = test_client.get("/api/v1/vegas/probability-calculator?american_odds=-150")
        assert prob_response.status_code == 200
        
        # Should be consistent
        odds_data = odds_response.json()
        prob_data = prob_response.json()
        
        assert odds_data["american_odds"] == prob_data["american_odds"]
        assert abs(odds_data["probability"] - prob_data["implied_probability"]) < 0.01
    
    def test_endpoint_error_handling(self, test_client):
        """Test error handling across all endpoints."""
        # Test missing required parameters
        response = test_client.get("/api/v1/vegas/odds-calculator")
        assert response.status_code == 422
        
        response = test_client.get("/api/v1/vegas/probability-calculator") 
        assert response.status_code == 422
        
        response = test_client.post("/api/v1/vegas/expected-value")
        assert response.status_code == 422
        
        response = test_client.post("/api/v1/vegas/validate")
        assert response.status_code == 422