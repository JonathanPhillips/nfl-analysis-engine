"""Data mapping utilities for converting nfl_data_py data to our models."""

import logging
from typing import Dict, Any, List, Optional, Union
from datetime import datetime, date
import pandas as pd
from decimal import Decimal
from src.models.team import TeamCreate, NFL_TEAMS, get_team_division
from src.models.player import PlayerCreate, parse_height_string
from src.models.game import GameCreate
from src.models.play import PlayCreate

logger = logging.getLogger(__name__)


class DataMapper:
    """Maps nfl_data_py data structures to our Pydantic models."""
    
    def __init__(self):
        """Initialize data mapper."""
        self._team_cache: Dict[str, Dict[str, Any]] = {}
        self._setup_team_cache()
    
    def _setup_team_cache(self) -> None:
        """Set up team mapping cache."""
        try:
            for conf, divisions in NFL_TEAMS.items():
                for div, teams in divisions.items():
                    for team in teams:
                        self._team_cache[team] = {
                            'team_conf': conf,
                            'team_division': div
                        }
            logger.info(f"Set up team cache with {len(self._team_cache)} teams")
        except Exception as e:
            logger.error(f"Failed to setup team cache: {e}")
    
    def map_teams_data(self, teams_df: pd.DataFrame) -> List[TeamCreate]:
        """Map nfl_data_py teams data to TeamCreate models.
        
        Args:
            teams_df: DataFrame from nfl.import_team_desc()
            
        Returns:
            List of TeamCreate models
        """
        teams = []
        
        for _, row in teams_df.iterrows():
            try:
                team_abbr = str(row.get('team_abbr', '')).strip().upper()
                if not team_abbr:
                    continue
                
                # Get conference and division from our cache
                team_info = self._team_cache.get(team_abbr, {})
                
                team_data = {
                    'team_abbr': team_abbr,
                    'team_name': str(row.get('team_name', '')).strip(),
                    'team_nick': str(row.get('team_nick', '')).strip(),
                    'team_conf': team_info.get('team_conf', 'NFC'),  # Default fallback
                    'team_division': team_info.get('team_division', 'North'),  # Default fallback
                }
                
                # Optional fields
                if 'team_color' in row and pd.notna(row['team_color']):
                    team_data['team_color'] = str(row['team_color']).strip()
                
                if 'team_color2' in row and pd.notna(row['team_color2']):
                    team_data['team_color2'] = str(row['team_color2']).strip()
                
                if 'team_logo_espn' in row and pd.notna(row['team_logo_espn']):
                    team_data['team_logo_espn'] = str(row['team_logo_espn']).strip()
                
                if 'team_logo_wikipedia' in row and pd.notna(row['team_logo_wikipedia']):
                    team_data['team_logo_wikipedia'] = str(row['team_logo_wikipedia']).strip()
                
                team = TeamCreate(**team_data)
                teams.append(team)
                
            except Exception as e:
                logger.warning(f"Failed to map team row: {e}")
                continue
        
        logger.info(f"Mapped {len(teams)} teams")
        return teams
    
    def map_players_data(self, players_df: pd.DataFrame) -> List[PlayerCreate]:
        """Map nfl_data_py players data to PlayerCreate models.
        
        Args:
            players_df: DataFrame from nfl.import_rosters()
            
        Returns:
            List of PlayerCreate models
        """
        players = []
        
        for _, row in players_df.iterrows():
            try:
                # Use gsis_id as player_id (primary identifier)
                player_id = str(row.get('gsis_id', '')).strip()
                if not player_id:
                    continue
                
                # Get display_name as full_name
                full_name = str(row.get('display_name', '')).strip()
                if not full_name:
                    continue
                
                player_data = {
                    'player_id': player_id,
                    'full_name': full_name
                }
                
                # Optional fields with validation
                if 'gsis_id' in row and pd.notna(row['gsis_id']):
                    player_data['gsis_id'] = str(row['gsis_id']).strip()
                
                # Improved team mapping with priority order
                # Priority: roster team > merged team > fallback teams  
                team_abbr = None
                for team_col in ['team', 'team_roster', 'latest_team', 'team_player']:
                    if team_col in row and pd.notna(row[team_col]):
                        team_abbr = str(row[team_col]).strip().upper()
                        break
                
                # Map old team abbreviations to current ones
                team_mapping = {
                    'LA': 'LAR',   # Los Angeles Rams
                    'OAK': 'LV',   # Oakland Raiders -> Las Vegas Raiders  
                    'SD': 'LAC',   # San Diego Chargers -> Los Angeles Chargers
                    'STL': 'LAR'   # St. Louis Rams -> Los Angeles Rams
                }
                
                if team_abbr and team_abbr != 'UNK' and team_abbr != 'NA':
                    # Apply team mapping
                    if team_abbr in team_mapping:
                        team_abbr = team_mapping[team_abbr]
                    player_data['team_abbr'] = team_abbr
                
                # Improved position mapping with priority order
                # Priority: roster position > merged position > fallback positions
                position = None
                
                # Try primary position sources first
                for pos_col in ['position', 'position_roster']:
                    if pos_col in row and pd.notna(row[pos_col]):
                        position = str(row[pos_col]).strip().upper()
                        break
                
                # Fallback to other position columns if needed
                if not position:
                    for pos_col in ['position_player', 'position_x', 'position_y', 'ngs_position']:
                        if pos_col in row and pd.notna(row[pos_col]):
                            position = str(row[pos_col]).strip().upper()
                            break
                
                if position and position not in ['NA', 'NULL', '']:
                    player_data['position'] = position
                
                # Improved jersey number mapping with priority order
                for jersey_col in ['jersey_number', 'jersey_number_roster', 'jersey_number_player', 'jersey_number_x', 'jersey_number_y']:
                    if jersey_col in row and pd.notna(row[jersey_col]):
                        try:
                            jersey = int(row[jersey_col])
                            if 0 <= jersey <= 99:
                                player_data['jersey_number'] = jersey
                                break
                        except (ValueError, TypeError):
                            continue
                
                # Height handling
                if 'height' in row and pd.notna(row['height']):
                    height_str = str(row['height']).strip()
                    height_inches = parse_height_string(height_str)
                    if height_inches:
                        player_data['height'] = height_inches
                
                # Weight handling
                if 'weight' in row and pd.notna(row['weight']):
                    try:
                        weight = int(row['weight'])
                        if 150 <= weight <= 400:
                            player_data['weight'] = weight
                    except (ValueError, TypeError):
                        pass
                
                # Age handling
                if 'age' in row and pd.notna(row['age']):
                    try:
                        age = int(row['age'])
                        if 18 <= age <= 50:
                            player_data['age'] = age
                    except (ValueError, TypeError):
                        pass
                
                # Rookie year - try different column names
                for rookie_col in ['rookie_season', 'rookie_year']:
                    if rookie_col in row and pd.notna(row[rookie_col]):
                        try:
                            rookie_year = int(row[rookie_col])
                            if 1920 <= rookie_year <= datetime.now().year:
                                player_data['rookie_year'] = rookie_year
                                break
                        except (ValueError, TypeError):
                            continue
                
                # Draft information
                if 'draft_year' in row and pd.notna(row['draft_year']):
                    try:
                        draft_year = int(row['draft_year'])
                        if 1920 <= draft_year <= datetime.now().year:
                            player_data['draft_year'] = draft_year
                    except (ValueError, TypeError):
                        pass
                
                if 'draft_round' in row and pd.notna(row['draft_round']):
                    try:
                        draft_round = int(row['draft_round'])
                        if 1 <= draft_round <= 10:
                            player_data['draft_round'] = draft_round
                    except (ValueError, TypeError):
                        pass
                
                if 'draft_pick' in row and pd.notna(row['draft_pick']):
                    try:
                        draft_pick = int(row['draft_pick'])
                        if 1 <= draft_pick <= 300:
                            player_data['draft_pick'] = draft_pick
                    except (ValueError, TypeError):
                        pass
                
                if 'draft_team' in row and pd.notna(row['draft_team']):
                    draft_team = str(row['draft_team']).strip().upper()
                    if draft_team and len(draft_team) <= 3:
                        player_data['draft_team'] = draft_team
                
                # Headshot URL
                if 'headshot' in row and pd.notna(row['headshot']):
                    headshot = str(row['headshot']).strip()
                    if headshot and headshot.startswith('http'):
                        player_data['headshot_url'] = headshot
                
                # College - try different column names
                for college_col in ['college_name', 'college']:
                    if college_col in row and pd.notna(row[college_col]):
                        player_data['college'] = str(row[college_col]).strip()
                        break
                
                # Years of experience - try different column names
                for years_col in ['years_of_experience', 'years_exp']:
                    if years_col in row and pd.notna(row[years_col]):
                        try:
                            years_exp = int(row[years_col])
                            if 0 <= years_exp <= 30:
                                player_data['years_exp'] = years_exp
                                break
                        except (ValueError, TypeError):
                            continue
                
                # Status
                if 'status' in row and pd.notna(row['status']):
                    status = str(row['status']).strip().lower()
                    # Map from nfl_data_py status codes to our status values
                    status_mapping = {
                        'act': 'active',
                        'active': 'active',
                        'ina': 'injured', 
                        'injured': 'injured',
                        'res': 'retired',
                        'retired': 'retired',
                        'non': 'practice_squad',
                        'practice_squad': 'practice_squad',
                        'udf': 'suspended',
                        'suspended': 'suspended'
                    }
                    if status in status_mapping:
                        player_data['status'] = status_mapping[status]
                
                player = PlayerCreate(**player_data)
                players.append(player)
                
            except Exception as e:
                logger.warning(f"Failed to map player row: {e}")
                continue
        
        logger.info(f"Mapped {len(players)} players")
        return players
    
    def map_games_data(self, games_df: pd.DataFrame) -> List[GameCreate]:
        """Map nfl_data_py games data to GameCreate models.
        
        Args:
            games_df: DataFrame from nfl.import_schedules()
            
        Returns:
            List of GameCreate models
        """
        games = []
        
        for _, row in games_df.iterrows():
            try:
                game_id = str(row.get('game_id', '')).strip()
                season = row.get('season')
                # Column is 'game_type' not 'season_type' in nfl_data_py
                season_type = str(row.get('game_type', '')).strip().upper()
                game_date = row.get('gameday')
                home_team = str(row.get('home_team', '')).strip().upper()
                away_team = str(row.get('away_team', '')).strip().upper()
                
                # Validate required fields
                if not all([game_id, season, season_type, game_date, home_team, away_team]):
                    continue
                
                # Parse game date
                if isinstance(game_date, str):
                    try:
                        game_date = datetime.strptime(game_date, '%Y-%m-%d').date()
                    except ValueError:
                        continue
                elif isinstance(game_date, pd.Timestamp):
                    game_date = game_date.date()
                elif not isinstance(game_date, date):
                    continue
                
                game_data = {
                    'game_id': game_id,
                    'season': int(season),
                    'season_type': season_type,
                    'game_date': game_date,
                    'home_team': home_team,
                    'away_team': away_team
                }
                
                # Optional fields
                if 'old_game_id' in row and pd.notna(row['old_game_id']):
                    game_data['old_game_id'] = str(row['old_game_id']).strip()
                
                if 'week' in row and pd.notna(row['week']):
                    try:
                        week = int(row['week'])
                        if 1 <= week <= 22:
                            game_data['week'] = week
                    except (ValueError, TypeError):
                        pass
                
                # Kickoff time
                if 'gametime' in row and pd.notna(row['gametime']):
                    try:
                        time_str = str(row['gametime']).strip()
                        # Parse time (format might be "1:00PM" or "13:00")
                        if ':' in time_str:
                            game_data['kickoff_time'] = datetime.strptime(time_str, '%H:%M').time()
                    except ValueError:
                        pass
                
                # Scores
                if 'home_score' in row and pd.notna(row['home_score']):
                    try:
                        home_score = int(row['home_score'])
                        if 0 <= home_score <= 100:
                            game_data['home_score'] = home_score
                    except (ValueError, TypeError):
                        pass
                
                if 'away_score' in row and pd.notna(row['away_score']):
                    try:
                        away_score = int(row['away_score'])
                        if 0 <= away_score <= 100:
                            game_data['away_score'] = away_score
                    except (ValueError, TypeError):
                        pass
                
                # Game conditions
                if 'roof' in row and pd.notna(row['roof']):
                    roof = str(row['roof']).strip().lower()
                    if roof in ['dome', 'outdoors', 'closed', 'open', 'retractable']:
                        game_data['roof'] = roof
                
                if 'surface' in row and pd.notna(row['surface']):
                    surface = str(row['surface']).strip().lower()
                    game_data['surface'] = surface
                
                if 'temp' in row and pd.notna(row['temp']):
                    try:
                        temp = int(row['temp'])
                        if -20 <= temp <= 120:
                            game_data['temp'] = temp
                    except (ValueError, TypeError):
                        pass
                
                if 'wind' in row and pd.notna(row['wind']):
                    try:
                        wind = int(row['wind'])
                        if 0 <= wind <= 50:
                            game_data['wind'] = wind
                    except (ValueError, TypeError):
                        pass
                
                # Betting lines
                if 'spread_line' in row and pd.notna(row['spread_line']):
                    try:
                        spread = float(row['spread_line'])
                        if -30.0 <= spread <= 30.0:
                            game_data['home_spread'] = spread
                    except (ValueError, TypeError):
                        pass
                
                if 'total_line' in row and pd.notna(row['total_line']):
                    try:
                        total = float(row['total_line'])
                        if 20.0 <= total <= 80.0:
                            game_data['total_line'] = total
                    except (ValueError, TypeError):
                        pass
                
                # Game finished status
                if 'home_score' in game_data and 'away_score' in game_data:
                    game_data['game_finished'] = True
                
                game = GameCreate(**game_data)
                games.append(game)
                
            except Exception as e:
                logger.warning(f"Failed to map game row: {e}")
                continue
        
        logger.info(f"Mapped {len(games)} games")
        return games
    
    def map_plays_data(self, plays_df: pd.DataFrame, batch_size: int = 1000) -> List[List[PlayCreate]]:
        """Map nfl_data_py plays data to PlayCreate models in batches.
        
        Args:
            plays_df: DataFrame from nfl.import_pbp_data()
            batch_size: Size of each batch
            
        Returns:
            List of batches, each containing PlayCreate models
        """
        batches = []
        current_batch = []
        
        for i, row in plays_df.iterrows():
            try:
                play_id = str(row.get('play_id', '')).strip()
                game_id = str(row.get('game_id', '')).strip()
                season = row.get('season')
                
                # Validate required fields
                if not all([play_id, game_id, season]):
                    continue
                
                play_data = {
                    'play_id': play_id,
                    'game_id': game_id,
                    'season': int(season)
                }
                
                # Optional fields with validation
                if 'week' in row and pd.notna(row['week']):
                    try:
                        week = int(row['week'])
                        if 1 <= week <= 22:
                            play_data['week'] = week
                    except (ValueError, TypeError):
                        pass
                
                # Team fields
                if 'posteam' in row and pd.notna(row['posteam']):
                    posteam = str(row['posteam']).strip().upper()
                    if posteam and posteam != 'NA':
                        play_data['posteam'] = posteam
                
                if 'defteam' in row and pd.notna(row['defteam']):
                    defteam = str(row['defteam']).strip().upper()
                    if defteam and defteam != 'NA':
                        play_data['defteam'] = defteam
                
                # Game situation fields
                if 'qtr' in row and pd.notna(row['qtr']):
                    try:
                        qtr = int(row['qtr'])
                        if 1 <= qtr <= 5:
                            play_data['qtr'] = qtr
                    except (ValueError, TypeError):
                        pass
                
                if 'game_seconds_remaining' in row and pd.notna(row['game_seconds_remaining']):
                    try:
                        seconds = int(row['game_seconds_remaining'])
                        if 0 <= seconds <= 3600:
                            play_data['game_seconds_remaining'] = seconds
                    except (ValueError, TypeError):
                        pass
                
                if 'half_seconds_remaining' in row and pd.notna(row['half_seconds_remaining']):
                    try:
                        seconds = int(row['half_seconds_remaining'])
                        if 0 <= seconds <= 1800:
                            play_data['half_seconds_remaining'] = seconds
                    except (ValueError, TypeError):
                        pass
                
                if 'game_half' in row and pd.notna(row['game_half']):
                    game_half = str(row['game_half']).strip().lower()
                    if game_half in ['half1', 'half2', 'overtime']:
                        play_data['game_half'] = game_half
                
                # Field position
                if 'yardline_100' in row and pd.notna(row['yardline_100']):
                    try:
                        yardline = int(row['yardline_100'])
                        if 1 <= yardline <= 99:
                            play_data['yardline_100'] = yardline
                    except (ValueError, TypeError):
                        pass
                
                if 'ydstogo' in row and pd.notna(row['ydstogo']):
                    try:
                        ydstogo = int(row['ydstogo'])
                        if 1 <= ydstogo <= 99:
                            play_data['ydstogo'] = ydstogo
                    except (ValueError, TypeError):
                        pass
                
                if 'down' in row and pd.notna(row['down']):
                    try:
                        down = int(row['down'])
                        if 1 <= down <= 4:
                            play_data['down'] = down
                    except (ValueError, TypeError):
                        pass
                
                # Play details
                if 'play_type' in row and pd.notna(row['play_type']):
                    play_type = str(row['play_type']).strip().lower()
                    if play_type:
                        play_data['play_type'] = play_type
                
                if 'desc' in row and pd.notna(row['desc']):
                    play_data['desc'] = str(row['desc']).strip()
                
                if 'yards_gained' in row and pd.notna(row['yards_gained']):
                    try:
                        yards = int(row['yards_gained'])
                        if -99 <= yards <= 99:
                            play_data['yards_gained'] = yards
                    except (ValueError, TypeError):
                        pass
                
                # Advanced metrics
                if 'ep' in row and pd.notna(row['ep']):
                    try:
                        ep = float(row['ep'])
                        if -10.0 <= ep <= 10.0:
                            play_data['ep'] = ep
                    except (ValueError, TypeError):
                        pass
                
                if 'epa' in row and pd.notna(row['epa']):
                    try:
                        epa = float(row['epa'])
                        if -15.0 <= epa <= 15.0:
                            play_data['epa'] = epa
                    except (ValueError, TypeError):
                        pass
                
                if 'wp' in row and pd.notna(row['wp']):
                    try:
                        wp = float(row['wp'])
                        if 0.0 <= wp <= 1.0:
                            play_data['wp'] = wp
                    except (ValueError, TypeError):
                        pass
                
                if 'wpa' in row and pd.notna(row['wpa']):
                    try:
                        wpa = float(row['wpa'])
                        if -1.0 <= wpa <= 1.0:
                            play_data['wpa'] = wpa
                    except (ValueError, TypeError):
                        pass
                
                # Boolean flags
                for flag in ['touchdown', 'pass_touchdown', 'rush_touchdown', 
                           'interception', 'fumble', 'safety', 'penalty']:
                    if flag in row and pd.notna(row[flag]):
                        try:
                            play_data[flag] = bool(row[flag])
                        except (ValueError, TypeError):
                            pass
                
                play = PlayCreate(**play_data)
                current_batch.append(play)
                
                # Create batch when size reached
                if len(current_batch) >= batch_size:
                    batches.append(current_batch)
                    current_batch = []
                    
            except Exception as e:
                logger.warning(f"Failed to map play row {i}: {e}")
                continue
        
        # Add remaining plays as final batch
        if current_batch:
            batches.append(current_batch)
        
        total_plays = sum(len(batch) for batch in batches)
        logger.info(f"Mapped {total_plays} plays into {len(batches)} batches")
        return batches