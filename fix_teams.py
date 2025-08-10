#!/usr/bin/env python3
"""Fix team data - remove duplicates and correct divisions."""

import requests

# Correct NFL team structure as of 2024
CORRECT_TEAMS = {
    # AFC East
    "BUF": {"name": "Buffalo", "nick": "Bills", "conf": "AFC", "div": "East"},
    "MIA": {"name": "Miami", "nick": "Dolphins", "conf": "AFC", "div": "East"},
    "NE": {"name": "New England", "nick": "Patriots", "conf": "AFC", "div": "East"},
    "NYJ": {"name": "New York", "nick": "Jets", "conf": "AFC", "div": "East"},
    
    # AFC North  
    "BAL": {"name": "Baltimore", "nick": "Ravens", "conf": "AFC", "div": "North"},
    "CIN": {"name": "Cincinnati", "nick": "Bengals", "conf": "AFC", "div": "North"},
    "CLE": {"name": "Cleveland", "nick": "Browns", "conf": "AFC", "div": "North"},
    "PIT": {"name": "Pittsburgh", "nick": "Steelers", "conf": "AFC", "div": "North"},
    
    # AFC South
    "HOU": {"name": "Houston", "nick": "Texans", "conf": "AFC", "div": "South"},
    "IND": {"name": "Indianapolis", "nick": "Colts", "conf": "AFC", "div": "South"},
    "JAX": {"name": "Jacksonville", "nick": "Jaguars", "conf": "AFC", "div": "South"},
    "TEN": {"name": "Tennessee", "nick": "Titans", "conf": "AFC", "div": "South"},
    
    # AFC West
    "DEN": {"name": "Denver", "nick": "Broncos", "conf": "AFC", "div": "West"},
    "KC": {"name": "Kansas City", "nick": "Chiefs", "conf": "AFC", "div": "West"},
    "LV": {"name": "Las Vegas", "nick": "Raiders", "conf": "AFC", "div": "West"},
    "LAC": {"name": "Los Angeles", "nick": "Chargers", "conf": "AFC", "div": "West"},
    
    # NFC East
    "DAL": {"name": "Dallas", "nick": "Cowboys", "conf": "NFC", "div": "East"},
    "NYG": {"name": "New York", "nick": "Giants", "conf": "NFC", "div": "East"},
    "PHI": {"name": "Philadelphia", "nick": "Eagles", "conf": "NFC", "div": "East"},
    "WAS": {"name": "Washington", "nick": "Commanders", "conf": "NFC", "div": "East"},
    
    # NFC North
    "CHI": {"name": "Chicago", "nick": "Bears", "conf": "NFC", "div": "North"},
    "DET": {"name": "Detroit", "nick": "Lions", "conf": "NFC", "div": "North"},
    "GB": {"name": "Green Bay", "nick": "Packers", "conf": "NFC", "div": "North"},
    "MIN": {"name": "Minnesota", "nick": "Vikings", "conf": "NFC", "div": "North"},
    
    # NFC South
    "ATL": {"name": "Atlanta", "nick": "Falcons", "conf": "NFC", "div": "South"},
    "CAR": {"name": "Carolina", "nick": "Panthers", "conf": "NFC", "div": "South"},
    "NO": {"name": "New Orleans", "nick": "Saints", "conf": "NFC", "div": "South"},
    "TB": {"name": "Tampa Bay", "nick": "Buccaneers", "conf": "NFC", "div": "South"},
    
    # NFC West
    "ARI": {"name": "Arizona", "nick": "Cardinals", "conf": "NFC", "div": "West"},
    "LAR": {"name": "Los Angeles", "nick": "Rams", "conf": "NFC", "div": "West"},
    "SF": {"name": "San Francisco", "nick": "49ers", "conf": "NFC", "div": "West"},
    "SEA": {"name": "Seattle", "nick": "Seahawks", "conf": "NFC", "div": "West"},
}

def cleanup_teams():
    """Clean up team data by removing old/duplicate teams and fixing divisions."""
    base_url = "http://localhost:8004"
    
    print("🔧 Cleaning up NFL team data...")
    
    # First, get all current teams
    response = requests.get(f"{base_url}/api/v1/teams/")
    current_teams = response.json()['teams']
    
    print(f"Found {len(current_teams)} teams in database")
    
    # Identify teams to delete (old abbreviations)
    old_teams = ["OAK", "SD", "LA", "STL"]  # Old team abbreviations
    teams_to_delete = []
    teams_to_update = []
    
    for team in current_teams:
        abbr = team['team_abbr']
        if abbr in old_teams:
            teams_to_delete.append(team)
            print(f"❌ Will delete old team: {abbr} - {team['team_name']} {team['team_nick']}")
        elif abbr in CORRECT_TEAMS:
            # Check if team info needs updating
            correct = CORRECT_TEAMS[abbr]
            if (team['team_conf'] != correct['conf'] or 
                team['team_division'] != correct['div']):
                teams_to_update.append((team, correct))
                print(f"🔄 Will update {abbr}: {team['team_conf']} {team['team_division']} → {correct['conf']} {correct['div']}")
    
    # Delete old teams
    for team in teams_to_delete:
        try:
            delete_response = requests.delete(f"{base_url}/api/v1/teams/{team['id']}")
            if delete_response.status_code == 200:
                print(f"✅ Deleted {team['team_abbr']}")
            else:
                print(f"❌ Failed to delete {team['team_abbr']}: {delete_response.text}")
        except Exception as e:
            print(f"❌ Error deleting {team['team_abbr']}: {e}")
    
    # Update incorrect divisions
    for team, correct in teams_to_update:
        try:
            update_data = {
                "team_name": correct['name'],
                "team_nick": correct['nick'], 
                "team_conf": correct['conf'],
                "team_division": correct['div']
            }
            update_response = requests.put(
                f"{base_url}/api/v1/teams/{team['id']}", 
                json=update_data
            )
            if update_response.status_code == 200:
                print(f"✅ Updated {team['team_abbr']} to {correct['conf']} {correct['div']}")
            else:
                print(f"❌ Failed to update {team['team_abbr']}: {update_response.text}")
        except Exception as e:
            print(f"❌ Error updating {team['team_abbr']}: {e}")
    
    # Verify final count
    response = requests.get(f"{base_url}/api/v1/teams/")
    final_teams = response.json()['teams']
    print(f"\n🏆 Final team count: {len(final_teams)}")
    
    # Show divisions
    divisions = {}
    for team in final_teams:
        conf_div = f"{team['team_conf']} {team['team_division']}"
        if conf_div not in divisions:
            divisions[conf_div] = []
        divisions[conf_div].append(team['team_abbr'])
    
    for div, teams in sorted(divisions.items()):
        print(f"{div}: {', '.join(sorted(teams))} ({len(teams)} teams)")

if __name__ == "__main__":
    cleanup_teams()