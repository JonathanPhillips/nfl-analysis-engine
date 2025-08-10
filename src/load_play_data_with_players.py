#!/usr/bin/env python3
"""
Load play-by-play data with player IDs for league leaders functionality.

This script loads play-by-play data from nfl_data_py including player IDs
for passers, receivers, and rushers to enable player statistics calculation.
"""

import os
import sys
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
import pandas as pd
import nfl_data_py as nfl

# Add the src directory to Python path
sys.path.insert(0, os.path.dirname(__file__))

from database.config import get_database_url

def load_play_data_with_players():
    """Load play-by-play data with player IDs."""
    
    # Get database connection
    database_url = get_database_url()
    engine = create_engine(database_url)
    Session = sessionmaker(bind=engine)
    session = Session()
    
    try:
        print("📅 Loading play-by-play data with player IDs...")
        
        # Load data for 2023 and 2024 seasons
        seasons = [2023, 2024]
        
        for season in seasons:
            print(f"\n🏈 Processing {season} season...")
            
            # Load play-by-play data from nfl_data_py
            print(f"  📥 Fetching play-by-play data...")
            pbp_data = nfl.import_pbp_data([season])
            
            if pbp_data.empty:
                print(f"  ⚠️ No play-by-play data found for {season}")
                continue
            
            # Filter to relevant columns for our analysis
            relevant_columns = [
                'play_id', 'game_id', 'season', 'week', 'posteam', 'defteam',
                'play_type', 'yards_gained', 'touchdown', 'pass_touchdown', 'rush_touchdown',
                'interception', 'fumble', 'safety', 'penalty',
                'passer_player_id', 'passer_player_name',
                'receiver_player_id', 'receiver_player_name',
                'rusher_player_id', 'rusher_player_name',
                'epa', 'wp', 'wpa', 'desc', 'qtr', 'down', 'ydstogo', 'yardline_100',
                'game_seconds_remaining', 'half_seconds_remaining', 'game_half',
                'posteam_score', 'defteam_score', 'score_differential',
                'cpoe', 'pass_location', 'air_yards', 'yards_after_catch'
            ]
            
            # Keep only columns that exist
            available_columns = [col for col in relevant_columns if col in pbp_data.columns]
            pbp_filtered = pbp_data[available_columns].copy()
            
            print(f"  📊 Found {len(pbp_filtered):,} plays")
            
            # Filter to regular plays (not kickoffs, timeouts, etc.)
            regular_plays = pbp_filtered[
                pbp_filtered['play_type'].isin(['pass', 'run', 'punt', 'field_goal', 'qb_kneel', 'qb_spike'])
            ].copy()
            
            print(f"  🎯 Filtered to {len(regular_plays):,} regular plays")
            
            # Check player ID coverage
            pass_plays = regular_plays[regular_plays['play_type'] == 'pass']
            run_plays = regular_plays[regular_plays['play_type'] == 'run']
            
            passer_coverage = pass_plays['passer_player_id'].notna().sum() / len(pass_plays) * 100 if len(pass_plays) > 0 else 0
            rusher_coverage = run_plays['rusher_player_id'].notna().sum() / len(run_plays) * 100 if len(run_plays) > 0 else 0
            
            print(f"  👤 Player ID coverage:")
            print(f"     Passers: {passer_coverage:.1f}%")
            print(f"     Rushers: {rusher_coverage:.1f}%")
            
            # Update existing plays with player IDs
            batch_size = 500
            updated_count = 0
            
            for i in range(0, len(regular_plays), batch_size):
                batch = regular_plays.iloc[i:i + batch_size]
                
                for _, play in batch.iterrows():
                    # Build update query
                    update_fields = []
                    
                    if pd.notna(play.get('passer_player_id')):
                        update_fields.append(f"passer_player_id = '{play['passer_player_id']}'")
                    if pd.notna(play.get('receiver_player_id')):
                        update_fields.append(f"receiver_player_id = '{play['receiver_player_id']}'")
                    if pd.notna(play.get('rusher_player_id')):
                        update_fields.append(f"rusher_player_id = '{play['rusher_player_id']}'")
                    
                    # Update EPA/WPA if available
                    if pd.notna(play.get('epa')):
                        update_fields.append(f"epa = {play['epa']}")
                    if pd.notna(play.get('wpa')):
                        update_fields.append(f"wpa = {play['wpa']}")
                    if pd.notna(play.get('wp')):
                        update_fields.append(f"wp = {play['wp']}")
                    
                    if update_fields:
                        update_query = text(f"""
                            UPDATE plays 
                            SET {', '.join(update_fields)}
                            WHERE game_id = :game_id 
                            AND play_id = :play_id
                        """)
                        
                        # Convert play_id to string to match database varchar type
                        play_id_str = str(int(play['play_id'])) if pd.notna(play['play_id']) else str(play['play_id'])
                        
                        result = session.execute(update_query, {
                            'game_id': play['game_id'],
                            'play_id': play_id_str
                        })
                        
                        if result.rowcount > 0:
                            updated_count += 1
                
                if (i + batch_size) % 2000 == 0:
                    session.commit()
                    print(f"    Updated {updated_count} plays...")
            
            session.commit()
            print(f"  ✅ Updated {updated_count} plays with player IDs for {season}")
        
        # Verify the update
        print("\n📊 Verification:")
        result = session.execute(text("""
            SELECT 
                COUNT(*) as total_plays,
                COUNT(passer_player_id) as plays_with_passer,
                COUNT(receiver_player_id) as plays_with_receiver,
                COUNT(rusher_player_id) as plays_with_rusher
            FROM plays
            WHERE play_type IN ('pass', 'run')
        """))
        
        row = result.fetchone()
        print(f"  Total plays: {row.total_plays:,}")
        print(f"  Plays with passer ID: {row.plays_with_passer:,}")
        print(f"  Plays with receiver ID: {row.plays_with_receiver:,}")
        print(f"  Plays with rusher ID: {row.plays_with_rusher:,}")
        
        return True
        
    except Exception as e:
        print(f"❌ Error loading play data: {e}")
        session.rollback()
        import traceback
        traceback.print_exc()
        return False
        
    finally:
        session.close()

if __name__ == "__main__":
    print("🚀 Starting play-by-play data update with player IDs...")
    
    success = load_play_data_with_players()
    if success:
        print("\n🎉 Play data update completed successfully!")
        print("🏆 League leaders functionality should now work!")
    else:
        print("\n💥 Play data update failed!")
        sys.exit(1)