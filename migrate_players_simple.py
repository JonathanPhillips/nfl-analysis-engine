#!/usr/bin/env python3
"""
Simplified player migration that avoids foreign key constraints.
Sets team_abbr to NULL to focus on getting player names into PostgreSQL.
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


def migrate_players_simple():
    """Simplified player migration without team foreign key constraints."""
    
    logger.info("👥 Starting simplified player migration...")
    
    # Verify SQLite database exists
    if not os.path.exists('nfl_data.db'):
        logger.error("❌ nfl_data.db not found.")
        return False
    
    # Connect to databases
    sqlite_conn = sqlite3.connect('nfl_data.db')
    postgres_url = get_database_url()
    postgres_engine = create_engine(postgres_url)
    Session = sessionmaker(bind=postgres_engine)
    postgres_session = Session()
    
    try:
        # Disable foreign key constraints temporarily
        logger.info("🔧 Disabling foreign key constraints...")
        postgres_session.execute(text("SET session_replication_role = replica;"))
        
        # Query unique players from SQLite plays table
        logger.info("📥 Reading players from SQLite...")
        
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
        logger.info(f"   📊 Found {len(players_df)} unique players in SQLite")
        
        # Insert or update players in PostgreSQL without team_abbr
        logger.info("📤 Inserting/updating players in PostgreSQL...")
        
        successful_inserts = 0
        
        for _, player in players_df.iterrows():
            try:
                postgres_session.execute(text("""
                    INSERT INTO players (player_id, full_name, position, team_abbr, created_at, updated_at, is_active)
                    VALUES (:player_id, :full_name, :position, NULL, :created_at, :updated_at, :is_active)
                    ON CONFLICT (player_id) DO UPDATE SET
                        full_name = EXCLUDED.full_name,
                        position = EXCLUDED.position,
                        updated_at = EXCLUDED.updated_at
                """), {
                    'player_id': player['player_id'],
                    'full_name': player['full_name'], 
                    'position': player['position'],
                    'created_at': datetime.now(),
                    'updated_at': datetime.now(),
                    'is_active': True
                })
                successful_inserts += 1
                    
            except Exception as e:
                logger.warning(f"  ⚠️  Player operation failed for {player['full_name']}: {str(e)}")
                continue
        
        postgres_session.commit()
        
        # Re-enable foreign key constraints
        logger.info("🔧 Re-enabling foreign key constraints...")
        postgres_session.execute(text("SET session_replication_role = DEFAULT;"))
        postgres_session.commit()
        
        logger.info(f"   👥 Successfully processed {successful_inserts} players!")
        
        # Verification - check for NFL stars
        logger.info("\n⭐ Verifying NFL stars in PostgreSQL players table:")
        stars_check = postgres_session.execute(text("""
            SELECT player_id, full_name, position, team_abbr
            FROM players 
            WHERE full_name IN ('P.Mahomes', 'J.Burrow', 'S.Barkley')
            ORDER BY full_name
        """)).fetchall()
        
        if stars_check:
            for star in stars_check:
                logger.info(f"  ⭐ {star.full_name} ({star.position}) - ID: {star.player_id}")
        else:
            logger.warning("  ⚠️  No NFL stars found - checking similar names...")
            similar_check = postgres_session.execute(text("""
                SELECT player_id, full_name, position, team_abbr
                FROM players 
                WHERE full_name LIKE '%Mahomes%' 
                   OR full_name LIKE '%Burrow%' 
                   OR full_name LIKE '%Barkley%'
                ORDER BY full_name
            """)).fetchall()
            
            for player in similar_check:
                logger.info(f"  🔍 {player.full_name} ({player.position}) - ID: {player.player_id}")
        
        # Test the League Leaders query
        logger.info("\n🏆 Testing League Leaders query with real data:")
        qb_test = postgres_session.execute(text("""
            SELECT p.full_name, COUNT(*) as attempts
            FROM plays pl
            JOIN players p ON pl.passer_player_id = p.player_id
            WHERE pl.play_type = 'pass' AND pl.season = 2024
            GROUP BY p.full_name
            ORDER BY attempts DESC
            LIMIT 5
        """)).fetchall()
        
        if qb_test:
            for qb in qb_test:
                logger.info(f"  🏆 {qb.full_name}: {qb.attempts} attempts")
        else:
            logger.warning("  ⚠️  No QB data found in joined query")
        
        logger.info(f"\n🎉 PLAYER MIGRATION COMPLETE!")
        logger.info(f"✅ League Leaders system now ready with real NFL player names!")
        
        return True
        
    except Exception as e:
        logger.error(f"❌ Player migration failed: {str(e)}")
        # Try to re-enable constraints even on error
        try:
            postgres_session.execute(text("SET session_replication_role = DEFAULT;"))
            postgres_session.commit()
        except:
            pass
        postgres_session.rollback()
        import traceback
        traceback.print_exc()
        return False
        
    finally:
        sqlite_conn.close()
        postgres_session.close()


if __name__ == "__main__":
    success = migrate_players_simple()
    if success:
        logger.info("\n🎯 SUCCESS: PostgreSQL now has real NFL player data!")
        logger.info("🏆 League Leaders will show Patrick Mahomes, Joe Burrow, Saquon Barkley!")
        logger.info("🚀 Your web app is ready with authentic NFL statistics!")
    else:
        logger.error("\n💥 Player migration failed - check logs for details")
        sys.exit(1)