"""Tests for data loader module."""

import pytest
import pandas as pd
from unittest.mock import Mock, MagicMock, patch
from datetime import datetime, date
from src.data.data_loader import DataLoader, DataLoadResult
from src.models.team import TeamModel, TeamCreate
from src.models.player import PlayerModel, PlayerCreate
from src.models.game import GameModel, GameCreate
from src.models.play import PlayModel, PlayCreate


class TestDataLoadResult:
    """Test DataLoadResult class."""
    
    def test_data_load_result_initialization(self):
        """Test DataLoadResult initialization."""
        result = DataLoadResult()
        assert result.success is False
        assert result.records_processed == 0
        assert result.records_inserted == 0
        assert result.records_updated == 0
        assert result.records_skipped == 0
        assert result.errors == []
        assert result.start_time is None
        assert result.end_time is None
    
    def test_data_load_result_duration(self):
        """Test duration calculation."""
        result = DataLoadResult()
        
        # No duration when times not set
        assert result.duration is None
        
        # Duration when times are set
        start = datetime(2023, 1, 1, 10, 0, 0)
        end = datetime(2023, 1, 1, 10, 0, 30)
        result.start_time = start
        result.end_time = end
        assert result.duration == 30.0
    
    def test_data_load_result_to_dict(self):
        """Test converting result to dictionary."""
        result = DataLoadResult()
        result.success = True
        result.records_processed = 100
        result.records_inserted = 80
        result.records_updated = 15
        result.records_skipped = 5
        result.errors = ['Error 1', 'Error 2']
        result.start_time = datetime(2023, 1, 1, 10, 0, 0)
        result.end_time = datetime(2023, 1, 1, 10, 0, 30)
        
        result_dict = result.to_dict()
        
        assert result_dict['success'] is True
        assert result_dict['records_processed'] == 100
        assert result_dict['records_inserted'] == 80
        assert result_dict['records_updated'] == 15
        assert result_dict['records_skipped'] == 5
        assert result_dict['error_count'] == 2
        assert result_dict['errors'] == ['Error 1', 'Error 2']
        assert result_dict['duration_seconds'] == 30.0
        assert result_dict['start_time'] is not None
        assert result_dict['end_time'] is not None


class TestDataLoader:
    """Test DataLoader class."""
    
    @pytest.fixture
    def mock_db_manager(self):
        """Mock database manager."""
        manager = Mock()
        session = Mock()
        manager.get_session.return_value = session
        return manager, session
    
    @pytest.fixture
    def mock_nfl_client(self):
        """Mock NFL data client."""
        return Mock()
    
    @pytest.fixture
    def mock_data_mapper(self):
        """Mock data mapper."""
        return Mock()
    
    @pytest.fixture
    def data_loader(self, mock_db_manager, mock_nfl_client, mock_data_mapper):
        """Create data loader with mocked dependencies."""
        db_manager, _ = mock_db_manager
        return DataLoader(db_manager, mock_nfl_client, mock_data_mapper)
    
    def test_data_loader_initialization(self):
        """Test DataLoader initialization."""
        from unittest.mock import Mock
        loader = DataLoader(
            db_manager=Mock(),
            nfl_client=Mock(),
            data_mapper=Mock()
        )
        assert loader.db_manager is not None
        assert loader.nfl_client is not None
        assert loader.data_mapper is not None
    
    def test_load_teams_success(self, data_loader, mock_nfl_client, 
                               mock_data_mapper, mock_db_manager):
        """Test successful teams loading."""
        db_manager, session = mock_db_manager
        
        # Mock data
        teams_df = pd.DataFrame({'team_abbr': ['SF', 'KC']})
        team_creates = [
            TeamCreate(team_abbr='SF', team_name='San Francisco', 
                      team_nick='49ers', team_conf='NFC', team_division='West'),
            TeamCreate(team_abbr='KC', team_name='Kansas City', 
                      team_nick='Chiefs', team_conf='AFC', team_division='West')
        ]
        
        mock_nfl_client.fetch_teams.return_value = teams_df
        mock_data_mapper.map_teams_data.return_value = team_creates
        
        # Mock session queries (no existing teams)
        session.query.return_value.filter.return_value.first.return_value = None
        
        result = data_loader.load_teams()
        
        assert result.success is True
        assert result.records_processed == 2
        assert result.records_inserted == 2
        assert result.records_updated == 0
        assert result.records_skipped == 0
        assert len(result.errors) == 0
        
        # Verify calls
        mock_nfl_client.fetch_teams.assert_called_once()
        mock_data_mapper.map_teams_data.assert_called_once_with(teams_df)
        session.commit.assert_called_once()
        session.close.assert_called_once()
    
    def test_load_teams_with_updates(self, data_loader, mock_nfl_client,
                                   mock_data_mapper, mock_db_manager):
        """Test teams loading with existing teams (updates)."""
        db_manager, session = mock_db_manager
        
        # Mock existing team
        existing_team = Mock(spec=TeamModel)
        existing_team.team_abbr = 'SF'
        
        teams_df = pd.DataFrame({'team_abbr': ['SF']})
        team_creates = [
            TeamCreate(team_abbr='SF', team_name='San Francisco', 
                      team_nick='49ers', team_conf='NFC', team_division='West')
        ]
        
        mock_nfl_client.fetch_teams.return_value = teams_df
        mock_data_mapper.map_teams_data.return_value = team_creates
        session.query.return_value.filter.return_value.first.return_value = existing_team
        
        result = data_loader.load_teams()
        
        assert result.success is True
        assert result.records_processed == 1
        assert result.records_inserted == 0
        assert result.records_updated == 1
        assert result.records_skipped == 0
    
    def test_load_teams_empty_data(self, data_loader, mock_nfl_client,
                                 mock_data_mapper, mock_db_manager):
        """Test teams loading with empty data."""
        db_manager, session = mock_db_manager
        
        mock_nfl_client.fetch_teams.return_value = pd.DataFrame()
        
        result = data_loader.load_teams()
        
        assert result.success is True
        assert result.records_processed == 0
        mock_data_mapper.map_teams_data.assert_not_called()
    
    def test_load_teams_error(self, data_loader, mock_nfl_client,
                            mock_data_mapper, mock_db_manager):
        """Test teams loading with error."""
        mock_nfl_client.fetch_teams.side_effect = Exception("API Error")
        
        result = data_loader.load_teams()
        
        assert result.success is False
        assert len(result.errors) == 1
        assert "API Error" in result.errors[0]
    
    def test_load_players_success(self, data_loader, mock_nfl_client,
                                mock_data_mapper, mock_db_manager):
        """Test successful players loading."""
        db_manager, session = mock_db_manager
        
        players_df = pd.DataFrame({'player_id': ['00-0012345']})
        player_creates = [
            PlayerCreate(player_id='00-0012345', full_name='John Doe')
        ]
        
        mock_nfl_client.fetch_players.return_value = players_df
        mock_data_mapper.map_players_data.return_value = player_creates
        session.query.return_value.filter.return_value.first.return_value = None
        
        result = data_loader.load_players([2023])
        
        assert result.success is True
        assert result.records_processed == 1
        assert result.records_inserted == 1
        
        mock_nfl_client.fetch_players.assert_called_once_with([2023])
    
    def test_load_games_success(self, data_loader, mock_nfl_client,
                              mock_data_mapper, mock_db_manager):
        """Test successful games loading."""
        db_manager, session = mock_db_manager
        
        games_df = pd.DataFrame({'game_id': ['2023_01_SF_KC']})
        game_creates = [
            GameCreate(game_id='2023_01_SF_KC', season=2023, season_type='REG',
                      game_date=date(2023, 9, 10), home_team='KC', away_team='SF')
        ]
        
        mock_nfl_client.fetch_games.return_value = games_df
        mock_data_mapper.map_games_data.return_value = game_creates
        session.query.return_value.filter.return_value.first.return_value = None
        
        result = data_loader.load_games([2023])
        
        assert result.success is True
        assert result.records_processed == 1
        assert result.records_inserted == 1
        
        mock_nfl_client.fetch_games.assert_called_once_with([2023])
    
    def test_load_plays_success(self, data_loader, mock_nfl_client,
                              mock_data_mapper, mock_db_manager):
        """Test successful plays loading."""
        db_manager, session = mock_db_manager
        
        plays_df = pd.DataFrame({'play_id': ['play_1', 'play_2']})
        play_creates = [
            PlayCreate(play_id='play_1', game_id='game_1', season=2023),
            PlayCreate(play_id='play_2', game_id='game_1', season=2023)
        ]
        
        mock_nfl_client.fetch_plays.return_value = plays_df
        mock_data_mapper.map_plays_data.return_value = [play_creates]  # One batch
        session.query.return_value.filter.return_value.first.return_value = None
        
        result = data_loader.load_plays([2023])
        
        assert result.success is True
        assert result.records_processed == 2
        assert result.records_inserted == 2
        
        mock_nfl_client.fetch_plays.assert_called_once_with([2023], None)
    
    def test_load_plays_with_weeks(self, data_loader, mock_nfl_client,
                                 mock_data_mapper, mock_db_manager):
        """Test plays loading with specific weeks."""
        db_manager, session = mock_db_manager
        
        plays_df = pd.DataFrame({'play_id': ['play_1']})
        play_creates = [PlayCreate(play_id='play_1', game_id='game_1', season=2023)]
        
        mock_nfl_client.fetch_plays.return_value = plays_df
        mock_data_mapper.map_plays_data.return_value = [play_creates]
        session.query.return_value.filter.return_value.first.return_value = None
        
        result = data_loader.load_plays([2023], weeks=[1, 2])
        
        mock_nfl_client.fetch_plays.assert_called_once_with([2023], [1, 2])
    
    def test_load_plays_multiple_batches(self, data_loader, mock_nfl_client,
                                       mock_data_mapper, mock_db_manager):
        """Test plays loading with multiple batches."""
        db_manager, session = mock_db_manager
        
        plays_df = pd.DataFrame({'play_id': ['play_1', 'play_2', 'play_3']})
        
        # Two batches
        batch1 = [PlayCreate(play_id='play_1', game_id='game_1', season=2023),
                 PlayCreate(play_id='play_2', game_id='game_1', season=2023)]
        batch2 = [PlayCreate(play_id='play_3', game_id='game_1', season=2023)]
        
        mock_nfl_client.fetch_plays.return_value = plays_df
        mock_data_mapper.map_plays_data.return_value = [batch1, batch2]
        session.query.return_value.filter.return_value.first.return_value = None
        
        result = data_loader.load_plays([2023])
        
        assert result.success is True
        assert result.records_processed == 3
        assert result.records_inserted == 3
        # Should commit twice (once per batch)
        assert session.commit.call_count == 2
    
    def test_load_full_dataset(self, data_loader, mock_nfl_client,
                             mock_data_mapper, mock_db_manager):
        """Test loading full dataset."""
        db_manager, session = mock_db_manager
        
        # Mock all data fetches to return empty data for simplicity
        mock_nfl_client.fetch_teams.return_value = pd.DataFrame()
        mock_nfl_client.fetch_games.return_value = pd.DataFrame()
        mock_nfl_client.fetch_players.return_value = pd.DataFrame()
        mock_nfl_client.fetch_plays.return_value = pd.DataFrame()
        
        results = data_loader.load_full_dataset([2023])
        
        assert 'teams' in results
        assert 'games' in results
        assert 'players' in results
        assert 'plays' in results
        
        # All should be successful (empty data is not an error)
        assert all(result.success for result in results.values())
    
    def test_load_full_dataset_no_plays(self, data_loader, mock_nfl_client,
                                      mock_data_mapper, mock_db_manager):
        """Test loading full dataset without plays."""
        db_manager, session = mock_db_manager
        
        mock_nfl_client.fetch_teams.return_value = pd.DataFrame()
        mock_nfl_client.fetch_games.return_value = pd.DataFrame()
        mock_nfl_client.fetch_players.return_value = pd.DataFrame()
        
        results = data_loader.load_full_dataset([2023], include_plays=False)
        
        assert 'teams' in results
        assert 'games' in results
        assert 'players' in results
        assert 'plays' not in results
    
    @patch('src.data.data_loader.TeamModel')
    @patch('src.data.data_loader.PlayerModel')
    @patch('src.data.data_loader.GameModel')
    @patch('src.data.data_loader.PlayModel')
    def test_get_load_status(self, mock_play_model, mock_game_model, 
                           mock_player_model, mock_team_model, data_loader,
                           mock_db_manager):
        """Test getting load status."""
        db_manager, session = mock_db_manager
        
        # Mock count queries
        session.query.return_value.count.side_effect = [32, 2000, 500, 50000]
        
        # Mock latest game query
        mock_game = Mock()
        mock_game.game_date = date(2023, 12, 31)
        mock_game.season = 2023
        session.query.return_value.order_by.return_value.first.return_value = mock_game
        
        # Mock seasons query
        session.query.return_value.distinct.return_value.all.return_value = [(2022,), (2023,)]
        
        status = data_loader.get_load_status()
        
        assert status['teams_count'] == 32
        assert status['players_count'] == 2000
        assert status['games_count'] == 500
        assert status['plays_count'] == 50000
        assert status['latest_game_date'] == '2023-12-31'
        assert status['latest_season'] == 2023
        assert status['available_seasons'] == [2022, 2023]
    
    def test_get_load_status_error(self, data_loader, mock_db_manager):
        """Test get_load_status with error."""
        db_manager, session = mock_db_manager
        session.query.side_effect = Exception("Database error")
        
        status = data_loader.get_load_status()
        
        assert 'error' in status
        assert "Database error" in status['error']


class TestDataLoaderErrorHandling:
    """Test error handling in DataLoader."""
    
    @pytest.fixture
    def data_loader(self):
        return DataLoader(Mock(), Mock(), Mock())
    
    def test_load_teams_session_error(self, data_loader):
        """Test teams loading with session error."""
        data_loader.nfl_client.fetch_teams.return_value = pd.DataFrame({'team_abbr': ['SF']})
        data_loader.data_mapper.map_teams_data.return_value = [
            TeamCreate(team_abbr='SF', team_name='San Francisco', 
                      team_nick='49ers', team_conf='NFC', team_division='West')
        ]
        
        # Mock session to raise error
        session = Mock()
        session.query.side_effect = Exception("Database error")
        data_loader.db_manager.get_session.return_value = session
        
        result = data_loader.load_teams()
        
        # Should succeed overall but skip the failed team
        assert result.success is True
        assert result.records_skipped == 1
        assert len(result.errors) == 1
        assert "Database error" in result.errors[0]
        session.close.assert_called_once()
    
    def test_load_teams_individual_errors(self, data_loader):
        """Test teams loading with individual team errors."""
        data_loader.nfl_client.fetch_teams.return_value = pd.DataFrame({'team_abbr': ['SF', 'KC']})
        
        # One valid, one invalid team
        team_creates = [
            TeamCreate(team_abbr='SF', team_name='San Francisco', 
                      team_nick='49ers', team_conf='NFC', team_division='West'),
            Mock()  # Invalid team that will cause error
        ]
        team_creates[1].model_dump.side_effect = Exception("Invalid team")
        
        data_loader.data_mapper.map_teams_data.return_value = team_creates
        
        session = Mock()
        session.query.return_value.filter.return_value.first.return_value = None
        data_loader.db_manager.get_session.return_value = session
        
        result = data_loader.load_teams()
        
        # Should succeed overall but skip the invalid team
        assert result.success is True
        assert result.records_processed == 2
        assert result.records_inserted == 1  # Only the valid one
        assert result.records_skipped == 1
        assert len(result.errors) == 1