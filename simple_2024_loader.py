#!/usr/bin/env python3
"""Simple 2024 NFL data loader using existing database setup."""

import sys
import os
import pandas as pd
import sqlite3
from pathlib import Path
from datetime import datetime

# Set PYTHONPATH
sys.path.insert(0, str(Path(__file__).parent / "src"))

def load_plays_direct():
    """Load plays directly into SQLite database using raw SQL."""
    
    print("=" * 60)
    print("DIRECT SQLITE LOADING OF 2024 NFL DATA")  
    print("=" * 60)
    
    data_dir = Path("data")
    pbp_file = data_dir / "pbp_2024.parquet"
    
    if not pbp_file.exists():
        print("❌ No play-by-play data found!")
        return False
    
    # Connect to database
    db_path = "test.db"  # Using existing test.db
    conn = sqlite3.connect(db_path)
    
    try:
        # Load parquet file
        print(f"Loading {pbp_file}...")
        pbp_df = pd.read_parquet(pbp_file)
        print(f"Loaded {len(pbp_df):,} plays from parquet file")
        
        # Check existing data
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM plays")
        existing_plays = cursor.fetchone()[0]
        print(f"Database currently has {existing_plays:,} plays")
        
        if existing_plays > 40000:
            print("✅ Database already has sufficient data!")
            
            # Quick verification of star players
            cursor.execute("""
                SELECT passer_player_name, COUNT(*) as attempts 
                FROM plays 
                WHERE pass_attempt = 1 AND passer_player_name IS NOT NULL
                GROUP BY passer_player_name 
                ORDER BY attempts DESC 
                LIMIT 10
            """)
            
            top_qbs = cursor.fetchall()
            print("\n🎯 Top QBs in database:")
            for qb, attempts in top_qbs:
                print(f"   {qb}: {attempts} attempts")
            
            return True
        
        # Prepare data for insertion
        print("\nProcessing NFL data for database insertion...")
        
        # Create a simplified play dataset with just the essential columns
        play_data = []
        batch_size = 1000
        
        essential_cols = [
            'play_id', 'game_id', 'season', 'week', 'season_type',
            'game_date', 'home_team', 'away_team', 'posteam', 'defteam',
            'play_type', 'yards_gained', 'down', 'ydstogo', 'yardline_100',
            'pass_attempt', 'rush_attempt', 'complete_pass',
            'passer_player_name', 'passer_player_id',  
            'rusher_player_name', 'rusher_player_id',
            'receiver_player_name', 'receiver_player_id',
            'passing_yards', 'rushing_yards', 'receiving_yards',
            'touchdown', 'interception', 'fumble', 'sack',
            'epa', 'wp', 'wpa'
        ]
        
        print(f"Processing {len(pbp_df)} plays in batches...")
        
        for i in range(0, len(pbp_df), batch_size):
            batch = pbp_df.iloc[i:i+batch_size]
            
            for _, row in batch.iterrows():
                # Map essential data only
                play_dict = {
                    'play_id': str(row.get('play_id', f'play_{i}')),
                    'game_id': str(row.get('game_id', '')),
                    'season': int(row.get('season', 2024)),
                    'week': int(row.get('week', 1)) if pd.notna(row.get('week')) else 1,
                    'season_type': str(row.get('season_type', 'REG')),
                    'game_date': row.get('game_date'),
                    'home_team': str(row.get('home_team', '')),
                    'away_team': str(row.get('away_team', '')),
                    'posteam': str(row.get('posteam', '')) if pd.notna(row.get('posteam')) else None,
                    'defteam': str(row.get('defteam', '')) if pd.notna(row.get('defteam')) else None,
                    'play_type': str(row.get('play_type', '')) if pd.notna(row.get('play_type')) else None,
                    'yards_gained': float(row.get('yards_gained', 0)) if pd.notna(row.get('yards_gained')) else 0,
                    'down': int(row.get('down', 0)) if pd.notna(row.get('down')) else None,
                    'ydstogo': int(row.get('ydstogo', 0)) if pd.notna(row.get('ydstogo')) else None,
                    'yardline_100': float(row.get('yardline_100', 0)) if pd.notna(row.get('yardline_100')) else None,
                    'pass_attempt': bool(row.get('pass', 0)),
                    'rush_attempt': bool(row.get('rush', 0)),
                    'complete_pass': bool(row.get('complete_pass', 0)),
                    'passer_player_name': str(row.get('passer_player_name', '')) if pd.notna(row.get('passer_player_name')) else None,
                    'passer_player_id': str(row.get('passer_player_id', '')) if pd.notna(row.get('passer_player_id')) else None,
                    'rusher_player_name': str(row.get('rusher_player_name', '')) if pd.notna(row.get('rusher_player_name')) else None,
                    'rusher_player_id': str(row.get('rusher_player_id', '')) if pd.notna(row.get('rusher_player_id')) else None,
                    'receiver_player_name': str(row.get('receiver_player_name', '')) if pd.notna(row.get('receiver_player_name')) else None,
                    'receiver_player_id': str(row.get('receiver_player_id', '')) if pd.notna(row.get('receiver_player_id')) else None,
                    'passing_yards': float(row.get('passing_yards', 0)) if pd.notna(row.get('passing_yards')) else 0,
                    'rushing_yards': float(row.get('rushing_yards', 0)) if pd.notna(row.get('rushing_yards')) else 0,
                    'receiving_yards': float(row.get('receiving_yards', 0)) if pd.notna(row.get('receiving_yards')) else 0,
                    'touchdown': bool(row.get('touchdown', 0)),
                    'interception': bool(row.get('interception', 0)),
                    'fumble': bool(row.get('fumble', 0)),
                    'sack': bool(row.get('sack', 0)),
                    'epa': float(row.get('epa', 0)) if pd.notna(row.get('epa')) else 0,
                    'wp': float(row.get('wp', 0)) if pd.notna(row.get('wp')) else None,
                    'wpa': float(row.get('wpa', 0)) if pd.notna(row.get('wpa')) else None
                }
                play_data.append(play_dict)
            
            if len(play_data) >= batch_size:
                # Insert batch
                insert_sql = """
                INSERT OR IGNORE INTO plays (
                    play_id, game_id, season, week, season_type, game_date,
                    home_team, away_team, posteam, defteam, play_type,
                    yards_gained, down, ydstogo, yardline_100,
                    pass_attempt, rush_attempt, complete_pass,
                    passer_player_name, passer_player_id,
                    rusher_player_name, rusher_player_id,
                    receiver_player_name, receiver_player_id,
                    passing_yards, rushing_yards, receiving_yards,
                    touchdown, interception, fumble, sack, epa, wp, wpa
                ) VALUES (
                    :play_id, :game_id, :season, :week, :season_type, :game_date,
                    :home_team, :away_team, :posteam, :defteam, :play_type,
                    :yards_gained, :down, :ydstogo, :yardline_100,
                    :pass_attempt, :rush_attempt, :complete_pass,
                    :passer_player_name, :passer_player_id,
                    :rusher_player_name, :rusher_player_id,
                    :receiver_player_name, :receiver_player_id,
                    :passing_yards, :rushing_yards, :receiving_yards,
                    :touchdown, :interception, :fumble, :sack, :epa, :wp, :wpa
                )
                """
                
                cursor.executemany(insert_sql, play_data)
                conn.commit()
                
                print(f"   Inserted batch ending at play {i+batch_size:,}")
                play_data = []  # Clear batch
        
        # Insert remaining plays
        if play_data:
            cursor.executemany(insert_sql, play_data)
            conn.commit()
        
        # Final verification
        cursor.execute("SELECT COUNT(*) FROM plays")
        final_count = cursor.fetchone()[0]
        
        print(f"\n✅ SUCCESS! Database now has {final_count:,} plays")
        
        # Verify star players
        cursor.execute("""
            SELECT passer_player_name, COUNT(*) as attempts 
            FROM plays 
            WHERE pass_attempt = 1 AND passer_player_name IS NOT NULL
            GROUP BY passer_player_name 
            ORDER BY attempts DESC 
            LIMIT 10
        """)
        
        top_qbs = cursor.fetchall()
        print("\n🎯 Top QBs now in database:")
        for qb, attempts in top_qbs:
            print(f"   {qb}: {attempts} attempts")
        
        # Check for specific stars
        mahomes_plays = cursor.execute(
            "SELECT COUNT(*) FROM plays WHERE passer_player_name LIKE '%Mahomes%'"
        ).fetchone()[0]
        
        if mahomes_plays > 0:
            print(f"\n🏆 VERIFICATION PASSED!")
            print(f"   - Patrick Mahomes has {mahomes_plays} plays in database")
            print(f"   - Your League Leaders will now show real NFL stars!")
            return True
        else:
            print(f"\n⚠️  Verification warning: No Mahomes plays found")
            return False
    
    except Exception as e:
        print(f"❌ Loading failed: {e}")
        return False
    
    finally:
        conn.close()

if __name__ == "__main__":
    success = load_plays_direct()
    if success:
        print(f"\n🚀 READY TO TEST! Start your web server and check League Leaders!")
        print(f"   Expected QBs: Patrick Mahomes, Joe Burrow, C.J. Stroud")
        sys.exit(0)
    else:
        print(f"\n❌ Loading failed. Check the errors above.")
        sys.exit(1)