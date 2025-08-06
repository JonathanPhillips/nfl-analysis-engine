"""Tests for players API endpoints."""

import pytest
from fastapi.testclient import TestClient


class TestPlayersAPI:
    """Test players API endpoints."""
    
    def test_get_players_empty(self, test_client):
        """Test getting players when database is empty."""
        response = test_client.get("/api/v1/players/")
        
        assert response.status_code == 200
        data = response.json()
        assert data["players"] == []
        assert data["total"] == 0
        assert data["limit"] == 50
        assert data["offset"] == 0
    
    def test_get_players_with_data(self, test_client, sample_player):
        """Test getting players with data in database."""
        response = test_client.get("/api/v1/players/")
        
        assert response.status_code == 200
        data = response.json()
        assert len(data["players"]) == 1
        assert data["total"] == 1
        
        player = data["players"][0]
        assert player["player_id"] == "00-0012345"
        assert player["full_name"] == "John Doe"
        assert player["team_abbr"] == "SF"
        assert player["position"] == "QB"
    
    def test_get_players_pagination(self, test_client, test_session):
        """Test players pagination."""
        from src.models.player import Player
        
        # Create multiple players
        players_data = [
            {"player_id": "00-0001", "full_name": "Player 1", "position": "QB"},
            {"player_id": "00-0002", "full_name": "Player 2", "position": "RB"},
            {"player_id": "00-0003", "full_name": "Player 3", "position": "WR"},
        ]
        
        for player_data in players_data:
            player = Player(**player_data)
            test_session.add(player)
        test_session.commit()
        
        # Test with limit
        response = test_client.get("/api/v1/players/?limit=2")
        assert response.status_code == 200
        data = response.json()
        assert len(data["players"]) == 2
        assert data["total"] == 3
        assert data["limit"] == 2
        
        # Test with offset
        response = test_client.get("/api/v1/players/?limit=2&offset=1")
        assert response.status_code == 200
        data = response.json()
        assert len(data["players"]) == 2
        assert data["offset"] == 1
    
    def test_get_players_team_filter(self, test_client, test_session):
        """Test filtering players by team."""
        from src.models.player import Player
        
        # Create players from different teams
        sf_player = Player(player_id="00-0001", full_name="SF Player", team_abbr="SF")
        kc_player = Player(player_id="00-0002", full_name="KC Player", team_abbr="KC")
        
        test_session.add(sf_player)
        test_session.add(kc_player)
        test_session.commit()
        
        # Filter by team
        response = test_client.get("/api/v1/players/?team_abbr=SF")
        data = response.json()
        assert len(data["players"]) == 1
        assert data["players"][0]["team_abbr"] == "SF"
    
    def test_get_players_position_filter(self, test_client, test_session):
        """Test filtering players by position."""
        from src.models.player import Player
        
        # Create players with different positions
        qb_player = Player(player_id="00-0001", full_name="QB Player", position="QB")
        rb_player = Player(player_id="00-0002", full_name="RB Player", position="RB")
        
        test_session.add(qb_player)
        test_session.add(rb_player)
        test_session.commit()
        
        # Filter by position
        response = test_client.get("/api/v1/players/?position=QB")
        data = response.json()
        assert len(data["players"]) == 1
        assert data["players"][0]["position"] == "QB"
    
    def test_get_players_active_filter(self, test_client, test_session):
        """Test filtering players by active status."""
        from src.models.player import Player
        
        # Create active and inactive players
        active_player = Player(
            player_id="00-0001", 
            full_name="Active Player", 
            status="active"
        )
        inactive_player = Player(
            player_id="00-0002", 
            full_name="Inactive Player", 
            status="inactive"
        )
        
        test_session.add(active_player)
        test_session.add(inactive_player)
        test_session.commit()
        
        # Test active only (default)
        response = test_client.get("/api/v1/players/")
        data = response.json()
        assert len(data["players"]) == 1
        assert data["players"][0]["status"] == "active"
        
        # Test including inactive
        response = test_client.get("/api/v1/players/?active_only=false")
        data = response.json()
        assert len(data["players"]) == 2
    
    def test_get_player_by_id(self, test_client, sample_player):
        """Test getting a specific player by ID."""
        response = test_client.get(f"/api/v1/players/{sample_player.player_id}")
        
        assert response.status_code == 200
        data = response.json()
        assert data["player_id"] == sample_player.player_id
        assert data["full_name"] == sample_player.full_name
        assert data["team_abbr"] == sample_player.team_abbr
        assert data["position"] == sample_player.position
        assert "created_at" in data
        assert "updated_at" in data
    
    def test_get_player_not_found(self, test_client):
        """Test getting a non-existent player."""
        response = test_client.get("/api/v1/players/99-9999999")
        
        assert response.status_code == 404
        data = response.json()
        assert "not found" in data["detail"]
    
    def test_get_player_stats(self, test_client, sample_player):
        """Test getting player statistics."""
        response = test_client.get(f"/api/v1/players/{sample_player.player_id}/stats")
        
        assert response.status_code == 200
        data = response.json()
        assert "player" in data
        assert data["player"]["player_id"] == sample_player.player_id
        assert "stats" in data
        assert "message" in data  # Placeholder until stats are implemented
    
    def test_get_player_stats_with_season(self, test_client, sample_player):
        """Test getting player statistics for a specific season."""
        response = test_client.get(f"/api/v1/players/{sample_player.player_id}/stats?season=2023")
        
        assert response.status_code == 200
        data = response.json()
        assert data["season"] == 2023
    
    def test_get_player_stats_not_found(self, test_client):
        """Test getting stats for a non-existent player."""
        response = test_client.get("/api/v1/players/99-9999999/stats")
        
        assert response.status_code == 404
    
    def test_players_query_parameters(self, test_client):
        """Test players endpoint query parameter validation."""
        # Test invalid limit
        response = test_client.get("/api/v1/players/?limit=0")
        assert response.status_code == 422
        
        response = test_client.get("/api/v1/players/?limit=2000")
        assert response.status_code == 422
        
        # Test invalid offset
        response = test_client.get("/api/v1/players/?offset=-1")
        assert response.status_code == 422
    
    def test_players_combined_filters(self, test_client, test_session):
        """Test combining multiple filters."""
        from src.models.player import Player
        
        # Create players with different attributes
        players_data = [
            {"player_id": "00-0001", "full_name": "QB1", "team_abbr": "SF", "position": "QB", "status": "active"},
            {"player_id": "00-0002", "full_name": "QB2", "team_abbr": "KC", "position": "QB", "status": "active"},
            {"player_id": "00-0003", "full_name": "RB1", "team_abbr": "SF", "position": "RB", "status": "active"},
            {"player_id": "00-0004", "full_name": "QB3", "team_abbr": "SF", "position": "QB", "status": "inactive"},
        ]
        
        for player_data in players_data:
            player = Player(**player_data)
            test_session.add(player)
        test_session.commit()
        
        # Filter by team and position
        response = test_client.get("/api/v1/players/?team_abbr=SF&position=QB")
        data = response.json()
        assert len(data["players"]) == 1  # Only active SF QB
        assert data["players"][0]["full_name"] == "QB1"
        
        # Filter by team, position, and include inactive
        response = test_client.get("/api/v1/players/?team_abbr=SF&position=QB&active_only=false")
        data = response.json()
        assert len(data["players"]) == 2  # Both SF QBs