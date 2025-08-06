"""Tests for plays API endpoints."""

import pytest
from fastapi.testclient import TestClient


class TestPlaysAPI:
    """Test plays API endpoints."""
    
    def test_get_plays_empty(self, test_client):
        """Test getting plays when database is empty."""
        response = test_client.get("/api/v1/plays/")
        
        assert response.status_code == 200
        data = response.json()
        assert data["plays"] == []
        assert data["total"] == 0
        assert data["limit"] == 100
        assert data["offset"] == 0
    
    def test_get_plays_with_data(self, test_client, sample_play):
        """Test getting plays with data in database."""
        response = test_client.get("/api/v1/plays/")
        
        assert response.status_code == 200
        data = response.json()
        assert len(data["plays"]) == 1
        assert data["total"] == 1
        
        play = data["plays"][0]
        assert play["play_id"] == "2023_01_SF_KC_1"
        assert play["game_id"] == "2023_01_SF_KC"
        assert play["posteam"] == "SF"
        assert play["defteam"] == "KC"
        assert play["play_type"] == "pass"
    
    def test_get_plays_pagination(self, test_client, test_session):
        """Test plays pagination."""
        from src.models.play import Play
        
        # Create multiple plays
        plays_data = [
            {"play_id": "2023_01_SF_KC_1", "game_id": "2023_01_SF_KC", "season": 2023, "posteam": "SF"},
            {"play_id": "2023_01_SF_KC_2", "game_id": "2023_01_SF_KC", "season": 2023, "posteam": "SF"},
            {"play_id": "2023_01_SF_KC_3", "game_id": "2023_01_SF_KC", "season": 2023, "posteam": "KC"},
        ]
        
        for play_data in plays_data:
            play = Play(**play_data)
            test_session.add(play)
        test_session.commit()
        
        # Test with limit
        response = test_client.get("/api/v1/plays/?limit=2")
        assert response.status_code == 200
        data = response.json()
        assert len(data["plays"]) == 2
        assert data["total"] == 3
        assert data["limit"] == 2
        
        # Test with offset
        response = test_client.get("/api/v1/plays/?limit=2&offset=1")
        assert response.status_code == 200
        data = response.json()
        assert len(data["plays"]) == 2
        assert data["offset"] == 1
    
    def test_get_plays_game_filter(self, test_client, test_session):
        """Test filtering plays by game ID."""
        from src.models.play import Play
        
        # Create plays from different games
        game1_play = Play(play_id="2023_01_SF_KC_1", game_id="2023_01_SF_KC", season=2023, posteam="SF")
        game2_play = Play(play_id="2023_02_DAL_GB_1", game_id="2023_02_DAL_GB", season=2023, posteam="DAL")
        
        test_session.add(game1_play)
        test_session.add(game2_play)
        test_session.commit()
        
        # Filter by game ID
        response = test_client.get("/api/v1/plays/?game_id=2023_01_SF_KC")
        data = response.json()
        assert len(data["plays"]) == 1
        assert data["plays"][0]["game_id"] == "2023_01_SF_KC"
    
    def test_get_plays_season_filter(self, test_client, test_session):
        """Test filtering plays by season."""
        from src.models.play import Play
        
        # Create plays from different seasons
        play_2022 = Play(play_id="2022_01_SF_KC_1", game_id="2022_01_SF_KC", season=2022, posteam="SF")
        play_2023 = Play(play_id="2023_01_SF_KC_1", game_id="2023_01_SF_KC", season=2023, posteam="SF")
        
        test_session.add(play_2022)
        test_session.add(play_2023)
        test_session.commit()
        
        # Filter by season
        response = test_client.get("/api/v1/plays/?season=2023")
        data = response.json()
        assert len(data["plays"]) == 1
        assert data["plays"][0]["season"] == 2023
    
    def test_get_plays_play_type_filter(self, test_client, test_session):
        """Test filtering plays by play type."""
        from src.models.play import Play
        
        # Create plays with different types
        pass_play = Play(
            play_id="2023_01_SF_KC_1", 
            game_id="2023_01_SF_KC", 
            season=2023, 
            posteam="SF",
            play_type="pass"
        )
        run_play = Play(
            play_id="2023_01_SF_KC_2", 
            game_id="2023_01_SF_KC", 
            season=2023, 
            posteam="SF",
            play_type="run"
        )
        
        test_session.add(pass_play)
        test_session.add(run_play)
        test_session.commit()
        
        # Filter by play type
        response = test_client.get("/api/v1/plays/?play_type=pass")
        data = response.json()
        assert len(data["plays"]) == 1
        assert data["plays"][0]["play_type"] == "pass"
    
    def test_get_plays_posteam_filter(self, test_client, test_session):
        """Test filtering plays by possession team."""
        from src.models.play import Play
        
        # Create plays with different possession teams
        sf_play = Play(play_id="2023_01_SF_KC_1", game_id="2023_01_SF_KC", season=2023, posteam="SF")
        kc_play = Play(play_id="2023_01_SF_KC_2", game_id="2023_01_SF_KC", season=2023, posteam="KC")
        
        test_session.add(sf_play)
        test_session.add(kc_play)
        test_session.commit()
        
        # Filter by possession team
        response = test_client.get("/api/v1/plays/?posteam=SF")
        data = response.json()
        assert len(data["plays"]) == 1
        assert data["plays"][0]["posteam"] == "SF"
    
    def test_get_play_by_id(self, test_client, sample_play):
        """Test getting a specific play by ID."""
        response = test_client.get(f"/api/v1/plays/{sample_play.play_id}")
        
        assert response.status_code == 200
        data = response.json()
        assert data["play_id"] == sample_play.play_id
        assert data["game_id"] == sample_play.game_id
        assert data["desc"] == sample_play.desc
        assert data["posteam"] == sample_play.posteam
        assert data["play_type"] == sample_play.play_type
        assert data["ep"] == sample_play.ep
        assert data["epa"] == sample_play.epa
        assert "created_at" in data
        assert "updated_at" in data
    
    def test_get_play_not_found(self, test_client):
        """Test getting a non-existent play."""
        response = test_client.get("/api/v1/plays/2999_99_XX_YY_999")
        
        assert response.status_code == 404
        data = response.json()
        assert "not found" in data["detail"]
    
    def test_get_game_plays(self, test_client, test_session):
        """Test getting all plays for a specific game."""
        from src.models.play import Play
        
        game_id = "2023_01_SF_KC"
        
        # Create multiple plays for the game
        plays_data = [
            {
                "play_id": f"{game_id}_1",
                "game_id": game_id,
                "season": 2023,
                "posteam": "SF",
                "play_type": "pass",
                "desc": "Pass play 1",
                "qtr": 1,
                "down": 1,
                "ydstogo": 10,
                "yards_gained": 8
            },
            {
                "play_id": f"{game_id}_2",
                "game_id": game_id,
                "season": 2023,
                "posteam": "SF",
                "play_type": "run",
                "desc": "Run play 2",
                "qtr": 1,
                "down": 2,
                "ydstogo": 2,
                "yards_gained": 3
            }
        ]
        
        for play_data in plays_data:
            play = Play(**play_data)
            test_session.add(play)
        test_session.commit()
        
        # Get all plays for the game
        response = test_client.get(f"/api/v1/plays/game/{game_id}")
        assert response.status_code == 200
        data = response.json()
        
        assert data["game_id"] == game_id
        assert len(data["plays"]) == 2
        assert data["total_plays"] == 2
        
        # Verify play details
        plays = data["plays"]
        assert plays[0]["play_type"] == "pass"
        assert plays[1]["play_type"] == "run"
        
        # Should include key play information
        for play in plays:
            assert "play_id" in play
            assert "desc" in play
            assert "qtr" in play
            assert "down" in play
            assert "posteam" in play
            assert "yards_gained" in play
    
    def test_get_game_plays_not_found(self, test_client):
        """Test getting plays for a non-existent game."""
        response = test_client.get("/api/v1/plays/game/2999_99_XX_YY")
        
        assert response.status_code == 404
        data = response.json()
        assert "No plays found" in data["detail"]
    
    def test_get_game_plays_with_limit(self, test_client, test_session):
        """Test getting game plays with custom limit."""
        from src.models.play import Play
        
        game_id = "2023_01_SF_KC"
        
        # Create many plays for the game
        for i in range(10):
            play = Play(
                play_id=f"{game_id}_{i+1}",
                game_id=game_id,
                season=2023,
                posteam="SF"
            )
            test_session.add(play)
        test_session.commit()
        
        # Get limited number of plays
        response = test_client.get(f"/api/v1/plays/game/{game_id}?limit=5")
        data = response.json()
        assert len(data["plays"]) == 5
        assert data["total_plays"] == 5
    
    def test_plays_query_parameters(self, test_client):
        """Test plays endpoint query parameter validation."""
        # Test invalid limit
        response = test_client.get("/api/v1/plays/?limit=0")
        assert response.status_code == 422
        
        response = test_client.get("/api/v1/plays/?limit=2000")
        assert response.status_code == 422
        
        # Test invalid offset
        response = test_client.get("/api/v1/plays/?offset=-1")
        assert response.status_code == 422
    
    def test_plays_combined_filters(self, test_client, test_session):
        """Test combining multiple filters."""
        from src.models.play import Play
        
        # Create plays with different attributes
        plays_data = [
            {"play_id": "2023_01_SF_KC_1", "game_id": "2023_01_SF_KC", "season": 2023, "posteam": "SF", "play_type": "pass"},
            {"play_id": "2023_01_SF_KC_2", "game_id": "2023_01_SF_KC", "season": 2023, "posteam": "KC", "play_type": "pass"},
            {"play_id": "2023_01_SF_KC_3", "game_id": "2023_01_SF_KC", "season": 2023, "posteam": "SF", "play_type": "run"},
            {"play_id": "2023_02_SF_DAL_1", "game_id": "2023_02_SF_DAL", "season": 2023, "posteam": "SF", "play_type": "pass"},
        ]
        
        for play_data in plays_data:
            play = Play(**play_data)
            test_session.add(play)
        test_session.commit()
        
        # Filter by game and play type
        response = test_client.get("/api/v1/plays/?game_id=2023_01_SF_KC&play_type=pass")
        data = response.json()
        assert len(data["plays"]) == 2  # Both pass plays from that game
        
        # Filter by game, play type, and team
        response = test_client.get("/api/v1/plays/?game_id=2023_01_SF_KC&play_type=pass&posteam=SF")
        data = response.json()
        assert len(data["plays"]) == 1  # Only SF pass play from that game
        assert data["plays"][0]["play_id"] == "2023_01_SF_KC_1"