"""Tests for teams API endpoints."""

import pytest
from fastapi.testclient import TestClient


class TestTeamsAPI:
    """Test teams API endpoints."""
    
    def test_get_teams_empty(self, test_client):
        """Test getting teams when database is empty."""
        response = test_client.get("/api/v1/teams/")
        
        assert response.status_code == 200
        data = response.json()
        assert data["teams"] == []
        assert data["total"] == 0
        assert data["limit"] == 32
        assert data["offset"] == 0
    
    def test_get_teams_with_data(self, test_client, sample_team):
        """Test getting teams with data in database."""
        response = test_client.get("/api/v1/teams/")
        
        assert response.status_code == 200
        data = response.json()
        assert len(data["teams"]) == 1
        assert data["total"] == 1
        
        team = data["teams"][0]
        assert team["team_abbr"] == "SF"
        assert team["team_name"] == "San Francisco 49ers"
        assert team["team_nick"] == "49ers"
        assert team["active"] is True
    
    def test_get_teams_pagination(self, test_client, test_session):
        """Test teams pagination."""
        # Create multiple teams
        from src.models.team import Team
        teams_data = [
            {"team_abbr": "SF", "team_name": "San Francisco 49ers"},
            {"team_abbr": "KC", "team_name": "Kansas City Chiefs"},
            {"team_abbr": "DAL", "team_name": "Dallas Cowboys"},
        ]
        
        for team_data in teams_data:
            team = Team(**team_data)
            test_session.add(team)
        test_session.commit()
        
        # Test with limit
        response = test_client.get("/api/v1/teams/?limit=2")
        assert response.status_code == 200
        data = response.json()
        assert len(data["teams"]) == 2
        assert data["total"] == 3
        assert data["limit"] == 2
        
        # Test with offset
        response = test_client.get("/api/v1/teams/?limit=2&offset=1")
        assert response.status_code == 200
        data = response.json()
        assert len(data["teams"]) == 2
        assert data["offset"] == 1
    
    def test_get_teams_active_filter(self, test_client, test_session):
        """Test filtering teams by active status."""
        from src.models.team import Team
        
        # Create active and inactive teams
        active_team = Team(team_abbr="SF", team_name="San Francisco", active=True)
        inactive_team = Team(team_abbr="OAK", team_name="Oakland", active=False)
        
        test_session.add(active_team)
        test_session.add(inactive_team)
        test_session.commit()
        
        # Test active only (default)
        response = test_client.get("/api/v1/teams/")
        data = response.json()
        assert len(data["teams"]) == 1
        assert data["teams"][0]["team_abbr"] == "SF"
        
        # Test including inactive
        response = test_client.get("/api/v1/teams/?active_only=false")
        data = response.json()
        assert len(data["teams"]) == 2
    
    def test_get_team_by_abbr(self, test_client, sample_team):
        """Test getting a specific team by abbreviation."""
        response = test_client.get("/api/v1/teams/SF")
        
        assert response.status_code == 200
        data = response.json()
        assert data["team_abbr"] == "SF"
        assert data["team_name"] == "San Francisco 49ers"
        assert data["id"] == sample_team.id
    
    def test_get_team_not_found(self, test_client):
        """Test getting a non-existent team."""
        response = test_client.get("/api/v1/teams/NOTFOUND")
        
        assert response.status_code == 404
        data = response.json()
        assert "not found" in data["detail"]
    
    def test_create_team(self, test_client, sample_team_data):
        """Test creating a new team."""
        response = test_client.post("/api/v1/teams/", json=sample_team_data)
        
        assert response.status_code == 201
        data = response.json()
        assert data["team_abbr"] == sample_team_data["team_abbr"]
        assert data["team_name"] == sample_team_data["team_name"]
        assert "id" in data
        assert "created_at" in data
    
    def test_create_team_duplicate(self, test_client, sample_team, sample_team_data):
        """Test creating a team that already exists."""
        response = test_client.post("/api/v1/teams/", json=sample_team_data)
        
        assert response.status_code == 409
        data = response.json()
        assert "already exists" in data["detail"]
    
    def test_create_team_invalid_data(self, test_client):
        """Test creating a team with invalid data."""
        invalid_data = {
            "team_abbr": "invalid_abbr",  # Too long
            "team_name": "",  # Empty
            "team_color": "invalid_color"  # Invalid hex format
        }
        
        response = test_client.post("/api/v1/teams/", json=invalid_data)
        
        assert response.status_code == 422  # Validation error
    
    def test_update_team(self, test_client, sample_team):
        """Test updating an existing team."""
        update_data = {
            "team_name": "Updated Team Name",
            "team_color": "#FF0000"
        }
        
        response = test_client.put(f"/api/v1/teams/{sample_team.team_abbr}", json=update_data)
        
        assert response.status_code == 200
        data = response.json()
        assert data["team_name"] == update_data["team_name"]
        assert data["team_color"] == update_data["team_color"]
        assert data["team_abbr"] == sample_team.team_abbr  # Unchanged
    
    def test_update_team_not_found(self, test_client):
        """Test updating a non-existent team."""
        update_data = {"team_name": "Updated Name"}
        
        response = test_client.put("/api/v1/teams/NOTFOUND", json=update_data)
        
        assert response.status_code == 404
    
    def test_delete_team(self, test_client, sample_team):
        """Test deleting (deactivating) a team."""
        response = test_client.delete(f"/api/v1/teams/{sample_team.team_abbr}")
        
        assert response.status_code == 204
        
        # Verify team is deactivated, not actually deleted
        response = test_client.get(f"/api/v1/teams/{sample_team.team_abbr}")
        assert response.status_code == 200
        data = response.json()
        assert data["active"] is False
    
    def test_delete_team_not_found(self, test_client):
        """Test deleting a non-existent team."""
        response = test_client.delete("/api/v1/teams/NOTFOUND")
        
        assert response.status_code == 404
    
    def test_get_team_stats(self, test_client, sample_team):
        """Test getting team statistics."""
        response = test_client.get(f"/api/v1/teams/{sample_team.team_abbr}/stats")
        
        assert response.status_code == 200
        data = response.json()
        assert "team" in data
        assert data["team"]["team_abbr"] == sample_team.team_abbr
        assert "games_played" in data
        assert "message" in data  # Placeholder until stats are implemented
    
    def test_get_team_stats_with_season(self, test_client, sample_team):
        """Test getting team statistics for a specific season."""
        response = test_client.get(f"/api/v1/teams/{sample_team.team_abbr}/stats?season=2023")
        
        assert response.status_code == 200
        data = response.json()
        assert data["season"] == 2023
    
    def test_get_team_stats_not_found(self, test_client):
        """Test getting stats for a non-existent team."""
        response = test_client.get("/api/v1/teams/NOTFOUND/stats")
        
        assert response.status_code == 404
    
    def test_teams_query_parameters(self, test_client):
        """Test teams endpoint query parameter validation."""
        # Test invalid limit
        response = test_client.get("/api/v1/teams/?limit=0")
        assert response.status_code == 422
        
        response = test_client.get("/api/v1/teams/?limit=200")
        assert response.status_code == 422
        
        # Test invalid offset
        response = test_client.get("/api/v1/teams/?offset=-1")
        assert response.status_code == 422