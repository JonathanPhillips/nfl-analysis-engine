#!/usr/bin/env python3
"""Populate teams table with basic NFL team data."""

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from src.models.team import TeamModel
import os

# Team data for all 32 NFL teams
NFL_TEAMS = [
    {'team_abbr': 'ARI', 'team_name': 'Arizona', 'team_nick': 'Cardinals', 'team_conf': 'NFC', 'team_division': 'West'},
    {'team_abbr': 'ATL', 'team_name': 'Atlanta', 'team_nick': 'Falcons', 'team_conf': 'NFC', 'team_division': 'South'},
    {'team_abbr': 'BAL', 'team_name': 'Baltimore', 'team_nick': 'Ravens', 'team_conf': 'AFC', 'team_division': 'North'},
    {'team_abbr': 'BUF', 'team_name': 'Buffalo', 'team_nick': 'Bills', 'team_conf': 'AFC', 'team_division': 'East'},
    {'team_abbr': 'CAR', 'team_name': 'Carolina', 'team_nick': 'Panthers', 'team_conf': 'NFC', 'team_division': 'South'},
    {'team_abbr': 'CHI', 'team_name': 'Chicago', 'team_nick': 'Bears', 'team_conf': 'NFC', 'team_division': 'North'},
    {'team_abbr': 'CIN', 'team_name': 'Cincinnati', 'team_nick': 'Bengals', 'team_conf': 'AFC', 'team_division': 'North'},
    {'team_abbr': 'CLE', 'team_name': 'Cleveland', 'team_nick': 'Browns', 'team_conf': 'AFC', 'team_division': 'North'},
    {'team_abbr': 'DAL', 'team_name': 'Dallas', 'team_nick': 'Cowboys', 'team_conf': 'NFC', 'team_division': 'East'},
    {'team_abbr': 'DEN', 'team_name': 'Denver', 'team_nick': 'Broncos', 'team_conf': 'AFC', 'team_division': 'West'},
    {'team_abbr': 'DET', 'team_name': 'Detroit', 'team_nick': 'Lions', 'team_conf': 'NFC', 'team_division': 'North'},
    {'team_abbr': 'GB', 'team_name': 'Green Bay', 'team_nick': 'Packers', 'team_conf': 'NFC', 'team_division': 'North'},
    {'team_abbr': 'HOU', 'team_name': 'Houston', 'team_nick': 'Texans', 'team_conf': 'AFC', 'team_division': 'South'},
    {'team_abbr': 'IND', 'team_name': 'Indianapolis', 'team_nick': 'Colts', 'team_conf': 'AFC', 'team_division': 'South'},
    {'team_abbr': 'JAX', 'team_name': 'Jacksonville', 'team_nick': 'Jaguars', 'team_conf': 'AFC', 'team_division': 'South'},
    {'team_abbr': 'KC', 'team_name': 'Kansas City', 'team_nick': 'Chiefs', 'team_conf': 'AFC', 'team_division': 'West'},
    {'team_abbr': 'LV', 'team_name': 'Las Vegas', 'team_nick': 'Raiders', 'team_conf': 'AFC', 'team_division': 'West'},
    {'team_abbr': 'LAC', 'team_name': 'Los Angeles', 'team_nick': 'Chargers', 'team_conf': 'AFC', 'team_division': 'West'},
    {'team_abbr': 'LAR', 'team_name': 'Los Angeles', 'team_nick': 'Rams', 'team_conf': 'NFC', 'team_division': 'West'},
    {'team_abbr': 'MIA', 'team_name': 'Miami', 'team_nick': 'Dolphins', 'team_conf': 'AFC', 'team_division': 'East'},
    {'team_abbr': 'MIN', 'team_name': 'Minnesota', 'team_nick': 'Vikings', 'team_conf': 'NFC', 'team_division': 'North'},
    {'team_abbr': 'NE', 'team_name': 'New England', 'team_nick': 'Patriots', 'team_conf': 'AFC', 'team_division': 'East'},
    {'team_abbr': 'NO', 'team_name': 'New Orleans', 'team_nick': 'Saints', 'team_conf': 'NFC', 'team_division': 'South'},
    {'team_abbr': 'NYG', 'team_name': 'New York', 'team_nick': 'Giants', 'team_conf': 'NFC', 'team_division': 'East'},
    {'team_abbr': 'NYJ', 'team_name': 'New York', 'team_nick': 'Jets', 'team_conf': 'AFC', 'team_division': 'East'},
    {'team_abbr': 'PHI', 'team_name': 'Philadelphia', 'team_nick': 'Eagles', 'team_conf': 'NFC', 'team_division': 'East'},
    {'team_abbr': 'PIT', 'team_name': 'Pittsburgh', 'team_nick': 'Steelers', 'team_conf': 'AFC', 'team_division': 'North'},
    {'team_abbr': 'SF', 'team_name': 'San Francisco', 'team_nick': '49ers', 'team_conf': 'NFC', 'team_division': 'West'},
    {'team_abbr': 'SEA', 'team_name': 'Seattle', 'team_nick': 'Seahawks', 'team_conf': 'NFC', 'team_division': 'West'},
    {'team_abbr': 'TB', 'team_name': 'Tampa Bay', 'team_nick': 'Buccaneers', 'team_conf': 'NFC', 'team_division': 'South'},
    {'team_abbr': 'TEN', 'team_name': 'Tennessee', 'team_nick': 'Titans', 'team_conf': 'AFC', 'team_division': 'South'},
    {'team_abbr': 'WAS', 'team_name': 'Washington', 'team_nick': 'Commanders', 'team_conf': 'NFC', 'team_division': 'East'}
]

def populate_teams():
    """Populate teams table."""
    database_url = os.getenv('DATABASE_URL', 'sqlite:///./nfl_data.db')
    engine = create_engine(database_url)
    Session = sessionmaker(bind=engine)
    session = Session()
    
    try:
        # Clear existing teams
        session.query(TeamModel).delete()
        
        # Add all teams
        for team_data in NFL_TEAMS:
            team = TeamModel(**team_data)
            session.add(team)
        
        session.commit()
        print(f"✅ Added {len(NFL_TEAMS)} NFL teams to the database")
        
        # Verify
        count = session.query(TeamModel).count()
        print(f"📊 Total teams in database: {count}")
        
    except Exception as e:
        print(f"❌ Error populating teams: {e}")
        session.rollback()
    finally:
        session.close()

if __name__ == "__main__":
    populate_teams()