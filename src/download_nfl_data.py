#!/usr/bin/env python3
"""
Download NFL play-by-play data directly from nflfastR repository.

This bypasses nfl_data_py installation issues by downloading parquet files
directly from the public nflfastR data repository.
"""

import os
import sys
import requests
import pandas as pd
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from datetime import datetime

# Add the project root to Python path
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from src.database.config import get_database_url


def download_nfl_pbp_data(seasons=[2023, 2024]):
    """Download NFL play-by-play data from nflfastR repository."""
    
    print("🏈 Downloading NFL play-by-play data from nflfastR...")
    
    # Create data directory
    os.makedirs('data', exist_ok=True)
    
    for season in seasons:
        print(f"\n📅 Downloading {season} season data...")
        
        # Try multiple nflfastR data URLs
        urls = [
            f"https://github.com/nflverse/nfldata/releases/download/pbp/play_by_play_{season}.parquet",
            f"https://github.com/nflverse/nfldata/raw/master/data/play_by_play/play_by_play_{season}.parquet",
            f"https://raw.githubusercontent.com/nflverse/nfldata/master/data/play_by_play_{season}.parquet"
        ]
        
        try:
            response = requests.get(url, stream=True)
            response.raise_for_status()
            
            filename = f"data/play_by_play_{season}.parquet"
            
            with open(filename, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    f.write(chunk)
            
            # Check file size
            size_mb = os.path.getsize(filename) / (1024 * 1024)
            print(f"  ✅ Downloaded {filename} ({size_mb:.1f} MB)")
            
            # Quick data check
            df = pd.read_parquet(filename)
            print(f"  📊 Contains {len(df):,} plays")
            
        except Exception as e:
            print(f"  ❌ Failed to download {season} data: {e}")


def load_pbp_to_database(seasons=[2023, 2024]):
    """Load downloaded play-by-play data into database."""
    
    # Get database connection
    database_url = get_database_url()
    engine = create_engine(database_url)
    Session = sessionmaker(bind=engine)
    session = Session()
    
    try:
        print("\n🗄️ Loading play-by-play data into database...")
        
        for season in seasons:
            filename = f"data/play_by_play_{season}.parquet"
            
            if not os.path.exists(filename):
                print(f"  ⚠️ Skipping {season} - file not found")
                continue
                
            print(f"  📥 Processing {season} season...")
            
            # Read parquet file
            df = pd.read_parquet(filename)
            
            # Filter to relevant columns that exist in our database
            relevant_columns = [
                'play_id', 'game_id', 'season', 'week', 'posteam', 'defteam',
                'qtr', 'down', 'ydstogo', 'yardline_100', 'play_type', 'desc',
                'yards_gained', 'touchdown', 'pass_touchdown', 'rush_touchdown',
                'interception', 'fumble', 'safety', 'penalty',
                'passer_player_id', 'passer_player_name',
                'receiver_player_id', 'receiver_player_name', 
                'rusher_player_id', 'rusher_player_name',
                'epa', 'wp', 'wpa', 'cpoe', 'air_yards', 'yards_after_catch'
            ]
            
            # Keep only columns that exist in the dataframe
            available_columns = [col for col in relevant_columns if col in df.columns]
            df_filtered = df[available_columns].copy()
            
            # Remove existing data for this season
            session.execute(text("DELETE FROM plays WHERE season = :season"), {'season': season})
            
            # Insert data in batches
            batch_size = 1000
            total_rows = len(df_filtered)
            
            for i in range(0, total_rows, batch_size):
                batch = df_filtered.iloc[i:i + batch_size]
                
                # Add required fields
                batch = batch.copy()
                batch['created_at'] = datetime.now()
                batch['updated_at'] = datetime.now()
                batch['is_active'] = True
                
                # Convert to records for bulk insert
                records = batch.to_dict('records')
                
                # Build INSERT statement dynamically
                if records:
                    columns = list(records[0].keys())
                    # Handle reserved 'desc' column
                    column_names = [f'"{col}"' if col == 'desc' else col for col in columns]
                    placeholders = [f":{col}" for col in columns]
                    
                    insert_sql = f"""
                        INSERT INTO plays ({', '.join(column_names)})
                        VALUES ({', '.join(placeholders)})
                    """
                    
                    session.execute(text(insert_sql), records)
                
                if (i + batch_size) % 5000 == 0:
                    session.commit()
                    print(f"    Processed {min(i + batch_size, total_rows):,}/{total_rows:,} plays...")
            
            session.commit()
            print(f"  ✅ Loaded {total_rows:,} plays for {season}")
        
        # Verification query
        print("\n📊 Database verification:")
        result = session.execute(text("""
            SELECT 
                season,
                COUNT(*) as total_plays,
                COUNT(CASE WHEN passer_player_id IS NOT NULL THEN 1 END) as qb_plays,
                COUNT(CASE WHEN rusher_player_id IS NOT NULL THEN 1 END) as rb_plays,
                COUNT(CASE WHEN receiver_player_id IS NOT NULL THEN 1 END) as wr_plays
            FROM plays 
            WHERE season IN (2023, 2024)
            GROUP BY season
            ORDER BY season
        """)).fetchall()
        
        for row in result:
            print(f"  {row.season}: {row.total_plays:,} total, {row.qb_plays:,} QB, {row.rb_plays:,} RB, {row.wr_plays:,} WR")
        
        return True
        
    except Exception as e:
        print(f"❌ Error loading data: {e}")
        session.rollback()
        import traceback
        traceback.print_exc()
        return False
        
    finally:
        session.close()


if __name__ == "__main__":
    print("🚀 Starting NFL data download and loading...")
    
    # Download data
    download_nfl_pbp_data([2023, 2024])
    
    # Load into database
    success = load_pbp_to_database([2023, 2024])
    
    if success:
        print("\n🎉 NFL data loaded successfully!")
        print("🏆 League Leaders should now show real NFL players!")
        print("🔗 Visit http://localhost:8000/web/league-leaders")
    else:
        print("\n💥 Data loading failed!")
        sys.exit(1)