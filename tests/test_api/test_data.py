"""Tests for data management API endpoints."""

import pytest
from unittest.mock import Mock, patch
from fastapi.testclient import TestClient


class TestDataAPI:
    """Test data management API endpoints."""
    
    def test_get_data_status_empty_db(self, test_client, test_session):
        """Test getting data status with empty database."""
        response = test_client.get("/api/v1/data/status")
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"
        assert "database_counts" in data
        assert data["database_counts"]["teams"] == 0
        assert data["database_counts"]["players"] == 0
        assert data["database_counts"]["games"] == 0
        assert data["database_counts"]["plays"] == 0
    
    def test_get_data_status_with_data(self, test_client, sample_team, sample_player, sample_game, sample_play):
        """Test getting data status with data in database."""
        response = test_client.get("/api/v1/data/status")
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"
        assert data["database_counts"]["teams"] == 1
        assert data["database_counts"]["players"] == 1
        assert data["database_counts"]["games"] == 1
        assert data["database_counts"]["plays"] == 1
    
    @patch('src.api.routers.data.get_data_loader')
    def test_load_teams_data_success(self, mock_get_loader, test_client):
        """Test successful teams data loading."""
        # Mock data loader and result
        mock_loader = Mock()
        mock_result = Mock()
        mock_result.records_loaded = 32
        mock_result.records_updated = 0
        mock_result.records_skipped = 0
        mock_result.duration.total_seconds.return_value = 5.2
        mock_result.errors = []
        
        mock_loader.load_teams.return_value = mock_result
        mock_get_loader.return_value = mock_loader
        
        response = test_client.post("/api/v1/data/load/teams")
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"
        assert "Loaded 32 teams" in data["message"]
        assert data["result"]["records_loaded"] == 32
        assert data["result"]["duration_seconds"] == 5.2
        
        # Verify loader was called correctly
        mock_loader.load_teams.assert_called_once_with(force_refresh=False)
    
    @patch('src.api.routers.data.get_data_loader')
    def test_load_teams_data_with_force_refresh(self, mock_get_loader, test_client):
        """Test teams data loading with force refresh."""
        mock_loader = Mock()
        mock_result = Mock()
        mock_result.records_loaded = 32
        mock_result.records_updated = 5
        mock_result.records_skipped = 0
        mock_result.duration.total_seconds.return_value = 8.1
        mock_result.errors = []
        
        mock_loader.load_teams.return_value = mock_result
        mock_get_loader.return_value = mock_loader
        
        response = test_client.post("/api/v1/data/load/teams?force_refresh=true")
        
        assert response.status_code == 200
        mock_loader.load_teams.assert_called_once_with(force_refresh=True)
    
    @patch('src.api.routers.data.get_data_loader')
    def test_load_players_data_success(self, mock_get_loader, test_client):
        """Test successful players data loading."""
        mock_loader = Mock()
        mock_result = Mock()
        mock_result.records_loaded = 1500
        mock_result.records_updated = 50
        mock_result.records_skipped = 10
        mock_result.duration.total_seconds.return_value = 30.5
        mock_result.errors = []
        
        mock_loader.load_players.return_value = mock_result
        mock_get_loader.return_value = mock_loader
        
        response = test_client.post("/api/v1/data/load/players")
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"
        assert "Loaded 1500 players" in data["message"]
        
        # Verify loader was called with default parameters
        mock_loader.load_players.assert_called_once_with(seasons=None, force_refresh=False)
    
    @patch('src.api.routers.data.get_data_loader')
    def test_load_players_data_with_seasons(self, mock_get_loader, test_client):
        """Test players data loading with specific seasons."""
        mock_loader = Mock()
        mock_result = Mock()
        mock_result.records_loaded = 800
        mock_result.records_updated = 0
        mock_result.records_skipped = 0
        mock_result.duration.total_seconds.return_value = 15.2
        mock_result.errors = []
        
        mock_loader.load_players.return_value = mock_result
        mock_get_loader.return_value = mock_loader
        
        response = test_client.post("/api/v1/data/load/players?seasons=2022,2023")
        
        assert response.status_code == 200
        mock_loader.load_players.assert_called_once_with(seasons=[2022, 2023], force_refresh=False)
    
    def test_load_players_data_invalid_seasons(self, test_client):
        """Test players data loading with invalid seasons parameter."""
        response = test_client.post("/api/v1/data/load/players?seasons=invalid,data")
        
        assert response.status_code == 400
        data = response.json()
        assert "Invalid seasons format" in data["detail"]
    
    @patch('src.api.routers.data.get_data_loader')
    def test_load_games_data_success(self, mock_get_loader, test_client):
        """Test successful games data loading."""
        mock_loader = Mock()
        mock_result = Mock()
        mock_result.records_loaded = 272
        mock_result.records_updated = 12
        mock_result.records_skipped = 5
        mock_result.duration.total_seconds.return_value = 45.8
        mock_result.errors = ["Minor error 1"]
        
        mock_loader.load_games.return_value = mock_result
        mock_get_loader.return_value = mock_loader
        
        response = test_client.post("/api/v1/data/load/games?seasons=2023")
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"
        assert data["result"]["errors"] == ["Minor error 1"]
        
        mock_loader.load_games.assert_called_once_with(seasons=[2023], force_refresh=False)
    
    @patch('src.api.routers.data.DataValidationPipeline')
    def test_validate_data_teams(self, mock_pipeline_class, test_client, sample_team):
        """Test data validation for teams."""
        # Mock validation pipeline
        mock_pipeline = Mock()
        mock_result = Mock()
        mock_result.to_summary.return_value = {
            "total_records": 1,
            "valid_records": 1,
            "validation_rate": 100.0,
            "total_issues": 0
        }
        mock_pipeline.validate_data.return_value = mock_result
        mock_pipeline_class.return_value = mock_pipeline
        
        response = test_client.post("/api/v1/data/validate?data_type=teams")
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"
        assert data["data_type"] == "teams"
        assert data["records_validated"] == 1
        assert data["validation_result"]["total_records"] == 1
    
    def test_validate_data_invalid_type(self, test_client):
        """Test data validation with invalid data type."""
        response = test_client.post("/api/v1/data/validate?data_type=invalid")
        
        assert response.status_code == 400
        data = response.json()
        assert "Invalid data type" in data["detail"]
    
    @patch('src.api.routers.data.DataValidationPipeline')
    def test_validate_data_no_data(self, mock_pipeline_class, test_client):
        """Test data validation when no data exists."""
        response = test_client.post("/api/v1/data/validate?data_type=teams")
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"
        assert "No teams data found" in data["message"]
        assert data["validation_result"] is None
    
    @patch('src.api.routers.data.DataValidationPipeline')
    def test_validate_data_strict_mode(self, mock_pipeline_class, test_client, sample_team):
        """Test data validation in strict mode."""
        mock_pipeline = Mock()
        mock_result = Mock()
        mock_result.to_summary.return_value = {"total_records": 1}
        mock_pipeline.validate_data.return_value = mock_result
        mock_pipeline_class.return_value = mock_pipeline
        
        response = test_client.post("/api/v1/data/validate?data_type=teams&strict_mode=true")
        
        assert response.status_code == 200
        
        # Verify pipeline was configured with strict mode
        mock_pipeline_class.assert_called_once()
        config_arg = mock_pipeline_class.call_args[0][0]
        assert config_arg.strict_validation is True
    
    @patch('src.api.routers.data.get_data_loader')
    def test_get_cache_info(self, mock_get_loader, test_client):
        """Test getting cache information."""
        mock_loader = Mock()
        mock_client = Mock()
        mock_client.get_cache_info.return_value = {
            "cache_enabled": True,
            "hits": 150,
            "misses": 25,
            "maxsize": 128,
            "currsize": 45
        }
        mock_loader.client = mock_client
        mock_get_loader.return_value = mock_loader
        
        response = test_client.get("/api/v1/data/cache/info")
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"
        assert data["cache_enabled"] is True
        assert data["cache_stats"]["hits"] == 150
    
    @patch('src.api.routers.data.get_data_loader')
    def test_get_cache_info_disabled(self, mock_get_loader, test_client):
        """Test getting cache info when caching is disabled."""
        mock_loader = Mock()
        mock_client = Mock()
        mock_client.get_cache_info.return_value = {"cache_enabled": False}
        mock_loader.client = mock_client
        mock_get_loader.return_value = mock_loader
        
        response = test_client.get("/api/v1/data/cache/info")
        
        assert response.status_code == 200
        data = response.json()
        assert data["cache_enabled"] is False
        assert data["cache_stats"] is None
    
    @patch('src.api.routers.data.get_data_loader')
    def test_clear_cache(self, mock_get_loader, test_client):
        """Test clearing the cache."""
        mock_loader = Mock()
        mock_client = Mock()
        mock_loader.client = mock_client
        mock_get_loader.return_value = mock_loader
        
        response = test_client.delete("/api/v1/data/cache")
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"
        assert "Cache cleared successfully" in data["message"]
        
        mock_client.clear_cache.assert_called_once()
    
    @patch('src.api.routers.data.get_data_loader')
    def test_data_loading_error_handling(self, mock_get_loader, test_client):
        """Test error handling in data loading endpoints."""
        mock_loader = Mock()
        mock_loader.load_teams.side_effect = Exception("Data loading failed")
        mock_get_loader.return_value = mock_loader
        
        response = test_client.post("/api/v1/data/load/teams")
        
        assert response.status_code == 500
        data = response.json()
        assert "Failed to load teams data" in data["detail"]