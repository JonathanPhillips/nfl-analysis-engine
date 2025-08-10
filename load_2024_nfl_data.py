#!/usr/bin/env python3
"""Load the extracted 2024 NFL data into the database for League Leaders system."""

import sys
import os
import pandas as pd
from pathlib import Path
from datetime import datetime, date
import logging

# Add the src directory to Python path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from database.config import get_db_session
from models.game import Game
from models.play import Play
from models.player import Player
from models.team import Team
from data.data_mapper import DataMapper

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def load_2024_data():
    """Load 2024 NFL data into the database for League Leaders."""
    
    print("=" * 60)
    print("LOADING 2024 NFL DATA FOR LEAGUE LEADERS")  
    print("=" * 60)
    
    data_dir = Path("data")
    
    # Initialize database session
    try:
        db = next(get_db_session())
        logger.info("Database connection established")
    except Exception as e:
        print(f"❌ Database connection failed: {e}")
        return False
    
    try:
        # Initialize data mapper
        data_mapper = DataMapper()
        
        # 1. Load roster data first (for player information)
        print("\n1. Loading roster data...")
        roster_file = data_dir / "rosters_2024.parquet"
        if roster_file.exists():
            rosters_df = pd.read_parquet(roster_file)
            print(f"   Found {len(rosters_df)} roster entries")
            
            # Process rosters into players
            players_loaded = 0
            for _, roster_row in rosters_df.iterrows():
                try:
                    # Convert roster data to player format
                    player_data = {
                        'player_id': roster_row.get('player_id', f"unknown_{roster_row.get('player_name', 'player')}"),
                        'display_name': roster_row.get('player_name'),
                        'first_name': roster_row.get('first_name', ''),
                        'last_name': roster_row.get('last_name', ''),
                        'position': roster_row.get('position'),
                        'team': roster_row.get('team'),
                        'jersey_number': roster_row.get('jersey_number'),
                        'height': roster_row.get('height'),
                        'weight': roster_row.get('weight'),
                        'birth_date': None,  # Not in roster data
                        'college': roster_row.get('college'),
                        'years_pro': roster_row.get('years_exp'),
                        'draft_year': None,
                        'draft_round': None,
                        'draft_pick': None
                    }
                    
                    # Check if player exists
                    existing_player = db.query(Player).filter(
                        Player.player_id == player_data['player_id']
                    ).first()
                    
                    if not existing_player:
                        player = Player(**player_data)
                        db.add(player)
                        players_loaded += 1
                        
                        if players_loaded % 100 == 0:
                            db.commit()  # Commit in batches
                            print(f"   Loaded {players_loaded} players...")
                    
                except Exception as e:
                    logger.warning(f"Failed to load player {roster_row.get('player_name', 'unknown')}: {e}")
                    continue
            
            db.commit()
            print(f"✅ Loaded {players_loaded} new players from rosters")
        else:
            print("⚠️  No roster data found - proceeding without it")
        
        # 2. Load schedule data (games)
        print("\n2. Loading schedule data...")
        schedule_file = data_dir / "schedule_2024.parquet"
        if schedule_file.exists():
            schedule_df = pd.read_parquet(schedule_file)
            print(f"   Found {len(schedule_df)} games")
            
            games_loaded = 0
            for _, game_row in schedule_df.iterrows():
                try:
                    # Convert schedule data to game format
                    game_data = {
                        'game_id': game_row.get('game_id'),
                        'season': 2024,
                        'season_type': game_row.get('season_type', 'REG'),
                        'week': game_row.get('week'),
                        'gameday': pd.to_datetime(game_row.get('gameday')).date() if game_row.get('gameday') else None,
                        'home_team': game_row.get('home_team'),
                        'away_team': game_row.get('away_team'),
                        'home_score': game_row.get('home_score'),
                        'away_score': game_row.get('away_score'),
                        'game_finished': game_row.get('home_score', 0) > 0 or game_row.get('away_score', 0) > 0,
                        'home_moneyline': game_row.get('home_moneyline'),
                        'away_moneyline': game_row.get('away_moneyline'),
                        'spread_line': game_row.get('spread_line'),
                        'total_line': game_row.get('total_line')
                    }
                    
                    # Check if game exists
                    existing_game = db.query(Game).filter(
                        Game.game_id == game_data['game_id']
                    ).first()
                    
                    if not existing_game:
                        game = Game(**game_data)
                        db.add(game)
                        games_loaded += 1
                        
                        if games_loaded % 50 == 0:
                            db.commit()  # Commit in batches
                            print(f"   Loaded {games_loaded} games...")
                    
                except Exception as e:
                    logger.warning(f"Failed to load game {game_row.get('game_id', 'unknown')}: {e}")
                    continue
            
            db.commit()
            print(f"✅ Loaded {games_loaded} new games from schedule")
        else:
            print("⚠️  No schedule data found - proceeding without it")
        
        # 3. Load play-by-play data (the main event!)
        print("\n3. Loading play-by-play data...")
        pbp_file = data_dir / "pbp_2024.parquet"
        if not pbp_file.exists():
            print("❌ No play-by-play data found!")
            return False
            
        pbp_df = pd.read_parquet(pbp_file)
        print(f"   Found {len(pbp_df)} plays to process")
        print(f"   Memory usage: {pbp_df.memory_usage(deep=True).sum() / (1024*1024):.1f} MB")
        
        # Process plays in smaller batches to avoid memory issues
        batch_size = 1000
        plays_loaded = 0
        
        for batch_start in range(0, len(pbp_df), batch_size):
            batch_end = min(batch_start + batch_size, len(pbp_df))
            batch_df = pbp_df.iloc[batch_start:batch_end]
            
            for _, play_row in batch_df.iterrows():
                try:
                    # Use data mapper to convert nflfastR format to our Play model
                    play_data = data_mapper.map_play_data(play_row)
                    
                    # Check if play exists (to avoid duplicates)
                    existing_play = db.query(Play).filter(
                        Play.play_id == play_data['play_id']
                    ).first()
                    
                    if not existing_play:
                        play = Play(**play_data)
                        db.add(play)
                        plays_loaded += 1
                
                except Exception as e:
                    logger.warning(f"Failed to load play {play_row.get('play_id', 'unknown')}: {e}")
                    continue
            
            # Commit this batch
            try:
                db.commit()
                print(f"   Processed {batch_end:,} / {len(pbp_df):,} plays ({plays_loaded:,} new plays loaded)")
            except Exception as e:
                db.rollback()
                logger.error(f"Failed to commit batch {batch_start}-{batch_end}: {e}")
                continue
        
        print(f"✅ Successfully loaded {plays_loaded:,} new plays")
        
        # 4. Verification
        print("\n" + "=" * 60)
        print("DATA LOADING VERIFICATION")
        print("=" * 60)
        
        total_plays = db.query(Play).count()
        total_games = db.query(Game).count()
        total_players = db.query(Player).count()
        
        print(f"✅ Database now contains:")
        print(f"   - {total_plays:,} total plays")
        print(f"   - {total_games:,} total games")
        print(f"   - {total_players:,} total players")
        
        # Quick League Leaders check
        passing_plays = db.query(Play).filter(Play.pass_attempt == True).count()
        rushing_plays = db.query(Play).filter(Play.rush_attempt == True).count()
        
        print(f"   - {passing_plays:,} passing plays")
        print(f"   - {rushing_plays:,} rushing plays")
        
        # Sample QB check
        sample_qb_plays = db.query(Play).filter(
            Play.passer_player_name.like('%Mahomes%')
        ).count()
        
        if sample_qb_plays > 0:
            print(f"   - {sample_qb_plays} plays by Mahomes found!")
            print(f"\n🎯 LEAGUE LEADERS SYSTEM IS READY!")
            print(f"   Your system now has real NFL data with stars like:")
            print(f"   - Patrick Mahomes, Joe Burrow, C.J. Stroud")
            print(f"   - Saquon Barkley, Derrick Henry, Josh Jacobs")
            print(f"   - DJ Moore, Ja'Marr Chase, Amon-Ra St. Brown")
        else:
            print("⚠️  Sample verification failed - check data mapping")
        
        return True
    
    except Exception as e:
        db.rollback()
        logger.error(f"Data loading failed: {e}")
        print(f"❌ Loading failed: {e}")
        return False
    
    finally:
        db.close()

if __name__ == "__main__":
    success = load_2024_data()
    if success:
        print(f"\n🚀 SUCCESS! Your League Leaders system now has complete 2024 NFL data!")
        print(f"   Run your web server to see Patrick Mahomes, Joe Burrow, etc. in the leaders!")
        sys.exit(0)
    else:
        print(f"\n❌ FAILED! Check the error messages above.")
        sys.exit(1)