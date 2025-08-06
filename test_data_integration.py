#!/usr/bin/env python3
"""Integration test for NFL data integration system without external dependencies."""

import os
import tempfile
import pandas as pd
from datetime import date, datetime
from sqlalchemy import create_engine
from unittest.mock import Mock, patch
from src.database.manager import DatabaseManager
from src.data.data_mapper import DataMapper
from src.data.data_loader import DataLoader
from src.models.team import TeamCreate
from src.models.player import PlayerCreate
from src.models.game import GameCreate
from src.models.play import PlayCreate


def create_mock_nfl_client():
    """Create a mock NFL data client with sample data."""
    client = Mock()
    
    # Mock teams data
    teams_df = pd.DataFrame({
        'team_abbr': ['SF', 'KC', 'DAL'],
        'team_name': ['San Francisco', 'Kansas City', 'Dallas'],
        'team_nick': ['49ers', 'Chiefs', 'Cowboys'],
        'team_color': ['#AA0000', '#E31837', '#003594'],
        'team_logo_espn': [
            'https://a.espncdn.com/i/teamlogos/nfl/500/sf.png',
            'https://a.espncdn.com/i/teamlogos/nfl/500/kc.png',
            'https://a.espncdn.com/i/teamlogos/nfl/500/dal.png'
        ]
    })
    client.fetch_teams.return_value = teams_df
    
    # Mock games data
    games_df = pd.DataFrame({
        'game_id': ['2023_01_SF_KC', '2023_02_DAL_SF'],
        'season': [2023, 2023],
        'season_type': ['REG', 'REG'],
        'gameday': ['2023-09-10', '2023-09-17'],
        'home_team': ['KC', 'SF'],
        'away_team': ['SF', 'DAL'],
        'week': [1, 2],
        'home_score': [24, 28],
        'away_score': [21, 14],
        'roof': ['dome', 'outdoors'],
        'surface': ['fieldturf', 'grass']
    })
    client.fetch_games.return_value = games_df
    
    # Mock players data
    players_df = pd.DataFrame({
        'player_id': ['00-0012345', '00-0012346', '00-0012347'],
        'full_name': ['Jimmy Garoppolo', 'Patrick Mahomes', 'Dak Prescott'],
        'team': ['SF', 'KC', 'DAL'],
        'position': ['QB', 'QB', 'QB'],
        'jersey_number': [10, 15, 4],
        'height': ['6-2', '6-3', '6-2'],
        'weight': [225, 230, 238],
        'age': [32, 28, 30],
        'status': ['ACT', 'ACT', 'ACT']
    })
    client.fetch_players.return_value = players_df
    
    # Mock plays data
    plays_df = pd.DataFrame({
        'play_id': ['2023_01_SF_KC_1', '2023_01_SF_KC_2', '2023_01_SF_KC_3'],
        'game_id': ['2023_01_SF_KC', '2023_01_SF_KC', '2023_01_SF_KC'],
        'season': [2023, 2023, 2023],
        'week': [1, 1, 1],
        'posteam': ['SF', 'KC', 'SF'],
        'defteam': ['KC', 'SF', 'KC'],
        'qtr': [1, 1, 1],
        'down': [1, 2, 3],
        'ydstogo': [10, 7, 8],
        'yardline_100': [75, 68, 73],
        'play_type': ['pass', 'run', 'pass'],
        'yards_gained': [12, 5, -2],
        'ep': [0.92, 1.45, 0.85],
        'epa': [1.23, 0.87, -1.12],
        'wp': [0.52, 0.55, 0.48],
        'wpa': [0.03, 0.02, -0.04],
        'touchdown': [False, False, False],
        'interception': [False, False, False]
    })
    client.fetch_plays.return_value = plays_df
    
    return client


def test_data_integration():
    """Test complete data integration workflow."""
    # Create temporary database
    temp_db = tempfile.NamedTemporaryFile(suffix='.db', delete=False)
    temp_db.close()
    db_url = f"sqlite:///{temp_db.name}"
    
    try:
        print(f"Testing data integration with database: {db_url}")
        
        # Set up components
        engine = create_engine(db_url)
        db_manager = DatabaseManager(engine)
        
        # Create database schema
        print("1. Creating database schema...")
        db_manager.create_all_tables()
        print("✓ Database schema created")
        
        # Set up data components
        data_mapper = DataMapper()
        mock_nfl_client = create_mock_nfl_client()
        data_loader = DataLoader(db_manager, mock_nfl_client, data_mapper)
        
        print("2. Testing data mapper...")
        # Test teams mapping
        teams_df = mock_nfl_client.fetch_teams()
        team_creates = data_mapper.map_teams_data(teams_df)
        assert len(team_creates) == 3
        assert all(isinstance(t, TeamCreate) for t in team_creates)
        print(f"✓ Mapped {len(team_creates)} teams")
        
        # Test players mapping
        players_df = mock_nfl_client.fetch_players()
        player_creates = data_mapper.map_players_data(players_df)
        assert len(player_creates) == 3
        assert all(isinstance(p, PlayerCreate) for p in player_creates)
        print(f"✓ Mapped {len(player_creates)} players")
        
        # Test games mapping
        games_df = mock_nfl_client.fetch_games()
        game_creates = data_mapper.map_games_data(games_df)
        assert len(game_creates) == 2
        assert all(isinstance(g, GameCreate) for g in game_creates)
        print(f"✓ Mapped {len(game_creates)} games")
        
        # Test plays mapping
        plays_df = mock_nfl_client.fetch_plays()
        play_batches = data_mapper.map_plays_data(plays_df, batch_size=2)
        total_plays = sum(len(batch) for batch in play_batches)
        assert total_plays == 3
        print(f"✓ Mapped {total_plays} plays in {len(play_batches)} batches")
        
        print("3. Testing data loading...")
        
        # Load teams
        teams_result = data_loader.load_teams()
        assert teams_result.success
        print(f"✓ Loaded teams: {teams_result.records_inserted} inserted, {teams_result.records_updated} updated")
        
        # Load games
        games_result = data_loader.load_games([2023])
        assert games_result.success
        print(f"✓ Loaded games: {games_result.records_inserted} inserted, {games_result.records_updated} updated")
        
        # Load players
        players_result = data_loader.load_players([2023])
        assert players_result.success
        print(f"✓ Loaded players: {players_result.records_inserted} inserted, {players_result.records_updated} updated")
        
        # Load plays
        plays_result = data_loader.load_plays([2023], batch_size=2)
        assert plays_result.success
        print(f"✓ Loaded plays: {plays_result.records_inserted} inserted, {plays_result.records_updated} updated")
        
        print("4. Testing full dataset load...")
        full_results = data_loader.load_full_dataset([2023], include_plays=True)
        
        assert all(result.success for result in full_results.values())
        total_inserted = sum(r.records_inserted for r in full_results.values())
        total_updated = sum(r.records_updated for r in full_results.values())
        print(f"✓ Full dataset load: {total_inserted} total inserted, {total_updated} total updated")
        
        print("5. Testing load status...")
        status = data_loader.get_load_status()
        assert status['teams_count'] == 3
        assert status['games_count'] == 2
        assert status['players_count'] == 3
        assert status['plays_count'] == 3
        assert status['available_seasons'] == [2023]
        print(f"✓ Load status: {status}")
        
        print("6. Testing data validation...")
        
        # Verify teams data
        session = db_manager.get_session()
        try:
            from src.models.team import TeamModel
            sf_team = session.query(TeamModel).filter(TeamModel.team_abbr == 'SF').first()
            assert sf_team is not None
            assert sf_team.team_name == 'San Francisco'
            assert sf_team.team_nick == '49ers'
            assert sf_team.team_conf == 'NFC'
            assert sf_team.team_division == 'West'
            print("✓ Teams data validated")
            
            # Verify games data
            from src.models.game import GameModel
            sf_kc_game = session.query(GameModel).filter(GameModel.game_id == '2023_01_SF_KC').first()
            assert sf_kc_game is not None
            assert sf_kc_game.home_team == 'KC'
            assert sf_kc_game.away_team == 'SF'
            assert sf_kc_game.home_score == 24
            assert sf_kc_game.away_score == 21
            print("✓ Games data validated")
            
            # Verify players data
            from src.models.player import PlayerModel
            mahomes = session.query(PlayerModel).filter(PlayerModel.full_name.like('%Mahomes%')).first()
            assert mahomes is not None
            assert mahomes.team_abbr == 'KC'
            assert mahomes.position == 'QB'
            assert mahomes.jersey_number == 15
            print("✓ Players data validated")
            
            # Verify plays data
            from src.models.play import PlayModel
            plays = session.query(PlayModel).filter(PlayModel.game_id == '2023_01_SF_KC').all()
            assert len(plays) == 3
            pass_plays = [p for p in plays if p.play_type == 'pass']
            assert len(pass_plays) == 2
            print("✓ Plays data validated")
            
        finally:
            session.close()
        
        print("\n🎉 All data integration tests passed!")
        print(f"Successfully processed:")
        print(f"  - {status['teams_count']} teams")
        print(f"  - {status['games_count']} games")
        print(f"  - {status['players_count']} players")
        print(f"  - {status['plays_count']} plays")
        
        return True
        
    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return False
        
    finally:
        # Cleanup
        try:
            engine.dispose()
            os.unlink(temp_db.name)
        except:
            pass


if __name__ == "__main__":
    success = test_data_integration()
    exit(0 if success else 1)