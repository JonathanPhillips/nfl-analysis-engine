#!/usr/bin/env python3
"""
Load 2025 NFL season schedule with team abbreviation mapping fixes.

This script loads the 2025 NFL schedule and maps old team abbreviations 
to current ones to maintain foreign key consistency.
"""

import os
import sys
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
import pandas as pd

# Add the src directory to Python path
sys.path.insert(0, os.path.dirname(__file__))

from database.config import get_database_url

def load_2025_schedule():
    """Load 2025 NFL schedule with team mapping fixes."""
    
    # Get database connection
    database_url = get_database_url()
    engine = create_engine(database_url)
    Session = sessionmaker(bind=engine)
    session = Session()
    
    try:
        print("📅 Loading 2025 NFL schedule...")
        
        # Check if we already have 2025 games
        result = session.execute(text("SELECT COUNT(*) FROM games WHERE season = 2025"))
        existing_count = result.scalar()
        
        if existing_count > 0:
            print(f"⚠️ Found {existing_count} existing 2025 games. Skipping duplicate load.")
            return True
        
        # Import nfl_data_py to get 2025 schedule
        import nfl_data_py as nfl
        
        print("📥 Fetching 2025 schedule from nfl_data_py...")
        schedule_2025 = nfl.import_schedules([2025])
        
        if schedule_2025.empty:
            print("⚠️ No 2025 schedule data available yet")
            return True
            
        print(f"📊 Found {len(schedule_2025)} games for 2025 season")
        
        # Map old team abbreviations to current ones
        team_mapping = {
            'LA': 'LAR',   # Los Angeles Rams
            'OAK': 'LV',   # Oakland Raiders -> Las Vegas Raiders  
            'SD': 'LAC',   # San Diego Chargers -> Los Angeles Chargers
            'STL': 'LAR'   # St. Louis Rams -> Los Angeles Rams
        }
        
        # Apply team mappings
        schedule_2025['home_team'] = schedule_2025['home_team'].replace(team_mapping)
        schedule_2025['away_team'] = schedule_2025['away_team'].replace(team_mapping)
        
        print("🔄 Applied team abbreviation mappings")
        
        # Verify all teams exist in database
        all_teams = list(schedule_2025['home_team'].unique()) + list(schedule_2025['away_team'].unique())
        unique_teams = sorted(set(all_teams))
        
        result = session.execute(text("SELECT team_abbr FROM teams"))
        db_teams = set(row.team_abbr for row in result)
        
        missing_teams = [team for team in unique_teams if team not in db_teams]
        if missing_teams:
            print(f"❌ Teams missing from database: {missing_teams}")
            return False
        
        print(f"✅ All {len(unique_teams)} teams exist in database")
        
        # Prepare games data for insertion
        games_data = []
        for _, game in schedule_2025.iterrows():
            game_data = {
                'game_id': game['game_id'],
                'season': int(game['season']),
                'week': int(game['week']) if pd.notna(game['week']) else None,
                'season_type': str(game['game_type']) if pd.notna(game['game_type']) else 'REG',
                'home_team': str(game['home_team']),
                'away_team': str(game['away_team']),
                'game_date': pd.to_datetime(game['gameday']).date(),
                'kickoff_time': str(game['gametime']) if pd.notna(game['gametime']) else None,
                'home_score': None,  # Games haven't been played yet
                'away_score': None
            }
            games_data.append(game_data)
        
        # Insert games in batches
        batch_size = 50
        inserted_count = 0
        
        for i in range(0, len(games_data), batch_size):
            batch = games_data[i:i + batch_size]
            
            # Process individual inserts using parameterized queries (fix SQL injection vulnerability)
            batch_inserted = 0
            for game in batch:
                # Use parameterized query to prevent SQL injection
                insert_query = text("""
                    INSERT INTO games (
                        game_id, season, week, season_type, home_team, away_team, 
                        game_date, kickoff_time, home_score, away_score,
                        created_at, updated_at, is_active
                    ) VALUES (
                        :game_id, :season, :week, :season_type, :home_team, :away_team,
                        :game_date, :kickoff_time, :home_score, :away_score,
                        NOW(), NOW(), TRUE
                    )
                    ON CONFLICT (game_id) DO NOTHING
                """)
                
                result = session.execute(insert_query, {
                    'game_id': game['game_id'],
                    'season': game['season'],
                    'week': game['week'],
                    'season_type': game['season_type'],
                    'home_team': game['home_team'],
                    'away_team': game['away_team'],
                    'game_date': game['game_date'],
                    'kickoff_time': game['kickoff_time'],
                    'home_score': game['home_score'],
                    'away_score': game['away_score']
                })
                batch_inserted += result.rowcount
            inserted_count += batch_inserted
            
            if batch_inserted > 0:
                session.commit()
                print(f"    Inserted {batch_inserted} games (batch {i//batch_size + 1})")
        
        print(f"\n✅ Successfully loaded {inserted_count} games for 2025 season")
        
        # Show sample upcoming games
        print("\n📋 Sample upcoming games:")
        result = session.execute(text("""
            SELECT game_date, home_team, away_team, week
            FROM games 
            WHERE season = 2025 
            ORDER BY game_date 
            LIMIT 5
        """))
        
        for row in result:
            print(f"  Week {row.week}: {row.away_team} @ {row.home_team} on {row.game_date}")
        
        return True
        
    except Exception as e:
        print(f"❌ Error loading 2025 schedule: {e}")
        session.rollback()
        return False
        
    finally:
        session.close()

if __name__ == "__main__":
    print("🚀 Starting 2025 schedule load...")
    
    success = load_2025_schedule()
    if success:
        print("\n🎉 2025 schedule load completed successfully!")
    else:
        print("\n💥 2025 schedule load failed!")
        sys.exit(1)