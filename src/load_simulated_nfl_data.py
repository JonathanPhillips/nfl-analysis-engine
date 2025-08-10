#!/usr/bin/env python3
"""
Load simulated 2024 NFL data for League Leaders testing.

This script generates realistic NFL play-by-play data to populate the
League Leaders system without requiring nfl_data_py installation.
"""

import os
import sys
import random
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from datetime import datetime

# Add the project root to Python path
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from src.database.config import get_database_url

# Real 2024 NFL starting quarterbacks and their typical stats
NFL_QBS = [
    {"name": "Josh Allen", "team": "BUF", "id": "00-0034857"},
    {"name": "Lamar Jackson", "team": "BAL", "id": "00-0035228"},
    {"name": "Dak Prescott", "team": "DAL", "id": "00-0033077"},
    {"name": "Patrick Mahomes", "team": "KC", "id": "00-0034754"},
    {"name": "Joe Burrow", "team": "CIN", "id": "00-0036442"},
    {"name": "Justin Herbert", "team": "LAC", "id": "00-0036389"},
    {"name": "Tua Tagovailoa", "team": "MIA", "id": "00-0036355"},
    {"name": "Jalen Hurts", "team": "PHI", "id": "00-0036389"},
    {"name": "Aaron Rodgers", "team": "NYJ", "id": "00-0023459"},
    {"name": "Russell Wilson", "team": "PIT", "id": "00-0029263"},
]

# Real 2024 NFL starting running backs
NFL_RBS = [
    {"name": "Derrick Henry", "team": "BAL", "id": "00-0030506"},
    {"name": "Saquon Barkley", "team": "PHI", "id": "00-0034844"},
    {"name": "Christian McCaffrey", "team": "SF", "id": "00-0033284"},
    {"name": "Josh Jacobs", "team": "GB", "id": "00-0035710"},
    {"name": "Joe Mixon", "team": "HOU", "id": "00-0032869"},
    {"name": "Jonathan Taylor", "team": "IND", "id": "00-0036971"},
    {"name": "Alvin Kamara", "team": "NO", "id": "00-0033054"},
    {"name": "Bijan Robinson", "team": "ATL", "id": "00-0038475"},
    {"name": "Breece Hall", "team": "NYJ", "id": "00-0037650"},
    {"name": "Kenneth Walker III", "team": "SEA", "id": "00-0037653"},
]

# Real 2024 NFL wide receivers
NFL_WRS = [
    {"name": "Tyreek Hill", "team": "MIA", "id": "00-0032653"},
    {"name": "Davante Adams", "team": "LV", "id": "00-0031381"},
    {"name": "Cooper Kupp", "team": "LAR", "id": "00-0033536"},
    {"name": "Stefon Diggs", "team": "HOU", "id": "00-0031280"},
    {"name": "A.J. Brown", "team": "PHI", "id": "00-0035676"},
    {"name": "DeAndre Hopkins", "team": "TEN", "id": "00-0029671"},
    {"name": "Mike Evans", "team": "TB", "id": "00-0030506"},
    {"name": "Ja'Marr Chase", "team": "CIN", "id": "00-0036971"},
    {"name": "CeeDee Lamb", "team": "DAL", "id": "00-0036389"},
    {"name": "DK Metcalf", "team": "SEA", "id": "00-0035676"},
]


def load_simulated_nfl_data():
    """Load simulated 2024 NFL data for League Leaders testing."""
    
    # Get database connection
    database_url = get_database_url()
    engine = create_engine(database_url)
    Session = sessionmaker(bind=engine)
    session = Session()
    
    try:
        print("🏈 Loading simulated 2024 NFL data for League Leaders...")
        
        # Clear existing play data to avoid conflicts
        print("  🧹 Clearing existing play data...")
        session.execute(text("DELETE FROM plays WHERE season = 2024"))
        session.commit()
        
        # Insert QB play data
        print("  🎯 Generating QB passing plays...")
        for qb in NFL_QBS:
            # Generate 200-400 pass attempts per QB (realistic range)
            attempts = random.randint(200, 400)
            
            for i in range(attempts):
                # Realistic QB stats based on NFL averages
                completion_rate = random.uniform(0.58, 0.72)  # 58-72% completion
                is_complete = random.random() < completion_rate
                
                if is_complete:
                    yards = max(0, int(random.gauss(8.5, 12)))  # ~8.5 Y/A average
                    is_td = random.random() < 0.04  # ~4% TD rate
                    is_int = False
                    epa = random.uniform(0.05, 0.35)  # Positive EPA for completions
                else:
                    yards = 0
                    is_td = False
                    is_int = random.random() < 0.015  # ~1.5% INT rate on incompletions
                    epa = random.uniform(-0.8, -0.2)  # Negative EPA for incompletions
                
                # Insert play
                play_data = {
                    'play_id': f"{qb['team']}_pass_{i+1}",
                    'game_id': f"2024_week_{random.randint(1, 17)}_{qb['team']}",
                    'season': 2024,
                    'week': random.randint(1, 17),
                    'posteam': qb['team'],
                    'play_type': 'pass',
                    'passer_player_id': qb['id'],
                    'yards_gained': yards,
                    'pass_touchdown': is_td,
                    'interception': is_int,
                    'epa': epa,
                    'desc': f"{'COMPLETE' if is_complete else 'INCOMPLETE'} pass for {yards} yards",
                    'created_at': datetime.now(),
                    'updated_at': datetime.now(),
                    'is_active': True
                }
                
                session.execute(text("""
                    INSERT INTO plays (
                        play_id, game_id, season, week, posteam, play_type,
                        passer_player_id, yards_gained, pass_touchdown, 
                        interception, epa, "desc", created_at, updated_at, is_active
                    ) VALUES (
                        :play_id, :game_id, :season, :week, :posteam, :play_type,
                        :passer_player_id, :yards_gained, :pass_touchdown,
                        :interception, :epa, :desc, :created_at, :updated_at, :is_active
                    )
                """), play_data)
            
            print(f"    ✅ {qb['name']} ({qb['team']}): {attempts} attempts")
        
        # Insert RB play data
        print("  🏃 Generating RB rushing plays...")
        for rb in NFL_RBS:
            # Generate 150-300 carries per RB
            carries = random.randint(150, 300)
            
            for i in range(carries):
                # Realistic RB stats
                yards = max(-5, int(random.gauss(4.2, 8)))  # ~4.2 YPC average
                is_td = random.random() < 0.06  # ~6% TD rate
                epa = random.uniform(-0.1, 0.2) if yards >= 0 else random.uniform(-0.5, -0.1)
                
                play_data = {
                    'play_id': f"{rb['team']}_run_{i+1}",
                    'game_id': f"2024_week_{random.randint(1, 17)}_{rb['team']}",
                    'season': 2024,
                    'week': random.randint(1, 17),
                    'posteam': rb['team'],
                    'play_type': 'run',
                    'rusher_player_id': rb['id'],
                    'yards_gained': yards,
                    'rush_touchdown': is_td,
                    'epa': epa,
                    'desc': f"Rush for {yards} yards"
                }
                
                session.execute(text("""
                    INSERT INTO plays (
                        play_id, game_id, season, week, posteam, play_type,
                        rusher_player_id, yards_gained, rush_touchdown, 
                        epa, "desc"
                    ) VALUES (
                        :play_id, :game_id, :season, :week, :posteam, :play_type,
                        :rusher_player_id, :yards_gained, :rush_touchdown,
                        :epa, :desc
                    )
                """), play_data)
            
            print(f"    ✅ {rb['name']} ({rb['team']}): {carries} carries")
        
        # Insert WR receiving data
        print("  🙌 Generating WR receiving plays...")
        for wr in NFL_WRS:
            # Generate 100-180 targets per WR
            targets = random.randint(100, 180)
            
            for i in range(targets):
                # Realistic WR stats
                catch_rate = random.uniform(0.60, 0.75)  # 60-75% catch rate
                is_catch = random.random() < catch_rate
                
                if is_catch:
                    yards = max(0, int(random.gauss(12, 15)))  # ~12 Y/R average
                    is_td = random.random() < 0.08  # ~8% TD rate
                    epa = random.uniform(0.1, 0.4)
                    desc = f"COMPLETE pass for {yards} yards"
                else:
                    yards = 0
                    is_td = False
                    epa = random.uniform(-0.6, -0.1)
                    desc = "INCOMPLETE pass"
                
                play_data = {
                    'play_id': f"{wr['team']}_target_{i+1}",
                    'game_id': f"2024_week_{random.randint(1, 17)}_{wr['team']}",
                    'season': 2024,
                    'week': random.randint(1, 17),
                    'posteam': wr['team'],
                    'play_type': 'pass',
                    'receiver_player_id': wr['id'],
                    'yards_gained': yards,
                    'pass_touchdown': is_td,
                    'epa': epa,
                    'desc': desc
                }
                
                session.execute(text("""
                    INSERT INTO plays (
                        play_id, game_id, season, week, posteam, play_type,
                        receiver_player_id, yards_gained, pass_touchdown,
                        epa, "desc"
                    ) VALUES (
                        :play_id, :game_id, :season, :week, :posteam, :play_type,
                        :receiver_player_id, :yards_gained, :pass_touchdown,
                        :epa, :desc
                    )
                """), play_data)
            
            print(f"    ✅ {wr['name']} ({wr['team']}): {targets} targets")
        
        session.commit()
        
        # Update player records with current data
        print("  👥 Updating player records...")
        all_players = NFL_QBS + NFL_RBS + NFL_WRS
        
        for player in all_players:
            session.execute(text("""
                INSERT INTO players (player_id, full_name, team_abbr, position)
                VALUES (:id, :name, :team, :position)
                ON CONFLICT (player_id) 
                DO UPDATE SET 
                    full_name = :name,
                    team_abbr = :team,
                    position = :position
            """), {
                'id': player['id'],
                'name': player['name'],
                'team': player['team'],
                'position': 'QB' if player in NFL_QBS else 'RB' if player in NFL_RBS else 'WR'
            })
        
        session.commit()
        
        # Verification
        print("\n📊 Data loading complete! Verification:")
        result = session.execute(text("""
            SELECT 
                COUNT(*) as total_plays,
                COUNT(CASE WHEN passer_player_id IS NOT NULL THEN 1 END) as qb_plays,
                COUNT(CASE WHEN rusher_player_id IS NOT NULL THEN 1 END) as rb_plays,
                COUNT(CASE WHEN receiver_player_id IS NOT NULL THEN 1 END) as wr_plays
            FROM plays
            WHERE season = 2024
        """)).fetchone()
        
        print(f"  📈 Total plays: {result.total_plays:,}")
        print(f"  🎯 QB plays: {result.qb_plays:,}")
        print(f"  🏃 RB plays: {result.rb_plays:,}")
        print(f"  🙌 WR plays: {result.wr_plays:,}")
        
        print("\n🏆 Ready for League Leaders with realistic NFL statistics!")
        return True
        
    except Exception as e:
        print(f"❌ Error loading simulated data: {e}")
        session.rollback()
        import traceback
        traceback.print_exc()
        return False
        
    finally:
        session.close()


if __name__ == "__main__":
    print("🚀 Starting simulated NFL data generation...")
    
    success = load_simulated_nfl_data()
    if success:
        print("\n🎉 Simulated NFL data loaded successfully!")
        print("🔗 Visit http://localhost:8000/web/league-leaders to see the results!")
    else:
        print("\n💥 Data loading failed!")
        sys.exit(1)