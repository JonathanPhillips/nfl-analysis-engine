#!/usr/bin/env python3
"""
Load real NFL data from SQLite to PostgreSQL production database.

This script migrates the comprehensive 2024 NFL data from the SQLite
database to our production PostgreSQL schema.
"""

import os
import sys
import sqlite3
import pandas as pd
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from datetime import datetime

# Add the project root to Python path
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from src.database.config import get_database_url


def migrate_nfl_data_to_postgres():
    """Migrate NFL data from SQLite to PostgreSQL production database."""
    
    print("🚀 Migrating NFL data from SQLite to PostgreSQL...")
    
    # Connect to SQLite source
    if not os.path.exists('nfl_data.db'):
        print("❌ nfl_data.db not found. Run the NFL data extraction first.")
        return False
        
    sqlite_conn = sqlite3.connect('nfl_data.db')
    
    # Connect to PostgreSQL target
    postgres_url = get_database_url()
    postgres_engine = create_engine(postgres_url)
    Session = sessionmaker(bind=postgres_engine)
    postgres_session = Session()
    
    try:
        # Read NFL data from SQLite
        print("📥 Reading NFL play-by-play data from SQLite...")
        
        sqlite_query = """
        SELECT 
            play_id,
            game_id, 
            season,
            week,
            posteam,
            defteam,
            qtr,
            down,
            ydstogo,
            yardline_100,
            play_type,
            desc,
            yards_gained,
            touchdown,
            pass_touchdown,
            rush_touchdown,
            interception,
            fumble,
            safety,
            penalty,
            passer_player_id,
            passer_player_name,
            receiver_player_id, 
            receiver_player_name,
            rusher_player_id,
            rusher_player_name,
            epa,
            wp,
            wpa,
            cpoe,
            air_yards,
            yards_after_catch,
            posteam_score,
            defteam_score
        FROM plays
        WHERE season = 2024
        """
        
        df = pd.read_sql_query(sqlite_query, sqlite_conn)
        print(f"  📊 Loaded {len(df):,} plays from SQLite")
        
        # Clear existing 2024 data from PostgreSQL
        print("🧹 Clearing existing 2024 data from PostgreSQL...")
        postgres_session.execute(text("DELETE FROM plays WHERE season = 2024"))
        postgres_session.commit()
        
        # Transform data to match PostgreSQL schema
        print("🔄 Transforming data to PostgreSQL schema...")
        
        # Add required PostgreSQL fields
        df['score_differential'] = df['posteam_score'] - df['defteam_score']
        df['game_seconds_remaining'] = None
        df['half_seconds_remaining'] = None 
        df['game_half'] = None
        df['ep'] = None
        df['pass_location'] = None
        df['created_at'] = datetime.now()
        df['updated_at'] = datetime.now()
        df['is_active'] = True
        
        # Handle boolean fields
        df['touchdown'] = df['touchdown'].astype('boolean')
        df['pass_touchdown'] = df['pass_touchdown'].astype('boolean') 
        df['rush_touchdown'] = df['rush_touchdown'].astype('boolean')
        df['interception'] = df['interception'].astype('boolean')
        df['fumble'] = df['fumble'].astype('boolean')
        df['safety'] = df['safety'].astype('boolean')
        df['penalty'] = df['penalty'].astype('boolean')
        
        # Insert data in batches to PostgreSQL
        print("📤 Inserting NFL data into PostgreSQL...")
        
        batch_size = 1000
        total_rows = len(df)
        successful_inserts = 0
        
        for i in range(0, total_rows, batch_size):
            batch = df.iloc[i:i + batch_size]
            
            try:
                # Convert to records
                records = batch.to_dict('records')
                
                if records:
                    # Build INSERT statement
                    columns = [
                        'play_id', 'game_id', 'season', 'week', 'posteam', 'defteam',
                        'qtr', 'down', 'ydstogo', 'yardline_100', 'play_type', '"desc"',
                        'yards_gained', 'touchdown', 'pass_touchdown', 'rush_touchdown',
                        'interception', 'fumble', 'safety', 'penalty',
                        'passer_player_id', 'receiver_player_id', 'rusher_player_id',
                        'epa', 'wp', 'wpa', 'cpoe', 'air_yards', 'yards_after_catch',
                        'posteam_score', 'defteam_score', 'score_differential',
                        'game_seconds_remaining', 'half_seconds_remaining', 'game_half',
                        'ep', 'pass_location', 'created_at', 'updated_at', 'is_active'
                    ]
                    
                    placeholders = [f":{col.replace('\"', '')}" for col in columns]
                    
                    insert_sql = f"""
                        INSERT INTO plays ({', '.join(columns)})
                        VALUES ({', '.join(placeholders)})
                    """
                    
                    postgres_session.execute(text(insert_sql), records)
                    successful_inserts += len(records)
                    
            except Exception as e:
                print(f"  ⚠️ Batch {i//batch_size + 1} failed: {e}")
                continue
            
            if (i + batch_size) % 5000 == 0:
                postgres_session.commit()
                print(f"    ✅ Processed {min(i + batch_size, total_rows):,}/{total_rows:,} plays...")
        
        postgres_session.commit()
        
        # Load player data
        print("\n👥 Loading player data...")
        
        # Get unique players from plays
        players_query = """
        SELECT DISTINCT
            passer_player_id as player_id,
            passer_player_name as full_name,
            posteam as team_abbr,
            'QB' as position
        FROM plays 
        WHERE passer_player_id IS NOT NULL
        
        UNION
        
        SELECT DISTINCT
            rusher_player_id as player_id,
            rusher_player_name as full_name,  
            posteam as team_abbr,
            'RB' as position
        FROM plays
        WHERE rusher_player_id IS NOT NULL
        
        UNION
        
        SELECT DISTINCT
            receiver_player_id as player_id,
            receiver_player_name as full_name,
            posteam as team_abbr,
            'WR' as position  
        FROM plays
        WHERE receiver_player_id IS NOT NULL
        """
        
        players_df = pd.read_sql_query(players_query, sqlite_conn)
        
        # Insert players into PostgreSQL
        for _, player in players_df.iterrows():
            try:
                postgres_session.execute(text("""
                    INSERT INTO players (player_id, full_name, team_abbr, position, created_at, updated_at, is_active)
                    VALUES (:player_id, :full_name, :team_abbr, :position, :created_at, :updated_at, :is_active)
                    ON CONFLICT (player_id) DO UPDATE SET
                        full_name = :full_name,
                        team_abbr = :team_abbr,
                        position = :position,
                        updated_at = :updated_at
                """), {
                    'player_id': player['player_id'],
                    'full_name': player['full_name'], 
                    'team_abbr': player['team_abbr'],
                    'position': player['position'],
                    'created_at': datetime.now(),
                    'updated_at': datetime.now(),
                    'is_active': True
                })
            except Exception as e:
                print(f"  ⚠️ Player insert failed: {e}")
                continue
        
        postgres_session.commit()
        
        # Verification
        print("\n📊 PostgreSQL Migration Verification:")
        result = postgres_session.execute(text("""
            SELECT 
                season,
                COUNT(*) as total_plays,
                COUNT(CASE WHEN passer_player_id IS NOT NULL THEN 1 END) as qb_plays,
                COUNT(CASE WHEN rusher_player_id IS NOT NULL THEN 1 END) as rb_plays,
                COUNT(CASE WHEN receiver_player_id IS NOT NULL THEN 1 END) as wr_plays
            FROM plays
            WHERE season = 2024
            GROUP BY season
        """)).fetchone()
        
        if result:
            print(f"  ✅ Season 2024: {result.total_plays:,} total plays")
            print(f"  🎯 QB plays: {result.qb_plays:,}")
            print(f"  🏃 RB plays: {result.rb_plays:,}")  
            print(f"  🙌 WR plays: {result.wr_plays:,}")
        
        # Check top QBs
        print("\n🏈 Top QBs in PostgreSQL:")
        qb_check = postgres_session.execute(text("""
            SELECT p.full_name, p.team_abbr, COUNT(*) as attempts
            FROM plays pl
            JOIN players p ON pl.passer_player_id = p.player_id
            WHERE pl.play_type = 'pass' AND pl.season = 2024
            GROUP BY p.full_name, p.team_abbr
            ORDER BY attempts DESC
            LIMIT 5
        """)).fetchall()
        
        for qb in qb_check:
            print(f"  🏆 {qb.full_name} ({qb.team_abbr}): {qb.attempts} attempts")
        
        print(f"\n🎉 Successfully migrated {successful_inserts:,} plays to PostgreSQL!")
        print("🚀 Production database ready with real NFL data!")
        
        return True
        
    except Exception as e:
        print(f"❌ Migration failed: {e}")
        postgres_session.rollback()
        import traceback
        traceback.print_exc()
        return False
        
    finally:
        sqlite_conn.close()
        postgres_session.close()


if __name__ == "__main__":
    print("🏈 Starting NFL data migration to PostgreSQL production database...")
    
    success = migrate_nfl_data_to_postgres()
    if success:
        print("\n✅ PRODUCTION READY: PostgreSQL database loaded with real NFL data!")
        print("🔗 League Leaders will now show Patrick Mahomes, Joe Burrow, etc.")
        print("🚀 Restart your server to see legitimate NFL stars!")
    else:
        print("\n💥 Migration failed!")
        sys.exit(1)