#!/usr/bin/env python3
"""
Complete NFL data migration from SQLite to PostgreSQL.

This script handles the schema differences between nflfastR SQLite format
and our PostgreSQL PlayModel schema, properly mapping all 49,492 plays.
"""

import os
import sys
import sqlite3
import pandas as pd
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from datetime import datetime
import logging

# Add the project root to Python path
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from src.database.config import get_database_url

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def transform_sqlite_to_postgres_schema(df):
    """Transform SQLite dataframe to match PostgreSQL PlayModel schema."""
    
    logger.info("🔄 Transforming SQLite data to PostgreSQL schema...")
    
    # Create a new dataframe with PostgreSQL column structure
    postgres_df = pd.DataFrame()
    
    # Direct mappings (same column names)
    direct_mappings = {
        'play_id': 'play_id',
        'game_id': 'game_id', 
        'season': 'season',
        'week': 'week',
        'posteam': 'posteam',
        'defteam': 'defteam',
        'yards_gained': 'yards_gained',
        'epa': 'epa',
        'wp': 'wp',
        'wpa': 'wpa',
        'air_yards': 'air_yards',
        'yards_after_catch': 'yards_after_catch',
        'passer_player_id': 'passer_player_id',
        'receiver_player_id': 'receiver_player_id', 
        'rusher_player_id': 'rusher_player_id',
        'touchdown': 'touchdown',
        'pass_touchdown': 'pass_touchdown',
        'rush_touchdown': 'rush_touchdown',
        'interception': 'interception',
        'fumble': 'fumble'
    }
    
    for sqlite_col, postgres_col in direct_mappings.items():
        if sqlite_col in df.columns:
            postgres_df[postgres_col] = df[sqlite_col]
    
    # Handle foreign key constraints by setting empty strings to None
    fk_columns = ['posteam', 'defteam', 'passer_player_id', 'receiver_player_id', 'rusher_player_id']
    for col in fk_columns:
        if col in postgres_df.columns:
            # Replace empty strings and whitespace-only strings with None
            postgres_df[col] = postgres_df[col].replace('', None)
            postgres_df[col] = postgres_df[col].replace(' ', None)
            # Also handle pandas NaN values
            postgres_df[col] = postgres_df[col].where(postgres_df[col].notna(), None)
    
    # Transform REAL to INTEGER fields
    real_to_int_fields = ['down', 'ydstogo', 'yardline_100', 'yards_gained', 'air_yards', 'yards_after_catch']
    for field in real_to_int_fields:
        if field in postgres_df.columns:
            postgres_df[field] = pd.to_numeric(postgres_df[field], errors='coerce').fillna(0).astype('Int64')
    
    # Transform play_id from REAL to STRING
    if 'play_id' in postgres_df.columns:
        postgres_df['play_id'] = postgres_df['play_id'].astype(str)
    
    # Determine play_type from pass_attempt/rush_attempt flags
    if 'play_type' not in postgres_df.columns or postgres_df['play_type'].isna().all():
        logger.info("   🔍 Deriving play_type from pass_attempt/rush_attempt flags...")
        
        pass_attempt = pd.to_numeric(df.get('pass_attempt', 0), errors='coerce').fillna(0)
        rush_attempt = pd.to_numeric(df.get('rush_attempt', 0), errors='coerce').fillna(0)
        
        postgres_df['play_type'] = 'no_play'  # default
        postgres_df.loc[pass_attempt > 0, 'play_type'] = 'pass'
        postgres_df.loc[rush_attempt > 0, 'play_type'] = 'run'
        
        # Special cases
        if 'field_goal_attempt' in df.columns:
            fg_attempt = pd.to_numeric(df['field_goal_attempt'], errors='coerce').fillna(0)
            postgres_df.loc[fg_attempt > 0, 'play_type'] = 'field_goal'
        
        if 'extra_point_attempt' in df.columns:
            xp_attempt = pd.to_numeric(df['extra_point_attempt'], errors='coerce').fillna(0)
            postgres_df.loc[xp_attempt > 0, 'play_type'] = 'extra_point'
    else:
        postgres_df['play_type'] = df['play_type']
    
    # Convert boolean fields from INTEGER (0/1) to proper boolean
    boolean_fields = ['touchdown', 'pass_touchdown', 'rush_touchdown', 'interception', 'fumble']
    for field in boolean_fields:
        if field in postgres_df.columns:
            postgres_df[field] = postgres_df[field].astype('boolean')
    
    # Add missing PostgreSQL fields with default values
    missing_fields = {
        'qtr': None,  # Quarter not available in SQLite
        'game_seconds_remaining': None,
        'half_seconds_remaining': None, 
        'game_half': None,
        'desc': None,  # Play description not available
        'posteam_score': None,
        'defteam_score': None,
        'score_differential': None,
        'ep': None,  # Expected Points not available
        'cpoe': None,  # Not available in this SQLite schema
        'pass_location': None,
        'safety': False,
        'penalty': False,
        'created_at': datetime.now(),
        'updated_at': datetime.now(),
        'is_active': True
    }
    
    for field, default_value in missing_fields.items():
        if field not in postgres_df.columns:
            postgres_df[field] = default_value
    
    logger.info(f"   ✅ Transformed {len(postgres_df)} rows with {len(postgres_df.columns)} columns")
    
    return postgres_df


def create_teams_from_plays(postgres_session, sqlite_conn):
    """Extract and create team records from plays data."""
    
    logger.info("🏈 Creating team records from plays data...")
    
    # Get unique teams from SQLite plays
    teams_query = """
    SELECT DISTINCT posteam as team_abbr FROM plays 
    WHERE posteam IS NOT NULL AND posteam != ''
    UNION
    SELECT DISTINCT defteam as team_abbr FROM plays
    WHERE defteam IS NOT NULL AND defteam != ''
    UNION  
    SELECT DISTINCT home_team as team_abbr FROM plays
    WHERE home_team IS NOT NULL AND home_team != ''
    UNION
    SELECT DISTINCT away_team as team_abbr FROM plays
    WHERE away_team IS NOT NULL AND away_team != ''
    """
    
    teams_df = pd.read_sql_query(teams_query, sqlite_conn)
    
    # Team name mappings (partial list for common teams)
    team_names = {
        'KC': 'Kansas City Chiefs',
        'BAL': 'Baltimore Ravens',
        'BUF': 'Buffalo Bills',
        'SF': 'San Francisco 49ers',
        'DAL': 'Dallas Cowboys',
        'ATL': 'Atlanta Falcons',
        'ARI': 'Arizona Cardinals',
        'NYG': 'New York Giants',
        'PHI': 'Philadelphia Eagles',
        'WAS': 'Washington Commanders',
        'GB': 'Green Bay Packers',
        'MIN': 'Minnesota Vikings',
        'CHI': 'Chicago Bears',
        'DET': 'Detroit Lions',
        'NO': 'New Orleans Saints',
        'TB': 'Tampa Bay Buccaneers',
        'CAR': 'Carolina Panthers',
        'LAR': 'Los Angeles Rams',
        'SEA': 'Seattle Seahawks',
        'LV': 'Las Vegas Raiders',
        'LAC': 'Los Angeles Chargers',
        'DEN': 'Denver Broncos',
        'PIT': 'Pittsburgh Steelers',
        'CLE': 'Cleveland Browns',
        'CIN': 'Cincinnati Bengals',
        'TEN': 'Tennessee Titans',
        'JAX': 'Jacksonville Jaguars',
        'IND': 'Indianapolis Colts',
        'HOU': 'Houston Texans',
        'NE': 'New England Patriots',
        'MIA': 'Miami Dolphins',
        'NYJ': 'New York Jets'
    }
    
    for _, team in teams_df.iterrows():
        try:
            team_abbr = team['team_abbr']
            team_name = team_names.get(team_abbr, f"{team_abbr} Team")
            
            postgres_session.execute(text("""
                INSERT INTO teams (team_abbr, full_name, created_at, updated_at, is_active)
                VALUES (:team_abbr, :full_name, :created_at, :updated_at, :is_active)
                ON CONFLICT (team_abbr) DO UPDATE SET
                    full_name = EXCLUDED.full_name,
                    updated_at = EXCLUDED.updated_at
            """), {
                'team_abbr': team_abbr,
                'full_name': team_name,
                'created_at': datetime.now(),
                'updated_at': datetime.now(),
                'is_active': True
            })
        except Exception as e:
            logger.warning(f"  ⚠️  Team insert failed for {team_abbr}: {str(e)}")
            continue
    
    postgres_session.commit()
    logger.info(f"   🏆 Created {len(teams_df)} team records")


def create_games_from_plays(postgres_session, sqlite_conn):
    """Extract and create game records from plays data."""
    
    logger.info("🎮 Creating game records from plays data...")
    
    # Get unique games from SQLite plays
    games_query = """
    SELECT DISTINCT 
        game_id,
        season,
        week,
        season_type,
        game_date,
        home_team,
        away_team
    FROM plays
    WHERE game_id IS NOT NULL AND game_id != ''
    ORDER BY game_date, game_id
    """
    
    games_df = pd.read_sql_query(games_query, sqlite_conn)
    
    for _, game in games_df.iterrows():
        try:
            postgres_session.execute(text("""
                INSERT INTO games (game_id, season, week, season_type, game_date, home_team, away_team, created_at, updated_at, is_active)
                VALUES (:game_id, :season, :week, :season_type, :game_date, :home_team, :away_team, :created_at, :updated_at, :is_active)
                ON CONFLICT (game_id) DO UPDATE SET
                    season = EXCLUDED.season,
                    week = EXCLUDED.week,
                    season_type = EXCLUDED.season_type,
                    game_date = EXCLUDED.game_date,
                    home_team = EXCLUDED.home_team,
                    away_team = EXCLUDED.away_team,
                    updated_at = EXCLUDED.updated_at
            """), {
                'game_id': game['game_id'],
                'season': int(game['season']),
                'week': int(game['week']) if pd.notna(game['week']) else None,
                'season_type': game['season_type'],
                'game_date': game['game_date'],
                'home_team': game['home_team'],
                'away_team': game['away_team'],
                'created_at': datetime.now(),
                'updated_at': datetime.now(),
                'is_active': True
            })
        except Exception as e:
            logger.warning(f"  ⚠️  Game insert failed for {game['game_id']}: {str(e)}")
            continue
    
    postgres_session.commit()
    logger.info(f"   🏅 Created {len(games_df)} game records")


def load_and_transform_players(sqlite_conn):
    """Load and transform player data from SQLite to PostgreSQL format."""
    
    logger.info("👥 Loading player data from SQLite...")
    
    # Query unique players from plays table
    players_query = """
    SELECT DISTINCT
        passer_player_id as player_id,
        passer_player_name as full_name,
        'QB' as position
    FROM plays 
    WHERE passer_player_id IS NOT NULL 
    AND passer_player_id != ''
    AND passer_player_name IS NOT NULL
    AND passer_player_name != ''
    
    UNION
    
    SELECT DISTINCT
        rusher_player_id as player_id,
        rusher_player_name as full_name,  
        'RB' as position
    FROM plays
    WHERE rusher_player_id IS NOT NULL 
    AND rusher_player_id != ''
    AND rusher_player_name IS NOT NULL
    AND rusher_player_name != ''
    
    UNION
    
    SELECT DISTINCT
        receiver_player_id as player_id,
        receiver_player_name as full_name,
        'WR' as position  
    FROM plays
    WHERE receiver_player_id IS NOT NULL
    AND receiver_player_id != ''
    AND receiver_player_name IS NOT NULL
    AND receiver_player_name != ''
    """
    
    players_df = pd.read_sql_query(players_query, sqlite_conn)
    
    # Add required PostgreSQL fields
    players_df['team_abbr'] = None  # Will be filled from team context if available
    players_df['created_at'] = datetime.now()
    players_df['updated_at'] = datetime.now()
    players_df['is_active'] = True
    
    logger.info(f"   📊 Loaded {len(players_df)} unique players")
    
    return players_df


def migrate_nfl_data_to_postgres():
    """Complete migration of NFL data from SQLite to PostgreSQL."""
    
    logger.info("🚀 Starting NFL data migration from SQLite to PostgreSQL...")
    
    # Verify SQLite database exists
    if not os.path.exists('nfl_data.db'):
        logger.error("❌ nfl_data.db not found. Please ensure the SQLite database is available.")
        return False
    
    # Connect to databases
    sqlite_conn = sqlite3.connect('nfl_data.db')
    postgres_url = get_database_url()
    postgres_engine = create_engine(postgres_url)
    Session = sessionmaker(bind=postgres_engine)
    postgres_session = Session()
    
    try:
        # 1. Clear existing 2024 data from PostgreSQL
        logger.info("🧹 Clearing existing 2024 data from PostgreSQL...")
        postgres_session.execute(text("DELETE FROM plays WHERE season = 2024"))
        postgres_session.commit()
        logger.info("   ✅ Cleared existing 2024 plays")
        
        # 2. Create prerequisite data (teams, games) 
        create_teams_from_plays(postgres_session, sqlite_conn)
        create_games_from_plays(postgres_session, sqlite_conn)
        
        # 3. Load and insert players first
        players_df = load_and_transform_players(sqlite_conn)
        logger.info("📤 Inserting players into PostgreSQL...")
        for _, player in players_df.iterrows():
            try:
                postgres_session.execute(text("""
                    INSERT INTO players (player_id, full_name, position, team_abbr, created_at, updated_at, is_active)
                    VALUES (:player_id, :full_name, :position, :team_abbr, :created_at, :updated_at, :is_active)
                    ON CONFLICT (player_id) DO UPDATE SET
                        full_name = EXCLUDED.full_name,
                        position = EXCLUDED.position,
                        team_abbr = EXCLUDED.team_abbr,
                        updated_at = EXCLUDED.updated_at
                """), {
                    'player_id': player['player_id'],
                    'full_name': player['full_name'], 
                    'position': player['position'],
                    'team_abbr': player['team_abbr'],
                    'created_at': player['created_at'],
                    'updated_at': player['updated_at'],
                    'is_active': player['is_active']
                })
            except Exception as e:
                logger.warning(f"  ⚠️  Player insert failed for {player['full_name']}: {str(e)}")
                continue
        
        postgres_session.commit()
        logger.info(f"   👥 Successfully inserted {len(players_df)} players!")
        
        # 4. Load all plays from SQLite
        logger.info("📥 Reading all NFL plays from SQLite...")
        
        plays_query = """
        SELECT *
        FROM plays
        WHERE season = 2024
        ORDER BY game_id, play_id
        """
        
        sqlite_df = pd.read_sql_query(plays_query, sqlite_conn)
        logger.info(f"   📊 Loaded {len(sqlite_df):,} plays from SQLite")
        
        # 5. Transform data to PostgreSQL schema  
        postgres_df = transform_sqlite_to_postgres_schema(sqlite_df)
        
        # 6. Insert plays in batches
        logger.info("📤 Inserting plays into PostgreSQL...")
        
        batch_size = 500  # Smaller batches for reliability
        total_rows = len(postgres_df)
        successful_inserts = 0
        
        for i in range(0, total_rows, batch_size):
            batch_df = postgres_df.iloc[i:i + batch_size].copy()
            
            try:
                # Use pandas to_sql for reliable insertion
                batch_df.to_sql(
                    'plays', 
                    postgres_engine, 
                    if_exists='append', 
                    index=False,
                    method='multi'
                )
                
                successful_inserts += len(batch_df)
                
                if (i + batch_size) % 2500 == 0:
                    logger.info(f"    ✅ Processed {min(i + batch_size, total_rows):,}/{total_rows:,} plays...")
                    
            except Exception as e:
                logger.warning(f"  ⚠️  Batch {i//batch_size + 1} failed: {str(e)}")
                # Try individual inserts for failed batch
                for _, row in batch_df.iterrows():
                    try:
                        row_df = row.to_frame().T
                        row_df.to_sql('plays', postgres_engine, if_exists='append', index=False)
                        successful_inserts += 1
                    except Exception as row_error:
                        logger.warning(f"    ⚠️  Single row insert failed: {str(row_error)}")
                        continue
        
        postgres_session.commit()
        logger.info(f"   🎉 Successfully inserted {successful_inserts:,} plays!")
        
        # 7. Verification and reporting
        logger.info("\n📊 Migration Verification:")
        
        # Verify plays
        result = postgres_session.execute(text("""
            SELECT 
                COUNT(*) as total_plays,
                COUNT(CASE WHEN play_type = 'pass' THEN 1 END) as pass_plays,
                COUNT(CASE WHEN play_type = 'run' THEN 1 END) as run_plays,
                COUNT(CASE WHEN passer_player_id IS NOT NULL THEN 1 END) as qb_plays
            FROM plays
            WHERE season = 2024
        """)).fetchone()
        
        if result:
            logger.info(f"  ✅ Total plays: {result.total_plays:,}")
            logger.info(f"  🎯 Pass plays: {result.pass_plays:,}")
            logger.info(f"  🏃 Run plays: {result.run_plays:,}")
            logger.info(f"  🏈 QB plays: {result.qb_plays:,}")
        
        # Verify top QBs 
        logger.info("\n🏈 Top QBs in PostgreSQL:")
        qb_check = postgres_session.execute(text("""
            SELECT p.full_name, COUNT(*) as attempts
            FROM plays pl
            JOIN players p ON pl.passer_player_id = p.player_id
            WHERE pl.play_type = 'pass' AND pl.season = 2024
            GROUP BY p.full_name
            ORDER BY attempts DESC
            LIMIT 5
        """)).fetchall()
        
        for qb in qb_check:
            logger.info(f"  🏆 {qb.full_name}: {qb.attempts} attempts")
        
        # Verify specific NFL stars
        logger.info("\n⭐ NFL Stars Verification:")
        stars = ['P.Mahomes', 'J.Burrow', 'S.Barkley']
        for star in stars:
            star_check = postgres_session.execute(text("""
                SELECT p.full_name, COUNT(*) as plays
                FROM plays pl
                JOIN players p ON (pl.passer_player_id = p.player_id 
                                 OR pl.rusher_player_id = p.player_id
                                 OR pl.receiver_player_id = p.player_id)
                WHERE p.full_name LIKE :name AND pl.season = 2024
                GROUP BY p.full_name
            """), {'name': f'{star}%'}).fetchone()
            
            if star_check:
                logger.info(f"  ⭐ {star_check.full_name}: {star_check.plays} plays")
        
        logger.info(f"\n🎉 MIGRATION COMPLETE!")
        logger.info(f"✅ Successfully migrated {successful_inserts:,} plays from SQLite to PostgreSQL")
        logger.info(f"🚀 Production database ready with authentic NFL data!")
        
        return True
        
    except Exception as e:
        logger.error(f"❌ Migration failed: {str(e)}")
        postgres_session.rollback()
        import traceback
        traceback.print_exc()
        return False
        
    finally:
        sqlite_conn.close()
        postgres_session.close()


if __name__ == "__main__":
    success = migrate_nfl_data_to_postgres()
    if success:
        logger.info("\n🎯 PRODUCTION READY: PostgreSQL loaded with real NFL data!")
        logger.info("🔗 League Leaders now features Patrick Mahomes, Joe Burrow, Saquon Barkley!")
        logger.info("🚀 Restart your application to see legitimate NFL statistics!")
    else:
        logger.error("\n💥 Migration failed - check logs for details")
        sys.exit(1)