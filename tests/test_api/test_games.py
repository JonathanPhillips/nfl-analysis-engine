"""Tests for games API endpoints."""

import pytest
from fastapi.testclient import TestClient
from datetime import date


class TestGamesAPI:
    """Test games API endpoints."""
    
    def test_get_games_empty(self, test_client):
        """Test getting games when database is empty."""
        response = test_client.get("/api/v1/games/")
        
        assert response.status_code == 200
        data = response.json()
        assert data["games"] == []
        assert data["total"] == 0
        assert data["limit"] == 50
        assert data["offset"] == 0
    
    def test_get_games_with_data(self, test_client, sample_game):
        """Test getting games with data in database."""
        response = test_client.get("/api/v1/games/")
        
        assert response.status_code == 200
        data = response.json()
        assert len(data["games"]) == 1
        assert data["total"] == 1
        
        game = data["games"][0]
        assert game["game_id"] == "2023_01_SF_KC"
        assert game["season"] == 2023
        assert game["home_team"] == "KC"
        assert game["away_team"] == "SF"
        assert game["home_score"] == 24
        assert game["away_score"] == 21
    
    def test_get_games_pagination(self, test_client, test_session):
        """Test games pagination."""
        from src.models.game import Game
        
        # Create multiple games
        games_data = [
            {"game_id": "2023_01_SF_KC", "season": 2023, "week": 1, "home_team": "KC", "away_team": "SF"},
            {"game_id": "2023_01_DAL_GB", "season": 2023, "week": 1, "home_team": "GB", "away_team": "DAL"},
            {"game_id": "2023_02_SF_DAL", "season": 2023, "week": 2, "home_team": "DAL", "away_team": "SF"},
        ]
        
        for game_data in games_data:
            game = Game(**game_data)
            test_session.add(game)
        test_session.commit()
        
        # Test with limit
        response = test_client.get("/api/v1/games/?limit=2")
        assert response.status_code == 200
        data = response.json()
        assert len(data["games"]) == 2
        assert data["total"] == 3
        assert data["limit"] == 2
        
        # Test with offset
        response = test_client.get("/api/v1/games/?limit=2&offset=1")
        assert response.status_code == 200
        data = response.json()
        assert len(data["games"]) == 2
        assert data["offset"] == 1
    
    def test_get_games_season_filter(self, test_client, test_session):
        """Test filtering games by season."""
        from src.models.game import Game
        
        # Create games from different seasons
        game_2022 = Game(game_id="2022_01_SF_KC", season=2022, home_team="KC", away_team="SF")
        game_2023 = Game(game_id="2023_01_SF_KC", season=2023, home_team="KC", away_team="SF")
        
        test_session.add(game_2022)
        test_session.add(game_2023)
        test_session.commit()
        
        # Filter by season
        response = test_client.get("/api/v1/games/?season=2023")
        data = response.json()
        assert len(data["games"]) == 1
        assert data["games"][0]["season"] == 2023
    
    def test_get_games_season_type_filter(self, test_client, test_session):
        """Test filtering games by season type."""
        from src.models.game import Game
        
        # Create games with different season types
        regular_game = Game(
            game_id="2023_01_SF_KC", 
            season=2023, 
            season_type="REG", 
            home_team="KC", 
            away_team="SF"
        )
        playoff_game = Game(
            game_id="2023_18_SF_KC", 
            season=2023, 
            season_type="POST", 
            home_team="KC", 
            away_team="SF"
        )
        
        test_session.add(regular_game)
        test_session.add(playoff_game)
        test_session.commit()
        
        # Filter by season type
        response = test_client.get("/api/v1/games/?season_type=POST")
        data = response.json()
        assert len(data["games"]) == 1
        assert data["games"][0]["season_type"] == "POST"
    
    def test_get_games_week_filter(self, test_client, test_session):
        """Test filtering games by week."""
        from src.models.game import Game
        
        # Create games from different weeks
        week1_game = Game(game_id="2023_01_SF_KC", season=2023, week=1, home_team="KC", away_team="SF")
        week2_game = Game(game_id="2023_02_SF_DAL", season=2023, week=2, home_team="DAL", away_team="SF")
        
        test_session.add(week1_game)
        test_session.add(week2_game)
        test_session.commit()
        
        # Filter by week
        response = test_client.get("/api/v1/games/?week=1")
        data = response.json()
        assert len(data["games"]) == 1
        assert data["games"][0]["week"] == 1
    
    def test_get_games_team_filter(self, test_client, test_session):
        """Test filtering games by team."""
        from src.models.game import Game
        
        # Create games with SF as home and away
        sf_home = Game(game_id="2023_01_SF_KC", season=2023, home_team="SF", away_team="KC")
        sf_away = Game(game_id="2023_02_DAL_SF", season=2023, home_team="DAL", away_team="SF")
        no_sf = Game(game_id="2023_03_KC_DAL", season=2023, home_team="DAL", away_team="KC")
        
        test_session.add(sf_home)
        test_session.add(sf_away)
        test_session.add(no_sf)
        test_session.commit()
        
        # Filter by team (should get both home and away games)
        response = test_client.get("/api/v1/games/?team=SF")
        data = response.json()
        assert len(data["games"]) == 2
        
        # Verify both games include SF
        game_ids = [game["game_id"] for game in data["games"]]
        assert "2023_01_SF_KC" in game_ids
        assert "2023_02_DAL_SF" in game_ids
    
    def test_get_game_by_id(self, test_client, sample_game):
        """Test getting a specific game by ID."""
        response = test_client.get(f"/api/v1/games/{sample_game.game_id}")
        
        assert response.status_code == 200
        data = response.json()
        assert data["game_id"] == sample_game.game_id
        assert data["season"] == sample_game.season
        assert data["home_team"] == sample_game.home_team
        assert data["away_team"] == sample_game.away_team
        assert data["stadium"] == sample_game.stadium
        assert "created_at" in data
        assert "updated_at" in data
    
    def test_get_game_not_found(self, test_client):
        """Test getting a non-existent game."""
        response = test_client.get("/api/v1/games/2999_99_XX_YY")
        
        assert response.status_code == 404
        data = response.json()
        assert "not found" in data["detail"]
    
    def test_get_recent_games(self, test_client, test_session):
        """Test getting recent games."""
        from src.models.game import Game
        from datetime import date, timedelta
        
        # Create games with different dates
        today = date.today()
        yesterday = today - timedelta(days=1)
        week_ago = today - timedelta(days=7)
        future_date = today + timedelta(days=1)
        
        games_data = [
            {"game_id": "2023_01_SF_KC", "game_date": yesterday},
            {"game_id": "2023_02_DAL_GB", "game_date": week_ago},
            {"game_id": "2023_03_SF_DAL", "game_date": future_date},  # Should not appear
        ]
        
        for game_data in games_data:
            game = Game(
                season=2023,
                home_team="KC",
                away_team="SF",
                **game_data
            )
            test_session.add(game)
        test_session.commit()
        
        # Get recent games (should exclude future games)
        response = test_client.get("/api/v1/games/recent")
        assert response.status_code == 200
        data = response.json()
        
        # Should only get past games, ordered by date descending
        assert len(data["games"]) == 2
        assert data["games"][0]["game_date"] == yesterday.isoformat()  # Most recent first
        assert data["games"][1]["game_date"] == week_ago.isoformat()
        
        # Future game should not be included
        game_ids = [game["game_id"] for game in data["games"]]
        assert "2023_03_SF_DAL" not in game_ids
    
    def test_get_recent_games_with_limit(self, test_client, test_session):
        """Test getting recent games with custom limit."""
        from src.models.game import Game
        from datetime import date, timedelta
        
        # Create multiple past games
        today = date.today()
        for i in range(5):
            game_date = today - timedelta(days=i+1)
            game = Game(
                game_id=f"2023_0{i+1}_SF_KC",
                season=2023,
                game_date=game_date,
                home_team="KC",
                away_team="SF"
            )
            test_session.add(game)
        test_session.commit()
        
        # Get only 2 most recent
        response = test_client.get("/api/v1/games/recent?limit=2")
        data = response.json()
        assert len(data["games"]) == 2
        assert data["count"] == 2
    
    def test_games_query_parameters(self, test_client):
        """Test games endpoint query parameter validation."""
        # Test invalid limit
        response = test_client.get("/api/v1/games/?limit=0")
        assert response.status_code == 422
        
        response = test_client.get("/api/v1/games/?limit=1000")
        assert response.status_code == 422
        
        # Test invalid offset
        response = test_client.get("/api/v1/games/?offset=-1")
        assert response.status_code == 422
    
    def test_games_combined_filters(self, test_client, test_session):
        """Test combining multiple filters."""
        from src.models.game import Game
        
        # Create games with different attributes
        games_data = [
            {"game_id": "2023_01_SF_KC", "season": 2023, "week": 1, "season_type": "REG", "home_team": "KC", "away_team": "SF"},
            {"game_id": "2023_01_DAL_GB", "season": 2023, "week": 1, "season_type": "REG", "home_team": "GB", "away_team": "DAL"},
            {"game_id": "2023_02_SF_DAL", "season": 2023, "week": 2, "season_type": "REG", "home_team": "DAL", "away_team": "SF"},
            {"game_id": "2022_01_SF_KC", "season": 2022, "week": 1, "season_type": "REG", "home_team": "KC", "away_team": "SF"},
        ]
        
        for game_data in games_data:
            game = Game(**game_data)
            test_session.add(game)
        test_session.commit()
        
        # Filter by season and team
        response = test_client.get("/api/v1/games/?season=2023&team=SF")
        data = response.json()
        assert len(data["games"]) == 2  # 2023 games with SF
        
        # Filter by season, week, and team
        response = test_client.get("/api/v1/games/?season=2023&week=1&team=SF")
        data = response.json()
        assert len(data["games"]) == 1  # Only 2023 week 1 game with SF
        assert data["games"][0]["game_id"] == "2023_01_SF_KC"