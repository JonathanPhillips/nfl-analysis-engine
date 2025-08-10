#!/usr/bin/env python3
"""
Apply position data fix by fetching seasonal rosters and updating player positions.

This script implements the fix identified by the NFL data scientist to improve
position data coverage from 8.6% to >95% by using seasonal roster data.
"""

import os
import sys
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

# Add the src directory to Python path
sys.path.insert(0, os.path.dirname(__file__))

from database.config import get_database_url

def apply_position_fix():
    """Apply position data fix using seasonal rosters data."""
    
    # Get database connection
    database_url = get_database_url()
    engine = create_engine(database_url)
    Session = sessionmaker(bind=engine)
    session = Session()
    
    try:
        print("🔍 Checking current position data coverage...")
        result = session.execute(text("SELECT COUNT(*) as total, COUNT(position) as with_position FROM players"))
        row = result.fetchone()
        initial_coverage = (row.with_position / row.total) * 100
        print(f"📊 Current position coverage: {row.with_position:,} of {row.total:,} players ({initial_coverage:.1f}%)")
        
        if initial_coverage > 90:
            print("✅ Position coverage is already good!")
            return True
        
        # Import nfl_data_py to get seasonal rosters
        print("📥 Fetching seasonal roster data from nfl_data_py...")
        import nfl_data_py as nfl
        
        # Get rosters for recent seasons to maximize coverage
        seasons = [2023, 2022, 2021, 2020]
        print(f"🔄 Loading roster data for seasons: {seasons}")
        
        rosters_updated = 0
        jerseys_updated = 0
        
        for season in seasons:
            print(f"  Processing season {season}...")
            
            try:
                # Fetch seasonal rosters for this season
                season_rosters = nfl.import_seasonal_rosters([season])
                
                if season_rosters.empty:
                    print(f"    ⚠️ No roster data found for {season}")
                    continue
                    
                # Filter to players with position data
                valid_rosters = season_rosters[
                    (season_rosters['player_id'].notna()) & 
                    (season_rosters['position'].notna()) & 
                    (season_rosters['position'].str.strip() != '')
                ].copy()
                
                print(f"    Found {len(valid_rosters):,} players with position data")
                
                # Update players in batches
                batch_size = 1000
                season_updates = 0
                season_jersey_updates = 0
                
                for i in range(0, len(valid_rosters), batch_size):
                    batch = valid_rosters.iloc[i:i + batch_size]
                    
                    # Process individual updates using parameterized queries (fix SQL injection vulnerability)
                    batch_updates = 0
                    for _, row in batch.iterrows():
                        player_id = row['player_id']
                        position = row['position']
                        jersey_number = row.get('jersey_number')
                        
                        # Skip if essential data is missing
                        if not player_id or not position:
                            continue
                            
                        # Handle NaN jersey numbers safely
                        import math
                        if jersey_number is not None and not math.isnan(float(jersey_number)):
                            jersey_num = int(jersey_number)
                        else:
                            jersey_num = None
                        
                        # Use parameterized query to prevent SQL injection
                        update_query = text("""
                            UPDATE players 
                            SET position = COALESCE(players.position, :position),
                                jersey_number = COALESCE(players.jersey_number, :jersey_number)
                            WHERE players.player_id = :player_id
                              AND (players.position IS NULL OR players.jersey_number IS NULL)
                        """)
                        
                        result = session.execute(update_query, {
                            'player_id': player_id,
                            'position': position,
                            'jersey_number': jersey_num
                        })
                        batch_updates += result.rowcount
                    season_updates += batch_updates
                    
                    if batch_updates > 0:
                        session.commit()
                        print(f"      Updated {batch_updates} players in batch")
                
                rosters_updated += season_updates
                print(f"    Season {season} total: {season_updates} players updated")
                
            except Exception as e:
                print(f"    ❌ Error processing season {season}: {e}")
                continue
        
        print(f"\n✅ Position fix completed! Updated {rosters_updated:,} players")
        
        # Verify the results
        result = session.execute(text("SELECT COUNT(*) as total, COUNT(position) as with_position FROM players"))
        row = result.fetchone()
        final_coverage = (row.with_position / row.total) * 100
        improvement = final_coverage - initial_coverage
        
        print(f"📊 Final position coverage: {row.with_position:,} of {row.total:,} players ({final_coverage:.1f}%)")
        print(f"🚀 Improvement: {improvement:+.1f} percentage points")
        
        if final_coverage > 95:
            print("🎉 Achieved target coverage of >95%!")
        elif improvement > 10:
            print("✅ Significant improvement achieved!")
        else:
            print("⚠️ Improvement was limited - may need additional data sources")
        
        return True
        
    except Exception as e:
        print(f"❌ Error applying position fix: {e}")
        session.rollback()
        return False
        
    finally:
        session.close()

if __name__ == "__main__":
    print("🚀 Starting position data fix...")
    
    success = apply_position_fix()
    if success:
        print("\n🎉 Position data fix completed successfully!")
    else:
        print("\n💥 Position data fix failed!")
        sys.exit(1)