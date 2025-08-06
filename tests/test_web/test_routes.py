"""Tests for web interface routes."""

import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock

from src.api.main import create_app


@pytest.fixture
def web_client(test_session):
    """Create test client with database session override."""
    from src.api.dependencies import get_db_session
    
    def override_get_db_session():
        """Override database session dependency."""
        try:
            yield test_session
        except Exception:
            test_session.rollback()
            raise
    
    app = create_app()
    app.dependency_overrides[get_db_session] = override_get_db_session
    
    with TestClient(app) as client:
        yield client


class TestWebRoutes:
    """Test web interface routes."""
    
    def test_home_page_loads(self, web_client):
        """Test that home page loads successfully."""
        response = web_client.get("/web/")
        
        assert response.status_code == 200
        assert "NFL Analysis Engine" in response.text
        assert "Dashboard" in response.text
    
    def test_teams_page_loads(self, web_client):
        """Test that teams page loads successfully."""
        response = web_client.get("/web/teams")
        
        assert response.status_code == 200
        assert "NFL Teams" in response.text
    
    def test_games_page_loads(self, web_client):
        """Test that games page loads successfully."""
        response = web_client.get("/web/games")
        
        assert response.status_code == 200
        assert "NFL Games" in response.text
    
    def test_predictions_page_loads(self, web_client):
        """Test that predictions page loads successfully."""
        response = web_client.get("/web/predictions")
        
        assert response.status_code == 200
        assert "Game Predictions" in response.text
    
    def test_predict_form_loads(self, web_client, sample_team):
        """Test that predict form loads successfully."""
        response = web_client.get("/web/predict")
        
        assert response.status_code == 200
        assert "Predict Game Outcome" in response.text
        assert "Away Team" in response.text
        assert "Home Team" in response.text
    
    def test_value_bets_page_loads(self, web_client):
        """Test that value bets page loads successfully."""
        response = web_client.get("/web/value-bets")
        
        assert response.status_code == 200
        assert "Value Betting Opportunities" in response.text
    
    def test_model_status_page_loads(self, web_client):
        """Test that model status page loads successfully."""
        response = web_client.get("/web/model")
        
        assert response.status_code == 200
        assert "Model Status" in response.text
        assert "Train Model" in response.text
    
    def test_root_redirects_to_web(self, web_client):
        """Test that root URL redirects to web interface."""
        response = web_client.get("/", follow_redirects=False)
        
        assert response.status_code == 307
        assert response.headers["location"] == "/web/"
    
    def test_predict_form_submission_untrained_model(self, web_client, sample_team):
        """Test predict form submission with untrained model."""
        response = web_client.post("/web/predict", data={
            "home_team": "SF",
            "away_team": "KC", 
            "game_date": "2024-01-01",
            "season": "2024"
        })
        
        assert response.status_code == 200
        assert "Model not trained" in response.text