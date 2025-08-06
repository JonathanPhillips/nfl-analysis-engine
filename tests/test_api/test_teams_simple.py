"""Simple teams API tests."""

import pytest
from fastapi.testclient import TestClient


class TestTeamsAPIBasic:
    """Basic tests for teams API endpoints."""
    
    def test_get_teams_empty(self, test_client):
        """Test getting teams when database is empty."""
        response = test_client.get("/api/v1/teams/")
        
        assert response.status_code == 200
        data = response.json()
        assert data["teams"] == []
        assert data["total"] == 0
        assert data["limit"] == 32
        assert data["offset"] == 0
    
    def test_get_teams_with_sample_data(self, test_client, test_session):
        """Test getting teams with data in database."""
        from src.models.team import TeamModel
        
        # Create a simple team
        team = TeamModel(
            team_abbr="SF",
            team_name="San Francisco",
            team_nick="49ers",
            team_conf="NFC",
            team_division="West"
        )
        test_session.add(team)
        test_session.commit()
        test_session.refresh(team)
        
        response = test_client.get("/api/v1/teams/")
        
        assert response.status_code == 200
        data = response.json()
        assert len(data["teams"]) == 1
        assert data["total"] == 1
        
        team_data = data["teams"][0]
        assert team_data["team_abbr"] == "SF"
        assert team_data["team_name"] == "San Francisco"
        assert team_data["team_nick"] == "49ers"
    
    def test_get_team_by_abbr(self, test_client, test_session):
        """Test getting a specific team by abbreviation."""
        from src.models.team import TeamModel
        
        # Create a simple team
        team = TeamModel(
            team_abbr="KC",
            team_name="Kansas City",
            team_nick="Chiefs",
            team_conf="AFC",
            team_division="West"
        )
        test_session.add(team)
        test_session.commit()
        
        response = test_client.get("/api/v1/teams/KC")
        
        assert response.status_code == 200
        data = response.json()
        assert data["team_abbr"] == "KC"
        assert data["team_name"] == "Kansas City"
    
    def test_get_team_not_found(self, test_client):
        """Test getting a non-existent team."""
        response = test_client.get("/api/v1/teams/NOTFOUND")
        
        assert response.status_code == 404
        data = response.json()
        assert "not found" in data["detail"]
    
    def test_get_team_stats(self, test_client, test_session):
        """Test getting team statistics."""
        from src.models.team import TeamModel
        
        # Create a simple team
        team = TeamModel(
            team_abbr="DAL",
            team_name="Dallas",
            team_nick="Cowboys",
            team_conf="NFC",
            team_division="East"
        )
        test_session.add(team)
        test_session.commit()
        
        response = test_client.get("/api/v1/teams/DAL/stats")
        
        assert response.status_code == 200
        data = response.json()
        assert "team" in data
        assert data["team"]["team_abbr"] == "DAL"
        assert "message" in data  # Should have placeholder message