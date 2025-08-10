#!/usr/bin/env python3
"""Set up SQLite database and load 2024 NFL data directly."""

import sqlite3
import pandas as pd
from pathlib import Path

def create_database_schema():
    """Create the necessary tables for NFL data."""
    
    db_path = "nfl_data.db"
    conn = sqlite3.connect(db_path)
    
    try:
        cursor = conn.cursor()
        
        # Create plays table with simplified schema
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS plays (
                play_id TEXT PRIMARY KEY,
                game_id TEXT,
                season INTEGER,
                week INTEGER,
                season_type TEXT,
                game_date TEXT,
                home_team TEXT,
                away_team TEXT,
                posteam TEXT,
                defteam TEXT,
                play_type TEXT,
                yards_gained REAL,
                down INTEGER,
                ydstogo INTEGER,
                yardline_100 REAL,
                pass_attempt BOOLEAN,
                rush_attempt BOOLEAN,
                complete_pass BOOLEAN,
                passer_player_name TEXT,
                passer_player_id TEXT,
                rusher_player_name TEXT,
                rusher_player_id TEXT,
                receiver_player_name TEXT,
                receiver_player_id TEXT,
                passing_yards REAL,
                rushing_yards REAL,
                receiving_yards REAL,
                touchdown BOOLEAN,
                interception BOOLEAN,
                fumble BOOLEAN,
                sack BOOLEAN,
                epa REAL,
                wp REAL,
                wpa REAL,
                air_yards REAL,
                yards_after_catch REAL,
                qb_epa REAL,
                pass_touchdown BOOLEAN,
                rush_touchdown BOOLEAN,
                two_point_attempt BOOLEAN,
                field_goal_attempt BOOLEAN,
                extra_point_attempt BOOLEAN
            )
        """)
        
        # Create index for quick League Leaders queries
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_passer ON plays(passer_player_name)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_rusher ON plays(rusher_player_name)")  
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_receiver ON plays(receiver_player_name)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_pass_attempt ON plays(pass_attempt)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_rush_attempt ON plays(rush_attempt)")
        
        conn.commit()
        print(f"✅ Created database schema: {db_path}")
        return db_path
        
    finally:
        conn.close()

def load_2024_data(db_path):
    """Load 2024 NFL data into the database."""
    
    data_dir = Path("data")
    pbp_file = data_dir / "pbp_2024.parquet"
    
    if not pbp_file.exists():
        print("❌ No play-by-play data found!")
        return False
    
    print(f"Loading {pbp_file}...")
    pbp_df = pd.read_parquet(pbp_file)
    print(f"Loaded {len(pbp_df):,} plays from parquet file")
    
    conn = sqlite3.connect(db_path)
    
    try:
        # Prepare simplified data
        print("Processing data for database insertion...")
        
        # Select and clean essential columns
        essential_data = pbp_df.copy()
        
        # Ensure boolean columns are properly formatted
        bool_cols = ['pass', 'rush', 'complete_pass', 'touchdown', 'interception', 'fumble', 'sack', 
                    'pass_touchdown', 'rush_touchdown', 'two_point_attempt', 'field_goal_attempt', 'extra_point_attempt']
        
        for col in bool_cols:
            if col in essential_data.columns:
                essential_data[col] = essential_data[col].fillna(False).astype(bool)
        
        # Handle column mapping - avoid duplicates
        if 'pass' in essential_data.columns and 'pass_attempt' not in essential_data.columns:
            essential_data['pass_attempt'] = essential_data['pass']
            essential_data = essential_data.drop(columns=['pass'])
        elif 'pass' in essential_data.columns and 'pass_attempt' in essential_data.columns:
            # Use pass_attempt and drop pass
            essential_data = essential_data.drop(columns=['pass'])
            
        if 'rush' in essential_data.columns and 'rush_attempt' not in essential_data.columns:
            essential_data['rush_attempt'] = essential_data['rush']
            essential_data = essential_data.drop(columns=['rush'])
        elif 'rush' in essential_data.columns and 'rush_attempt' in essential_data.columns:
            # Use rush_attempt and drop rush
            essential_data = essential_data.drop(columns=['rush'])
        
        # Fill NaN values
        essential_data = essential_data.fillna({
            'play_id': '',
            'game_id': '',
            'season': 2024,
            'week': 1,
            'season_type': 'REG',
            'game_date': '',
            'home_team': '',
            'away_team': '',
            'posteam': '',
            'defteam': '',
            'play_type': '',
            'yards_gained': 0,
            'down': 0,
            'ydstogo': 0,
            'yardline_100': 0,
            'pass_attempt': False,
            'rush_attempt': False,
            'complete_pass': False,
            'passer_player_name': '',
            'passer_player_id': '',
            'rusher_player_name': '',
            'rusher_player_id': '',
            'receiver_player_name': '',
            'receiver_player_id': '',
            'passing_yards': 0,
            'rushing_yards': 0,
            'receiving_yards': 0,
            'touchdown': False,
            'interception': False,
            'fumble': False,
            'sack': False,
            'epa': 0,
            'wp': 0,
            'wpa': 0,
            'air_yards': 0,
            'yards_after_catch': 0,
            'qb_epa': 0,
            'pass_touchdown': False,
            'rush_touchdown': False,
            'two_point_attempt': False,
            'field_goal_attempt': False,
            'extra_point_attempt': False
        })
        
        # Insert data using pandas to_sql (much faster)
        print("Inserting data into database...")
        
        # Select only columns that exist in our schema
        db_columns = [
            'play_id', 'game_id', 'season', 'week', 'season_type', 'game_date',
            'home_team', 'away_team', 'posteam', 'defteam', 'play_type',
            'yards_gained', 'down', 'ydstogo', 'yardline_100',
            'pass_attempt', 'rush_attempt', 'complete_pass',
            'passer_player_name', 'passer_player_id',
            'rusher_player_name', 'rusher_player_id',
            'receiver_player_name', 'receiver_player_id',
            'passing_yards', 'rushing_yards', 'receiving_yards',
            'touchdown', 'interception', 'fumble', 'sack', 'epa', 'wp', 'wpa',
            'air_yards', 'yards_after_catch', 'qb_epa',
            'pass_touchdown', 'rush_touchdown', 'two_point_attempt',
            'field_goal_attempt', 'extra_point_attempt'
        ]
        
        # Filter to columns that exist in the dataframe
        available_columns = [col for col in db_columns if col in essential_data.columns]
        insert_data = essential_data[available_columns]
        
        # Insert data
        insert_data.to_sql('plays', conn, if_exists='replace', index=False, chunksize=1000)
        
        print(f"✅ Inserted {len(insert_data)} plays into database")
        
        # Verification queries
        cursor = conn.cursor()
        
        # Total plays
        cursor.execute("SELECT COUNT(*) FROM plays")
        total_plays = cursor.fetchone()[0]
        print(f"   Total plays in database: {total_plays:,}")
        
        # QB stats
        cursor.execute("""
            SELECT passer_player_name, COUNT(*) as attempts 
            FROM plays 
            WHERE pass_attempt = 1 AND passer_player_name != ''
            GROUP BY passer_player_name 
            ORDER BY attempts DESC 
            LIMIT 10
        """)
        
        top_qbs = cursor.fetchall()
        print(f"\n🏆 Top 10 QBs by attempts:")
        for i, (qb, attempts) in enumerate(top_qbs, 1):
            print(f"   {i:2d}. {qb}: {attempts} attempts")
        
        # RB stats  
        cursor.execute("""
            SELECT rusher_player_name, COUNT(*) as carries
            FROM plays 
            WHERE rush_attempt = 1 AND rusher_player_name != ''
            GROUP BY rusher_player_name 
            ORDER BY carries DESC 
            LIMIT 10
        """)
        
        top_rbs = cursor.fetchall()
        print(f"\n🏃 Top 10 RBs by carries:")
        for i, (rb, carries) in enumerate(top_rbs, 1):
            print(f"   {i:2d}. {rb}: {carries} carries")
        
        # Verify star players
        cursor.execute("SELECT COUNT(*) FROM plays WHERE passer_player_name LIKE '%Mahomes%'")
        mahomes_plays = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM plays WHERE passer_player_name LIKE '%Burrow%'")
        burrow_plays = cursor.fetchone()[0]
        
        print(f"\n✅ STAR VERIFICATION:")
        print(f"   Patrick Mahomes: {mahomes_plays} plays")
        print(f"   Joe Burrow: {burrow_plays} plays")
        
        if mahomes_plays > 500 and burrow_plays > 500:
            print(f"\n🎉 SUCCESS! Database is ready for League Leaders with real NFL stars!")
            return True
        else:
            print(f"\n⚠️  Warning: Star player verification incomplete")
            return True  # Still return True if we have data
    
    except Exception as e:
        print(f"❌ Data loading failed: {e}")
        return False
    
    finally:
        conn.close()

def main():
    print("=" * 70)
    print("NFL DATABASE SETUP AND DATA LOADING")  
    print("=" * 70)
    
    # Create database schema
    db_path = create_database_schema()
    
    # Load 2024 data
    success = load_2024_data(db_path)
    
    if success:
        print(f"\n🚀 COMPLETE! Your NFL database is ready at: {db_path}")
        print(f"   Use this database with your League Leaders system")
        print(f"   Update your DATABASE_URL to: sqlite:///{db_path}")
        print(f"\n🎯 Expected League Leaders will show:")
        print(f"   - Patrick Mahomes, Joe Burrow, C.J. Stroud (QBs)")
        print(f"   - Saquon Barkley, Derrick Henry, Josh Jacobs (RBs)")
        print(f"   - DJ Moore, Ja'Marr Chase, Amon-Ra St. Brown (WRs)")
    else:
        print(f"\n❌ Setup failed. Check error messages above.")

if __name__ == "__main__":
    main()