"""Tests for data mapper module."""

import pytest
import pandas as pd
from datetime import date, datetime
from src.data.data_mapper import DataMapper
from src.models.team import TeamCreate
from src.models.player import PlayerCreate
from src.models.game import GameCreate
from src.models.play import PlayCreate


class TestDataMapper:
    """Test DataMapper class."""
    
    @pytest.fixture
    def mapper(self):
        """Create data mapper for testing."""
        return DataMapper()
    
    def test_mapper_initialization(self, mapper):
        """Test mapper initialization."""
        assert isinstance(mapper._team_cache, dict)
        assert len(mapper._team_cache) > 0
        # Test some known teams
        assert 'SF' in mapper._team_cache
        assert 'KC' in mapper._team_cache
        assert mapper._team_cache['SF']['team_conf'] == 'NFC'
        assert mapper._team_cache['KC']['team_conf'] == 'AFC'


class TestTeamsMapping:
    """Test teams data mapping."""
    
    @pytest.fixture
    def mapper(self):
        return DataMapper()
    
    def test_map_teams_data_basic(self, mapper):
        """Test basic teams data mapping."""
        teams_df = pd.DataFrame({
            'team_abbr': ['SF', 'KC'],
            'team_name': ['San Francisco', 'Kansas City'],
            'team_nick': ['49ers', 'Chiefs']
        })
        
        result = mapper.map_teams_data(teams_df)
        
        assert len(result) == 2
        assert all(isinstance(team, TeamCreate) for team in result)
        
        sf_team = next(t for t in result if t.team_abbr == 'SF')
        assert sf_team.team_name == 'San Francisco'
        assert sf_team.team_nick == '49ers'
        assert sf_team.team_conf == 'NFC'
        assert sf_team.team_division == 'West'
    
    def test_map_teams_data_with_colors(self, mapper):
        """Test teams mapping with color data."""
        teams_df = pd.DataFrame({
            'team_abbr': ['SF'],
            'team_name': ['San Francisco'],
            'team_nick': ['49ers'],
            'team_color': ['#AA0000'],
            'team_color2': ['#B3995D'],
            'team_logo_espn': ['https://example.com/logo.png']
        })
        
        result = mapper.map_teams_data(teams_df)
        
        assert len(result) == 1
        team = result[0]
        assert team.team_color == '#AA0000'
        assert team.team_color2 == '#B3995D'
        assert team.team_logo_espn == 'https://example.com/logo.png'
    
    def test_map_teams_data_empty_abbr(self, mapper):
        """Test teams mapping with empty abbreviation."""
        teams_df = pd.DataFrame({
            'team_abbr': ['', 'KC'],
            'team_name': ['Empty', 'Kansas City'],
            'team_nick': ['Empty', 'Chiefs']
        })
        
        result = mapper.map_teams_data(teams_df)
        
        # Should skip empty abbreviation
        assert len(result) == 1
        assert result[0].team_abbr == 'KC'
    
    def test_map_teams_data_invalid_row(self, mapper):
        """Test teams mapping with invalid row."""
        teams_df = pd.DataFrame({
            'team_abbr': ['SF', 'INVALID_LONG_ABBR'],
            'team_name': ['San Francisco', 'Invalid'],
            'team_nick': ['49ers', 'Team']
        })
        
        # Should handle validation error gracefully
        result = mapper.map_teams_data(teams_df)
        
        # Should still get valid team
        assert len(result) >= 1
        valid_teams = [t for t in result if t.team_abbr == 'SF']
        assert len(valid_teams) == 1


class TestPlayersMapping:
    """Test players data mapping."""
    
    @pytest.fixture
    def mapper(self):
        return DataMapper()
    
    def test_map_players_data_basic(self, mapper):
        """Test basic players data mapping."""
        players_df = pd.DataFrame({
            'player_id': ['00-0012345', '00-0012346'],
            'full_name': ['John Doe', 'Jane Smith'],
            'team': ['SF', 'KC'],
            'position': ['QB', 'RB']
        })
        
        result = mapper.map_players_data(players_df)
        
        assert len(result) == 2
        assert all(isinstance(player, PlayerCreate) for player in result)
        
        player1 = result[0]
        assert player1.player_id == '00-0012345'
        assert player1.full_name == 'John Doe'
        assert player1.team_abbr == 'SF'
        assert player1.position == 'QB'
    
    def test_map_players_data_with_details(self, mapper):
        """Test players mapping with detailed data."""
        players_df = pd.DataFrame({
            'player_id': ['00-0012345'],
            'full_name': ['John Doe'],
            'gsis_id': ['12345'],
            'team': ['SF'],
            'position': ['QB'],
            'jersey_number': [12],
            'height': ['6-2'],
            'weight': [220],
            'age': [28],
            'rookie_year': [2018],
            'status': ['active']
        })
        
        result = mapper.map_players_data(players_df)
        
        assert len(result) == 1
        player = result[0]
        assert player.gsis_id == '12345'
        assert player.jersey_number == 12
        assert player.height == 74  # 6'2" = 74 inches
        assert player.weight == 220
        assert player.age == 28
        assert player.rookie_year == 2018
        assert player.status == 'active'
    
    def test_map_players_data_invalid_values(self, mapper):
        """Test players mapping with invalid values."""
        players_df = pd.DataFrame({
            'player_id': ['00-0012345'],
            'full_name': ['John Doe'],
            'jersey_number': [999],  # Invalid jersey number
            'height': ['invalid'],   # Invalid height
            'weight': [-100],        # Invalid weight
            'age': [100],           # Invalid age
        })
        
        result = mapper.map_players_data(players_df)
        
        assert len(result) == 1
        player = result[0]
        # Should skip invalid values
        assert not hasattr(player, 'jersey_number') or player.jersey_number is None
        assert not hasattr(player, 'height') or player.height is None
        assert not hasattr(player, 'weight') or player.weight is None
        assert not hasattr(player, 'age') or player.age is None
    
    def test_map_players_data_empty_id(self, mapper):
        """Test players mapping with empty player ID."""
        players_df = pd.DataFrame({
            'player_id': ['', '00-0012346'],
            'full_name': ['Empty ID', 'Valid Player']
        })
        
        result = mapper.map_players_data(players_df)
        
        # Should skip empty ID
        assert len(result) == 1
        assert result[0].player_id == '00-0012346'


class TestGamesMapping:
    """Test games data mapping."""
    
    @pytest.fixture
    def mapper(self):
        return DataMapper()
    
    def test_map_games_data_basic(self, mapper):
        """Test basic games data mapping."""
        games_df = pd.DataFrame({
            'game_id': ['2023_01_SF_KC'],
            'season': [2023],
            'season_type': ['REG'],
            'gameday': ['2023-09-10'],
            'home_team': ['KC'],
            'away_team': ['SF']
        })
        
        result = mapper.map_games_data(games_df)
        
        assert len(result) == 1
        game = result[0]
        assert isinstance(game, GameCreate)
        assert game.game_id == '2023_01_SF_KC'
        assert game.season == 2023
        assert game.season_type == 'REG'
        assert game.game_date == date(2023, 9, 10)
        assert game.home_team == 'KC'
        assert game.away_team == 'SF'
    
    def test_map_games_data_with_details(self, mapper):
        """Test games mapping with detailed data."""
        games_df = pd.DataFrame({
            'game_id': ['2023_01_SF_KC'],
            'season': [2023],
            'season_type': ['REG'],
            'gameday': ['2023-09-10'],
            'home_team': ['KC'],
            'away_team': ['SF'],
            'week': [1],
            'home_score': [24],
            'away_score': [21],
            'roof': ['dome'],
            'surface': ['fieldturf'],
            'temp': [72],
            'wind': [5]
        })
        
        result = mapper.map_games_data(games_df)
        
        assert len(result) == 1
        game = result[0]
        assert game.week == 1
        assert game.home_score == 24
        assert game.away_score == 21
        assert game.roof == 'dome'
        assert game.surface == 'fieldturf'
        assert game.temp == 72
        assert game.wind == 5
        assert game.game_finished is True  # Should be True when scores present
    
    def test_map_games_data_invalid_date(self, mapper):
        """Test games mapping with invalid date."""
        games_df = pd.DataFrame({
            'game_id': ['2023_01_SF_KC', '2023_02_SF_DAL'],
            'season': [2023, 2023],
            'season_type': ['REG', 'REG'],
            'gameday': ['invalid-date', '2023-09-17'],
            'home_team': ['KC', 'DAL'],
            'away_team': ['SF', 'SF']
        })
        
        result = mapper.map_games_data(games_df)
        
        # Should skip invalid date
        assert len(result) == 1
        assert result[0].game_id == '2023_02_SF_DAL'
    
    def test_map_games_data_missing_required(self, mapper):
        """Test games mapping with missing required fields."""
        games_df = pd.DataFrame({
            'game_id': ['2023_01_SF_KC', ''],  # Missing game_id in second row
            'season': [2023, 2023],
            'season_type': ['REG', 'REG'],
            'gameday': ['2023-09-10', '2023-09-17'],
            'home_team': ['KC', 'DAL'],
            'away_team': ['SF', '']  # Missing away_team in second row
        })
        
        result = mapper.map_games_data(games_df)
        
        # Should only get first game
        assert len(result) == 1
        assert result[0].game_id == '2023_01_SF_KC'


class TestPlaysMapping:
    """Test plays data mapping."""
    
    @pytest.fixture
    def mapper(self):
        return DataMapper()
    
    def test_map_plays_data_basic(self, mapper):
        """Test basic plays data mapping."""
        plays_df = pd.DataFrame({
            'play_id': ['2023_01_SF_KC_1', '2023_01_SF_KC_2'],
            'game_id': ['2023_01_SF_KC', '2023_01_SF_KC'],
            'season': [2023, 2023],
            'posteam': ['SF', 'KC'],
            'play_type': ['pass', 'run']
        })
        
        result = mapper.map_plays_data(plays_df, batch_size=10)
        
        assert len(result) == 1  # One batch
        batch = result[0]
        assert len(batch) == 2
        assert all(isinstance(play, PlayCreate) for play in batch)
        
        play1 = batch[0]
        assert play1.play_id == '2023_01_SF_KC_1'
        assert play1.game_id == '2023_01_SF_KC'
        assert play1.season == 2023
        assert play1.posteam == 'SF'
        assert play1.play_type == 'pass'
    
    def test_map_plays_data_with_details(self, mapper):
        """Test plays mapping with detailed data."""
        plays_df = pd.DataFrame({
            'play_id': ['2023_01_SF_KC_1'],
            'game_id': ['2023_01_SF_KC'],
            'season': [2023],
            'week': [1],
            'posteam': ['SF'],
            'defteam': ['KC'],
            'qtr': [1],
            'game_seconds_remaining': [3540],
            'yardline_100': [75],
            'down': [1],
            'ydstogo': [10],
            'yards_gained': [12],
            'ep': [0.92],
            'epa': [1.45],
            'wp': [0.52],
            'wpa': [0.03],
            'touchdown': [False],
            'interception': [False]
        })
        
        result = mapper.map_plays_data(plays_df)
        
        assert len(result) == 1
        play = result[0][0]
        assert play.week == 1
        assert play.defteam == 'KC'
        assert play.qtr == 1
        assert play.game_seconds_remaining == 3540
        assert play.yardline_100 == 75
        assert play.down == 1
        assert play.ydstogo == 10
        assert play.yards_gained == 12
        assert play.ep == 0.92
        assert play.epa == 1.45
        assert play.wp == 0.52
        assert play.wpa == 0.03
        assert play.touchdown is False
        assert play.interception is False
    
    def test_map_plays_data_batching(self, mapper):
        """Test plays data batching."""
        plays_df = pd.DataFrame({
            'play_id': [f'play_{i}' for i in range(5)],
            'game_id': ['game'] * 5,
            'season': [2023] * 5
        })
        
        result = mapper.map_plays_data(plays_df, batch_size=2)
        
        assert len(result) == 3  # 2 + 2 + 1 = 3 batches
        assert len(result[0]) == 2
        assert len(result[1]) == 2
        assert len(result[2]) == 1
    
    def test_map_plays_data_invalid_values(self, mapper):
        """Test plays mapping with invalid values."""
        plays_df = pd.DataFrame({
            'play_id': ['2023_01_SF_KC_1'],
            'game_id': ['2023_01_SF_KC'],
            'season': [2023],
            'qtr': [10],  # Invalid quarter
            'down': [5],  # Invalid down
            'yards_gained': [200],  # Invalid yards
            'ep': [50.0],  # Invalid EP
            'wp': [2.0]   # Invalid WP
        })
        
        result = mapper.map_plays_data(plays_df)
        
        assert len(result) == 1
        play = result[0][0]
        # Should skip invalid values (use hasattr to check if field was set)
        assert not hasattr(play, 'qtr') or play.qtr is None
        assert not hasattr(play, 'down') or play.down is None
        assert not hasattr(play, 'yards_gained') or play.yards_gained is None
        assert not hasattr(play, 'ep') or play.ep is None
        assert not hasattr(play, 'wp') or play.wp is None
    
    def test_map_plays_data_missing_required(self, mapper):
        """Test plays mapping with missing required fields."""
        plays_df = pd.DataFrame({
            'play_id': ['', 'valid_play'],  # Empty play_id
            'game_id': ['game', ''],        # Empty game_id
            'season': [2023, 2023]
        })
        
        result = mapper.map_plays_data(plays_df)
        
        # Should skip both invalid rows
        assert len(result) == 0 or (len(result) == 1 and len(result[0]) == 0)


class TestDataMapperIntegration:
    """Integration tests for data mapper."""
    
    @pytest.fixture
    def mapper(self):
        return DataMapper()
    
    def test_full_mapping_workflow(self, mapper):
        """Test complete mapping workflow with realistic data."""
        # Teams
        teams_df = pd.DataFrame({
            'team_abbr': ['SF', 'KC'],
            'team_name': ['San Francisco', 'Kansas City'],
            'team_nick': ['49ers', 'Chiefs']
        })
        teams = mapper.map_teams_data(teams_df)
        assert len(teams) == 2
        
        # Players
        players_df = pd.DataFrame({
            'player_id': ['00-0012345', '00-0012346'],
            'full_name': ['John Doe', 'Jane Smith'],
            'team': ['SF', 'KC'],
            'position': ['QB', 'RB']
        })
        players = mapper.map_players_data(players_df)
        assert len(players) == 2
        
        # Games
        games_df = pd.DataFrame({
            'game_id': ['2023_01_SF_KC'],
            'season': [2023],
            'season_type': ['REG'],
            'gameday': ['2023-09-10'],
            'home_team': ['KC'],
            'away_team': ['SF']
        })
        games = mapper.map_games_data(games_df)
        assert len(games) == 1
        
        # Plays
        plays_df = pd.DataFrame({
            'play_id': ['2023_01_SF_KC_1'],
            'game_id': ['2023_01_SF_KC'],
            'season': [2023],
            'posteam': ['SF']
        })
        play_batches = mapper.map_plays_data(plays_df)
        assert len(play_batches) == 1
        assert len(play_batches[0]) == 1