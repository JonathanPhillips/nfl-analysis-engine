"""Tests for NFL data client."""

import pytest
import pandas as pd
from unittest.mock import patch, MagicMock
from datetime import datetime, date
from src.data.nfl_data_client import NFLDataClient, DataFetchConfig


class TestDataFetchConfig:
    """Test DataFetchConfig dataclass."""
    
    def test_default_config(self):
        """Test default configuration values."""
        config = DataFetchConfig()
        assert config.max_retries == 3
        assert config.timeout_seconds == 300
        assert config.cache_enabled is True
        assert config.batch_size == 1000
        assert config.rate_limit_delay == 0.1
    
    def test_custom_config(self):
        """Test custom configuration values."""
        config = DataFetchConfig(
            max_retries=5,
            timeout_seconds=600,
            cache_enabled=False,
            batch_size=500,
            rate_limit_delay=0.2
        )
        assert config.max_retries == 5
        assert config.timeout_seconds == 600
        assert config.cache_enabled is False
        assert config.batch_size == 500
        assert config.rate_limit_delay == 0.2


class TestNFLDataClient:
    """Test NFLDataClient class."""
    
    @pytest.fixture
    def client(self):
        """Create NFL data client for testing."""
        config = DataFetchConfig(cache_enabled=True)
        return NFLDataClient(config)
    
    @pytest.fixture
    def client_no_cache(self):
        """Create NFL data client without caching."""
        config = DataFetchConfig(cache_enabled=False)
        return NFLDataClient(config)
    
    def test_client_initialization(self, client):
        """Test client initialization."""
        assert client.config.cache_enabled is True
        assert isinstance(client._cache, dict)
    
    def test_client_initialization_no_cache(self, client_no_cache):
        """Test client initialization without cache."""
        assert client_no_cache.config.cache_enabled is False
        assert isinstance(client_no_cache._cache, dict)
        assert len(client_no_cache._cache) == 0
    
    @patch('src.data.nfl_data_client.NFL_DATA_PY_AVAILABLE', True)
    @patch('src.data.nfl_data_client.nfl.import_team_desc')
    def test_fetch_teams_success(self, mock_import, client):
        """Test successful teams data fetch."""
        # Mock data
        mock_df = pd.DataFrame({
            'team_abbr': ['SF', 'KC'],
            'team_name': ['San Francisco', 'Kansas City'],
            'team_nick': ['49ers', 'Chiefs']
        })
        mock_import.return_value = mock_df
        
        result = client.fetch_teams()
        
        assert isinstance(result, pd.DataFrame)
        assert len(result) == 2
        assert 'SF' in result['team_abbr'].values
        assert 'KC' in result['team_abbr'].values
        mock_import.assert_called_once()
    
    @patch('src.data.nfl_data_client.NFL_DATA_PY_AVAILABLE', True)
    @patch('src.data.nfl_data_client.nfl.import_team_desc')
    def test_fetch_teams_caching(self, mock_import, client):
        """Test teams data caching."""
        mock_df = pd.DataFrame({
            'team_abbr': ['SF'],
            'team_name': ['San Francisco'],
            'team_nick': ['49ers']
        })
        mock_import.return_value = mock_df
        
        # First call
        result1 = client.fetch_teams()
        # Second call
        result2 = client.fetch_teams()
        
        # Should only call import once due to caching
        mock_import.assert_called_once()
        pd.testing.assert_frame_equal(result1, result2)
    
    @patch('src.data.nfl_data_client.NFL_DATA_PY_AVAILABLE', True)
    @patch('src.data.nfl_data_client.nfl.import_team_desc')
    def test_fetch_teams_no_caching(self, mock_import, client_no_cache):
        """Test teams data without caching."""
        mock_df = pd.DataFrame({
            'team_abbr': ['SF'],
            'team_name': ['San Francisco'],
            'team_nick': ['49ers']
        })
        mock_import.return_value = mock_df
        
        # Two calls
        client_no_cache.fetch_teams()
        client_no_cache.fetch_teams()
        
        # Should call import twice without caching
        assert mock_import.call_count == 2
    
    @patch('src.data.nfl_data_client.NFL_DATA_PY_AVAILABLE', True)
    @patch('src.data.nfl_data_client.nfl.import_team_desc')
    def test_fetch_teams_error(self, mock_import, client):
        """Test teams data fetch error handling."""
        mock_import.side_effect = Exception("Network error")
        
        with pytest.raises(Exception, match="Network error"):
            client.fetch_teams()
    
    @patch('src.data.nfl_data_client.NFL_DATA_PY_AVAILABLE', True)
    @patch('src.data.nfl_data_client.nfl.import_schedules')
    def test_fetch_games_success(self, mock_import, client):
        """Test successful games data fetch."""
        mock_df = pd.DataFrame({
            'game_id': ['2023_01_SF_KC'],
            'season': [2023],
            'home_team': ['KC'],
            'away_team': ['SF']
        })
        mock_import.return_value = mock_df
        
        result = client.fetch_games([2023])
        
        assert isinstance(result, pd.DataFrame)
        assert len(result) == 1
        mock_import.assert_called_once_with([2023])
    
    @patch('src.data.nfl_data_client.NFL_DATA_PY_AVAILABLE', True)
    @patch('src.data.nfl_data_client.nfl.import_schedules')
    def test_fetch_games_multiple_seasons(self, mock_import, client):
        """Test games fetch for multiple seasons."""
        mock_df = pd.DataFrame({
            'game_id': ['2022_01_SF_KC', '2023_01_SF_KC'],
            'season': [2022, 2023],
            'home_team': ['KC', 'KC'],
            'away_team': ['SF', 'SF']
        })
        mock_import.return_value = mock_df
        
        result = client.fetch_games([2022, 2023])
        
        assert len(result) == 2
        mock_import.assert_called_once_with([2022, 2023])
    
    @patch('src.data.nfl_data_client.NFL_DATA_PY_AVAILABLE', True)
    @patch('src.data.nfl_data_client.nfl.import_pbp_data')
    def test_fetch_plays_success(self, mock_import, client):
        """Test successful plays data fetch."""
        mock_df = pd.DataFrame({
            'play_id': ['2023_01_SF_KC_1', '2023_01_SF_KC_2'],
            'game_id': ['2023_01_SF_KC', '2023_01_SF_KC'],
            'season': [2023, 2023],
            'play_type': ['pass', 'run']
        })
        mock_import.return_value = mock_df
        
        result = client.fetch_plays([2023])
        
        assert isinstance(result, pd.DataFrame)
        assert len(result) == 2
        mock_import.assert_called_once_with([2023], downcast=False)
    
    @patch('src.data.nfl_data_client.NFL_DATA_PY_AVAILABLE', True)
    @patch('src.data.nfl_data_client.nfl.import_rosters')
    def test_fetch_players_success(self, mock_import, client):
        """Test successful players data fetch."""
        mock_df = pd.DataFrame({
            'player_id': ['00-0012345', '00-0012346'],
            'full_name': ['John Doe', 'Jane Smith'],
            'position': ['QB', 'RB']
        })
        mock_import.return_value = mock_df
        
        result = client.fetch_players([2023])
        
        assert isinstance(result, pd.DataFrame)
        assert len(result) == 2
        mock_import.assert_called_once_with([2023])
    
    @patch('src.data.nfl_data_client.NFL_DATA_PY_AVAILABLE', True)
    @patch('src.data.nfl_data_client.nfl.import_rosters')
    def test_fetch_players_current_season(self, mock_import, client):
        """Test fetching current season players."""
        mock_df = pd.DataFrame({
            'player_id': ['00-0012345'],
            'full_name': ['John Doe'],
            'position': ['QB']
        })
        mock_import.return_value = mock_df
        
        result = client.fetch_players()
        
        assert len(result) == 1
        # Should call with current year
        current_year = datetime.now().year
        mock_import.assert_called_once_with([current_year])
    
    def test_get_available_seasons(self, client):
        """Test getting available seasons."""
        seasons = client.get_available_seasons()
        
        assert isinstance(seasons, list)
        assert len(seasons) > 0
        assert 1999 in seasons  # NFL data typically starts from 1999
        current_year = datetime.now().year
        # Should include up to current year or previous year
        assert max(seasons) >= current_year - 1
    
    @patch('src.data.nfl_data_client.NFL_DATA_PY_AVAILABLE', True)
    @patch('src.data.nfl_data_client.nfl.import_schedules')
    def test_fetch_season_games(self, mock_import, client):
        """Test fetching games for specific season and type."""
        mock_df = pd.DataFrame({
            'game_id': ['2023_01_SF_KC', '2023_20_SF_KC'],
            'season': [2023, 2023],
            'season_type': ['REG', 'POST'],
            'home_team': ['KC', 'KC'],
            'away_team': ['SF', 'SF']
        })
        mock_import.return_value = mock_df
        
        result = client.fetch_season_games(2023, 'REG')
        
        assert len(result) == 1
        assert result['season_type'].iloc[0] == 'REG'
    
    @patch('src.data.nfl_data_client.NFL_DATA_PY_AVAILABLE', True)
    @patch('src.data.nfl_data_client.nfl.import_schedules')
    def test_fetch_recent_games(self, mock_import, client):
        """Test fetching recent games."""
        today = pd.Timestamp.now()
        old_date = today - pd.Timedelta(days=10)
        recent_date = today - pd.Timedelta(days=3)
        
        mock_df = pd.DataFrame({
            'game_id': ['2023_01_SF_KC', '2023_02_SF_KC'],
            'season': [2023, 2023],
            'gameday': [old_date, recent_date],
            'home_team': ['KC', 'KC'],
            'away_team': ['SF', 'SF']
        })
        mock_import.return_value = mock_df
        
        result = client.fetch_recent_games(days=7)
        
        assert len(result) == 1
        assert result['game_id'].iloc[0] == '2023_02_SF_KC'
    
    @patch('src.data.nfl_data_client.NFL_DATA_PY_AVAILABLE', True)
    @patch('src.data.nfl_data_client.nfl.import_schedules')
    def test_fetch_team_games(self, mock_import, client):
        """Test fetching games for specific team."""
        mock_df = pd.DataFrame({
            'game_id': ['2023_01_SF_KC', '2023_02_SF_DAL'],
            'season': [2023, 2023],
            'home_team': ['KC', 'DAL'],
            'away_team': ['SF', 'SF']
        })
        mock_import.return_value = mock_df
        
        result = client.fetch_team_games('SF', 2023)
        
        assert len(result) == 2  # SF appears in both games
        assert all('SF' in [row['home_team'], row['away_team']] 
                  for _, row in result.iterrows())
    
    def test_clear_cache(self, client):
        """Test clearing cache."""
        # Add some fake cache data
        client._cache['test'] = pd.DataFrame({'a': [1, 2, 3]})
        assert len(client._cache) > 0
        
        client.clear_cache()
        assert len(client._cache) == 0
    
    def test_get_cache_info(self, client):
        """Test getting cache information."""
        # Add some fake cache data
        test_df = pd.DataFrame({'a': [1, 2, 3], 'b': [4, 5, 6]})
        client._cache['test'] = test_df
        
        info = client.get_cache_info()
        
        assert info['cache_enabled'] is True
        assert info['cached_items'] == 1
        assert 'test' in info['cache_keys']
        assert 'estimated_memory_mb' in info
    
    def test_get_cache_info_disabled(self, client_no_cache):
        """Test getting cache info when caching disabled."""
        info = client_no_cache.get_cache_info()
        
        assert info['cache_enabled'] is False
        assert info['cached_items'] == 0


class TestNFLDataClientErrorHandling:
    """Test error handling in NFLDataClient."""
    
    @pytest.fixture
    def client(self):
        """Create client for error testing."""
        return NFLDataClient()
    
    @patch('src.data.nfl_data_client.NFL_DATA_PY_AVAILABLE', True)
    @patch('src.data.nfl_data_client.nfl.import_schedules')
    def test_fetch_games_error(self, mock_import, client):
        """Test games fetch error handling."""
        mock_import.side_effect = Exception("API error")
        
        with pytest.raises(Exception, match="API error"):
            client.fetch_games([2023])
    
    @patch('src.data.nfl_data_client.NFL_DATA_PY_AVAILABLE', True)
    @patch('src.data.nfl_data_client.nfl.import_pbp_data')
    def test_fetch_plays_error(self, mock_import, client):
        """Test plays fetch error handling."""
        mock_import.side_effect = Exception("Data error")
        
        with pytest.raises(Exception, match="Data error"):
            client.fetch_plays([2023])
    
    @patch('src.data.nfl_data_client.NFL_DATA_PY_AVAILABLE', True)
    @patch('src.data.nfl_data_client.nfl.import_rosters')
    def test_fetch_players_error_handling(self, mock_import, client):
        """Test players fetch with partial errors."""
        # First call succeeds, second fails
        mock_import.side_effect = [
            pd.DataFrame({'player_id': ['1'], 'full_name': ['Test']}),
            Exception("Season data error")
        ]
        
        # Should return data from successful call
        result = client.fetch_players([2022, 2023])
        assert len(result) == 1
    
    @patch('src.data.nfl_data_client.NFL_DATA_PY_AVAILABLE', True)
    @patch('src.data.nfl_data_client.nfl.import_schedules')
    def test_fetch_recent_games_no_gameday(self, mock_import, client):
        """Test recent games fetch without gameday column."""
        mock_df = pd.DataFrame({
            'game_id': ['2023_01_SF_KC'],
            'season': [2023],
            # No gameday column
        })
        mock_import.return_value = mock_df
        
        result = client.fetch_recent_games()
        assert len(result) == 0  # Should return empty DataFrame