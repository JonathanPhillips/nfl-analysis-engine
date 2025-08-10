#!/usr/bin/env python3
"""
Fix score_differential calculation for all plays in the database.

The NFL data scientist identified that ALL 4,308 plays have score_differential = NULL,
which is causing NoneType comparison errors in the Insights page. This script calculates
and updates score_differential for all plays based on home/away scores and possession team.
"""

import os
import sys
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

# Add the src directory to Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from database.config import get_database_url

def fix_score_differential():
    """Calculate and update score_differential for all plays."""
    
    # Get database connection
    database_url = get_database_url()
    engine = create_engine(database_url)
    Session = sessionmaker(bind=engine)
    session = Session()
    
    try:
        print("🔧 Fixing score_differential calculation for all plays...")
        
        # First, let's see how many plays have NULL score_differential
        result = session.execute(text("SELECT COUNT(*) FROM plays WHERE score_differential IS NULL"))
        null_count = result.scalar()
        print(f"📊 Found {null_count:,} plays with NULL score_differential")
        
        if null_count == 0:
            print("✅ All plays already have score_differential calculated!")
            return True
            
        # Update score_differential based on game scores and possession team (posteam)
        # score_differential = possessing_team_score - opposing_team_score
        update_query = text("""
            UPDATE plays 
            SET score_differential = CASE 
                WHEN plays.posteam = games.home_team THEN 
                    COALESCE(games.home_score, 0) - COALESCE(games.away_score, 0)
                WHEN plays.posteam = games.away_team THEN 
                    COALESCE(games.away_score, 0) - COALESCE(games.home_score, 0)
                ELSE NULL
            END
            FROM games 
            WHERE plays.game_id = games.game_id
            AND plays.score_differential IS NULL
        """)
        
        result = session.execute(update_query)
        updated_count = result.rowcount
        session.commit()
        
        print(f"✅ Updated score_differential for {updated_count:,} plays")
        
        # Verify the fix
        result = session.execute(text("SELECT COUNT(*) FROM plays WHERE score_differential IS NOT NULL"))
        non_null_count = result.scalar()
        
        result = session.execute(text("SELECT COUNT(*) FROM plays"))
        total_count = result.scalar()
        
        print(f"📊 Verification: {non_null_count:,} of {total_count:,} plays now have score_differential")
        print(f"📊 Coverage: {(non_null_count/total_count)*100:.1f}%")
        
        # Show some sample score differentials
        print("\n📋 Sample score differentials:")
        result = session.execute(text("""
            SELECT p.posteam, p.score_differential, g.home_team, g.away_team, 
                   g.home_score, g.away_score
            FROM plays p 
            JOIN games g ON p.game_id = g.game_id 
            WHERE p.score_differential IS NOT NULL 
            LIMIT 5
        """))
        
        for row in result:
            print(f"  Team {row.posteam}: score_diff={row.score_differential} "
                  f"(Game: {row.home_team} {row.home_score} - {row.away_team} {row.away_score})")
        
        return True
        
    except Exception as e:
        print(f"❌ Error fixing score_differential: {e}")
        session.rollback()
        return False
        
    finally:
        session.close()

def verify_insights_fix():
    """Verify that the insights page will no longer have NoneType errors."""
    
    database_url = get_database_url()
    engine = create_engine(database_url)
    Session = sessionmaker(bind=engine)
    session = Session()
    
    try:
        print("\n🧪 Testing insights calculations that were failing...")
        
        # Test the specific comparison that was failing
        result = session.execute(text("""
            SELECT COUNT(*) as total_plays,
                   COUNT(CASE WHEN score_differential > 0 THEN 1 END) as leading_plays,
                   COUNT(CASE WHEN score_differential < 0 THEN 1 END) as trailing_plays,
                   COUNT(CASE WHEN score_differential = 0 THEN 1 END) as tied_plays
            FROM plays 
            WHERE score_differential IS NOT NULL
        """))
        
        row = result.fetchone()
        print(f"✅ Score differential analysis:")
        print(f"  Total plays: {row.total_plays:,}")
        print(f"  Leading plays: {row.leading_plays:,}")
        print(f"  Trailing plays: {row.trailing_plays:,}")  
        print(f"  Tied plays: {row.tied_plays:,}")
        
        return True
        
    except Exception as e:
        print(f"❌ Error verifying insights fix: {e}")
        return False
        
    finally:
        session.close()

if __name__ == "__main__":
    print("🚀 Starting score_differential fix...")
    
    success = fix_score_differential()
    if success:
        verify_insights_fix()
        print("\n🎉 Score differential fix completed successfully!")
        print("🔗 The Insights page should now work without NoneType errors.")
    else:
        print("\n💥 Score differential fix failed!")
        sys.exit(1)