#!/usr/bin/env python3
"""NFL data extraction script for Docker container."""

import nfl_data_py as nfl
import pandas as pd
import logging
import sys
from pathlib import Path

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def extract_2024_data():
    """Extract 2024 NFL data for League Leaders system."""
    
    print("=" * 60)
    print("NFL DATA EXTRACTION - DOCKER ENVIRONMENT")
    print("=" * 60)
    
    data_dir = Path("/app/data")
    data_dir.mkdir(exist_ok=True)
    
    try:
        # 1. Extract play-by-play data
        print("\n1. Extracting 2024 play-by-play data...")
        pbp_2024 = nfl.import_pbp_data([2024], downcast=False)
        
        if not pbp_2024.empty:
            # Save as parquet for efficient loading
            pbp_file = data_dir / "pbp_2024.parquet"
            pbp_2024.to_parquet(pbp_file, index=False)
            
            print(f"✅ Saved {len(pbp_2024)} plays to {pbp_file}")
            print(f"   File size: {pbp_file.stat().st_size / (1024*1024):.1f} MB")
            
            # Basic analysis for League Leaders validation
            print(f"   Date range: {pbp_2024['game_date'].min()} to {pbp_2024['game_date'].max()}")
            print(f"   Weeks: {sorted(pbp_2024['week'].unique())}")
            print(f"   Unique games: {pbp_2024['game_id'].nunique()}")
            
            # QB analysis
            if 'passer_player_name' in pbp_2024.columns:
                qb_attempts = pbp_2024[pbp_2024['pass'] == 1]['passer_player_name'].value_counts()
                print(f"   Top QBs by attempts: {list(qb_attempts.head(5).index)}")
                qualified_qbs = qb_attempts[qb_attempts >= 150]
                print(f"   QBs with 150+ attempts: {len(qualified_qbs)}")
            
            # RB analysis
            if 'rusher_player_name' in pbp_2024.columns:
                rb_carries = pbp_2024[pbp_2024['rush'] == 1]['rusher_player_name'].value_counts()
                print(f"   Top RBs by carries: {list(rb_carries.head(5).index)}")
                qualified_rbs = rb_carries[rb_carries >= 75]
                print(f"   RBs with 75+ carries: {len(qualified_rbs)}")
        
        else:
            print("❌ No 2024 play-by-play data available")
            
            # Try 2023 data as fallback
            print("\nFalling back to 2023 data for testing...")
            pbp_2023 = nfl.import_pbp_data([2023], downcast=False)
            
            if not pbp_2023.empty:
                pbp_file = data_dir / "pbp_2023.parquet"
                pbp_2023.to_parquet(pbp_file, index=False)
                print(f"✅ Saved 2023 data: {len(pbp_2023)} plays")
            else:
                print("❌ No 2023 data available either")
    
    except Exception as e:
        print(f"❌ Play-by-play extraction failed: {e}")
    
    try:
        # 2. Extract roster data
        print("\n2. Extracting roster data...")
        rosters = nfl.import_seasonal_rosters([2024])
        
        if not rosters.empty:
            roster_file = data_dir / "rosters_2024.parquet"
            rosters.to_parquet(roster_file, index=False)
            print(f"✅ Saved {len(rosters)} roster entries")
        else:
            print("❌ No roster data available")
            
    except Exception as e:
        print(f"❌ Roster extraction failed: {e}")
    
    try:
        # 3. Extract schedule data
        print("\n3. Extracting schedule data...")
        schedule = nfl.import_schedules([2024])
        
        if not schedule.empty:
            schedule_file = data_dir / "schedule_2024.parquet"
            schedule.to_parquet(schedule_file, index=False)
            print(f"✅ Saved {len(schedule)} games")
        else:
            print("❌ No schedule data available")
            
    except Exception as e:
        print(f"❌ Schedule extraction failed: {e}")
    
    # 4. Summary
    print("\n" + "=" * 60)
    print("EXTRACTION SUMMARY")
    print("=" * 60)
    
    extracted_files = list(data_dir.glob("*.parquet"))
    total_size = sum(f.stat().st_size for f in extracted_files)
    
    print(f"Extracted files: {len(extracted_files)}")
    print(f"Total size: {total_size / (1024*1024):.1f} MB")
    
    if extracted_files:
        print("Files:")
        for file in extracted_files:
            size_mb = file.stat().st_size / (1024*1024)
            print(f"  - {file.name}: {size_mb:.1f} MB")
        
        print("\nTo use in Python 3.13 environment:")
        print("1. Copy files from Docker container:")
        print("   docker cp <container_id>:/app/data ./data/")
        print("2. Load in Python:")
        print("   import pandas as pd")
        print("   pbp = pd.read_parquet('data/pbp_2024.parquet')")
    else:
        print("❌ No data files were successfully extracted")

if __name__ == "__main__":
    extract_2024_data()