"""Data cleaning utilities for NFL data."""

import logging
from typing import Dict, Any, Optional, List, Tuple
import pandas as pd
import numpy as np
from datetime import datetime, date
import re

from .validators import ValidationResult, ValidationSeverity

logger = logging.getLogger(__name__)


class DataCleaner:
    """Base class for data cleaning operations."""
    
    def __init__(self, strict_mode: bool = False):
        """Initialize cleaner.
        
        Args:
            strict_mode: If True, be more aggressive with data cleaning
        """
        self.strict_mode = strict_mode
        self.cleaning_log: List[str] = []
    
    def log_cleaning_action(self, action: str) -> None:
        """Log a cleaning action."""
        self.cleaning_log.append(action)
        logger.info(f"Cleaning action: {action}")
    
    def clear_log(self) -> None:
        """Clear the cleaning log."""
        self.cleaning_log.clear()
    
    def clean(self, data: pd.DataFrame) -> Tuple[pd.DataFrame, List[str]]:
        """Clean data and return cleaned DataFrame with log of actions."""
        raise NotImplementedError("Subclasses must implement clean method")


class NFLDataCleaner(DataCleaner):
    """General NFL data cleaner with common cleaning operations."""
    
    # Team name mappings for common inconsistencies
    TEAM_MAPPINGS = {
        'OAK': 'LV',  # Oakland to Las Vegas
        'SD': 'LAC',  # San Diego to Los Angeles Chargers
        'STL': 'LAR',  # St. Louis to Los Angeles Rams
        'LA': 'LAR',  # Generic LA to Rams
    }
    
    # Position mappings for inconsistent formats
    POSITION_MAPPINGS = {
        'HB': 'RB',  # Halfback to Running Back
        'OG': 'G',   # Offensive Guard
        'OT': 'T',   # Offensive Tackle
        'NT': 'DT',  # Nose Tackle to Defensive Tackle
        'ILB': 'LB', # Inside Linebacker
        'OLB': 'LB', # Outside Linebacker
        'MLB': 'LB', # Middle Linebacker
        'FS': 'S',   # Free Safety
        'SS': 'S',   # Strong Safety
    }
    
    def clean_team_abbreviations(self, data: pd.DataFrame, 
                                 team_columns: List[str]) -> pd.DataFrame:
        """Clean and standardize team abbreviations."""
        cleaned_data = data.copy()
        
        for column in team_columns:
            if column not in cleaned_data.columns:
                continue
            
            # Apply team mappings
            original_teams = cleaned_data[column].value_counts()
            cleaned_data[column] = cleaned_data[column].replace(self.TEAM_MAPPINGS)
            new_teams = cleaned_data[column].value_counts()
            
            # Log changes
            for old_team, new_team in self.TEAM_MAPPINGS.items():
                if old_team in original_teams and new_team in new_teams:
                    count = original_teams[old_team]
                    self.log_cleaning_action(
                        f"Mapped {count} instances of '{old_team}' to '{new_team}' in {column}"
                    )
            
            # Convert to uppercase
            cleaned_data[column] = cleaned_data[column].str.upper()
            
            # Remove extra whitespace
            cleaned_data[column] = cleaned_data[column].str.strip()
        
        return cleaned_data
    
    def clean_positions(self, data: pd.DataFrame, 
                        position_column: str = 'position') -> pd.DataFrame:
        """Clean and standardize player positions."""
        if position_column not in data.columns:
            return data
        
        cleaned_data = data.copy()
        original_positions = cleaned_data[position_column].value_counts()
        
        # Apply position mappings
        cleaned_data[position_column] = cleaned_data[position_column].replace(self.POSITION_MAPPINGS)
        
        # Convert to uppercase and strip whitespace
        cleaned_data[position_column] = cleaned_data[position_column].str.upper().str.strip()
        
        # Log changes
        new_positions = cleaned_data[position_column].value_counts()
        for old_pos, new_pos in self.POSITION_MAPPINGS.items():
            if old_pos in original_positions and new_pos in new_positions:
                count = original_positions[old_pos]
                self.log_cleaning_action(
                    f"Mapped {count} instances of '{old_pos}' to '{new_pos}'"
                )
        
        return cleaned_data
    
    def clean_names(self, data: pd.DataFrame, name_columns: List[str]) -> pd.DataFrame:
        """Clean and standardize names."""
        cleaned_data = data.copy()
        
        for column in name_columns:
            if column not in cleaned_data.columns:
                continue
            
            # Remove extra whitespace
            cleaned_data[column] = cleaned_data[column].str.strip()
            
            # Fix multiple spaces
            cleaned_data[column] = cleaned_data[column].str.replace(r'\s+', ' ', regex=True)
            
            # Remove special characters that shouldn't be in names
            invalid_chars = cleaned_data[column].str.contains(r'[^\w\s\.\'\-]', na=False).sum()
            if invalid_chars > 0:
                cleaned_data[column] = cleaned_data[column].str.replace(r'[^\w\s\.\'\-]', '', regex=True)
                self.log_cleaning_action(
                    f"Removed invalid characters from {invalid_chars} names in {column}"
                )
            
            # Title case for names
            cleaned_data[column] = cleaned_data[column].str.title()
        
        return cleaned_data
    
    def clean_dates(self, data: pd.DataFrame, date_columns: List[str]) -> pd.DataFrame:
        """Clean and standardize dates."""
        cleaned_data = data.copy()
        
        for column in date_columns:
            if column not in cleaned_data.columns:
                continue
            
            original_format_count = cleaned_data[column].notna().sum()
            
            # Try to parse dates
            cleaned_data[column] = pd.to_datetime(cleaned_data[column], errors='coerce')
            
            # Count parsing failures
            parsed_count = cleaned_data[column].notna().sum()
            failed_count = original_format_count - parsed_count
            
            if failed_count > 0:
                self.log_cleaning_action(
                    f"Failed to parse {failed_count} dates in {column}"
                )
        
        return cleaned_data
    
    def clean_numeric_fields(self, data: pd.DataFrame, 
                            numeric_columns: List[str],
                            clip_ranges: Optional[Dict[str, Tuple[float, float]]] = None) -> pd.DataFrame:
        """Clean numeric fields by handling outliers and invalid values."""
        cleaned_data = data.copy()
        clip_ranges = clip_ranges or {}
        
        for column in numeric_columns:
            if column not in cleaned_data.columns:
                continue
            
            # Convert to numeric, coercing errors to NaN
            original_count = cleaned_data[column].notna().sum()
            cleaned_data[column] = pd.to_numeric(cleaned_data[column], errors='coerce')
            new_count = cleaned_data[column].notna().sum()
            
            if original_count != new_count:
                self.log_cleaning_action(
                    f"Converted {original_count - new_count} non-numeric values to NaN in {column}"
                )
            
            # Apply clipping if ranges specified
            if column in clip_ranges:
                min_val, max_val = clip_ranges[column]
                outliers = ((cleaned_data[column] < min_val) | 
                           (cleaned_data[column] > max_val)).sum()
                
                if outliers > 0:
                    cleaned_data[column] = cleaned_data[column].clip(min_val, max_val)
                    self.log_cleaning_action(
                        f"Clipped {outliers} outlier values in {column} to range [{min_val}, {max_val}]"
                    )
        
        return cleaned_data
    
    def remove_duplicates(self, data: pd.DataFrame, 
                         subset: Optional[List[str]] = None,
                         keep: str = 'first') -> pd.DataFrame:
        """Remove duplicate records."""
        original_count = len(data)
        cleaned_data = data.drop_duplicates(subset=subset, keep=keep)
        duplicates_removed = original_count - len(cleaned_data)
        
        if duplicates_removed > 0:
            columns_str = f"columns {subset}" if subset else "all columns"
            self.log_cleaning_action(
                f"Removed {duplicates_removed} duplicate records based on {columns_str}"
            )
        
        return cleaned_data
    
    def handle_missing_values(self, data: pd.DataFrame,
                             fill_strategies: Dict[str, Any]) -> pd.DataFrame:
        """Handle missing values with specified strategies."""
        cleaned_data = data.copy()
        
        for column, strategy in fill_strategies.items():
            if column not in cleaned_data.columns:
                continue
            
            missing_count = cleaned_data[column].isna().sum()
            if missing_count == 0:
                continue
            
            if strategy == 'drop':
                cleaned_data = cleaned_data.dropna(subset=[column])
                self.log_cleaning_action(
                    f"Dropped {missing_count} rows with missing {column}"
                )
            elif strategy == 'forward_fill':
                cleaned_data[column] = cleaned_data[column].ffill()
                self.log_cleaning_action(
                    f"Forward-filled {missing_count} missing values in {column}"
                )
            elif strategy == 'median':
                if pd.api.types.is_numeric_dtype(cleaned_data[column]):
                    fill_value = cleaned_data[column].median()
                    cleaned_data[column] = cleaned_data[column].fillna(fill_value)
                    self.log_cleaning_action(
                        f"Filled {missing_count} missing values in {column} with median {fill_value}"
                    )
                else:
                    self.log_cleaning_action(
                        f"Skipped median fill for non-numeric column {column}"
                    )
            elif strategy == 'mode':
                fill_value = cleaned_data[column].mode().iloc[0] if not cleaned_data[column].mode().empty else 'Unknown'
                cleaned_data[column] = cleaned_data[column].fillna(fill_value)
                self.log_cleaning_action(
                    f"Filled {missing_count} missing values in {column} with mode {fill_value}"
                )
            elif isinstance(strategy, (int, float, str)):
                # This should be last to avoid catching string strategies like 'median', 'mode'
                cleaned_data[column] = cleaned_data[column].fillna(strategy)
                self.log_cleaning_action(
                    f"Filled {missing_count} missing values in {column} with {strategy}"
                )
        
        return cleaned_data


class TeamDataCleaner(NFLDataCleaner):
    """Specialized cleaner for team data."""
    
    def clean(self, data: pd.DataFrame) -> Tuple[pd.DataFrame, List[str]]:
        """Clean team data."""
        self.clear_log()
        cleaned_data = data.copy()
        
        # Clean team abbreviations
        cleaned_data = self.clean_team_abbreviations(cleaned_data, ['team_abbr'])
        
        # Clean team names
        cleaned_data = self.clean_names(cleaned_data, ['team_name', 'team_nick'])
        
        # Remove duplicates based on team abbreviation
        cleaned_data = self.remove_duplicates(cleaned_data, subset=['team_abbr'])
        
        # Handle missing team names
        fill_strategies = {
            'team_name': 'Unknown Team',
            'team_nick': 'Unknown'
        }
        cleaned_data = self.handle_missing_values(cleaned_data, fill_strategies)
        
        return cleaned_data, self.cleaning_log.copy()


class PlayerDataCleaner(NFLDataCleaner):
    """Specialized cleaner for player data."""
    
    def clean_height_strings(self, data: pd.DataFrame, 
                            height_column: str = 'height') -> pd.DataFrame:
        """Clean height strings and convert to inches."""
        if height_column not in data.columns:
            return data
        
        cleaned_data = data.copy()
        
        def parse_height(height_str):
            """Parse height string to inches."""
            if pd.isna(height_str):
                return None
            
            height_str = str(height_str).strip()
            
            # Format: "6-2" or "6'2\"" or "6 2" 
            patterns = [
                r"^(\d+)['\-\s](\d+)\"?$",  # 6-2, 6'2", 6 2
                r"^(\d+)$"                  # Just feet: 6
            ]
            
            for pattern in patterns:
                match = re.match(pattern, height_str)
                if match:
                    feet = int(match.group(1))
                    inches = int(match.group(2)) if len(match.groups()) > 1 else 0
                    return feet * 12 + inches
            
            return None
        
        # Create new height_inches column if height is string
        if cleaned_data[height_column].dtype == 'object':
            original_count = cleaned_data[height_column].notna().sum()
            cleaned_data['height_inches'] = cleaned_data[height_column].apply(parse_height)
            parsed_count = cleaned_data['height_inches'].notna().sum()
            
            self.log_cleaning_action(
                f"Parsed {parsed_count} out of {original_count} height strings to inches"
            )
            
            # Drop original height column and rename
            cleaned_data = cleaned_data.drop(columns=[height_column])
            cleaned_data = cleaned_data.rename(columns={'height_inches': height_column})
        
        return cleaned_data
    
    def clean(self, data: pd.DataFrame) -> Tuple[pd.DataFrame, List[str]]:
        """Clean player data."""
        self.clear_log()
        cleaned_data = data.copy()
        
        # Clean names
        cleaned_data = self.clean_names(cleaned_data, ['full_name', 'first_name', 'last_name'])
        
        # Clean team abbreviations
        cleaned_data = self.clean_team_abbreviations(cleaned_data, ['team_abbr'])
        
        # Clean positions
        cleaned_data = self.clean_positions(cleaned_data)
        
        # Clean height strings
        cleaned_data = self.clean_height_strings(cleaned_data)
        
        # Clean numeric fields with clipping
        numeric_fields = ['height', 'weight', 'age', 'jersey_number', 'rookie_year']
        clip_ranges = {
            'height': (60, 84),  # 5'0" to 7'0"
            'weight': (150, 400),
            'age': (18, 50),
            'jersey_number': (0, 99),
            'rookie_year': (1920, datetime.now().year)
        }
        cleaned_data = self.clean_numeric_fields(cleaned_data, numeric_fields, clip_ranges)
        
        # Remove duplicates based on player_id
        cleaned_data = self.remove_duplicates(cleaned_data, subset=['player_id'])
        
        # Handle missing values
        fill_strategies = {
            'team_abbr': 'UNK',
            'position': 'UNK',
            'status': 'active'
        }
        cleaned_data = self.handle_missing_values(cleaned_data, fill_strategies)
        
        return cleaned_data, self.cleaning_log.copy()


class GameDataCleaner(NFLDataCleaner):
    """Specialized cleaner for game data."""
    
    def clean_game_ids(self, data: pd.DataFrame, 
                       game_id_column: str = 'game_id') -> pd.DataFrame:
        """Clean and validate game IDs."""
        if game_id_column not in data.columns:
            return data
        
        cleaned_data = data.copy()
        
        # Remove extra whitespace
        cleaned_data[game_id_column] = cleaned_data[game_id_column].str.strip()
        
        # Convert to uppercase for team parts
        def standardize_game_id(game_id):
            if pd.isna(game_id):
                return game_id
            
            parts = str(game_id).split('_')
            if len(parts) >= 4:
                # Standard format: YYYY_WW_AWAY_HOME
                parts[2] = parts[2].upper()  # Away team
                parts[3] = parts[3].upper()  # Home team
                return '_'.join(parts)
            return game_id
        
        original_ids = cleaned_data[game_id_column].copy()
        cleaned_data[game_id_column] = cleaned_data[game_id_column].apply(standardize_game_id)
        
        # Count changes
        changes = (original_ids != cleaned_data[game_id_column]).sum()
        if changes > 0:
            self.log_cleaning_action(f"Standardized {changes} game IDs")
        
        return cleaned_data
    
    def clean(self, data: pd.DataFrame) -> Tuple[pd.DataFrame, List[str]]:
        """Clean game data."""
        self.clear_log()
        cleaned_data = data.copy()
        
        # Clean game IDs
        cleaned_data = self.clean_game_ids(cleaned_data)
        
        # Clean team abbreviations
        cleaned_data = self.clean_team_abbreviations(cleaned_data, ['home_team', 'away_team'])
        
        # Clean dates
        date_columns = ['game_date', 'gameday']
        cleaned_data = self.clean_dates(cleaned_data, date_columns)
        
        # Clean numeric fields
        numeric_fields = ['season', 'week', 'home_score', 'away_score']
        clip_ranges = {
            'season': (1920, datetime.now().year + 1),
            'week': (1, 22),
            'home_score': (0, 100),
            'away_score': (0, 100)
        }
        cleaned_data = self.clean_numeric_fields(cleaned_data, numeric_fields, clip_ranges)
        
        # Remove duplicates based on game_id
        cleaned_data = self.remove_duplicates(cleaned_data, subset=['game_id'])
        
        # Handle missing values
        fill_strategies = {
            'season_type': 'REG',
            'roof': 'unknown',
            'surface': 'unknown'
        }
        cleaned_data = self.handle_missing_values(cleaned_data, fill_strategies)
        
        return cleaned_data, self.cleaning_log.copy()


class PlayDataCleaner(NFLDataCleaner):
    """Specialized cleaner for play-by-play data."""
    
    def clean_play_types(self, data: pd.DataFrame, 
                         play_type_column: str = 'play_type') -> pd.DataFrame:
        """Clean and standardize play types."""
        if play_type_column not in data.columns:
            return data
        
        cleaned_data = data.copy()
        
        # Standardize play type names
        play_type_mappings = {
            'rushing': 'run',
            'running': 'run',
            'passing': 'pass',
            'field goal': 'field_goal',
            'fg': 'field_goal',
            'extra point': 'extra_point',
            'pat': 'extra_point',
            'qb kneel': 'qb_kneel',
            'qb spike': 'qb_spike',
            'end of period': 'end_period',
            'timeout': 'timeout'
        }
        
        # Clean whitespace and convert to lowercase
        cleaned_data[play_type_column] = (cleaned_data[play_type_column]
                                        .str.strip()
                                        .str.lower()
                                        .str.replace(' ', '_'))
        
        # Apply mappings
        original_types = cleaned_data[play_type_column].value_counts()
        cleaned_data[play_type_column] = cleaned_data[play_type_column].replace(play_type_mappings)
        
        # Log changes
        new_types = cleaned_data[play_type_column].value_counts()
        for old_type, new_type in play_type_mappings.items():
            if old_type in original_types and new_type in new_types:
                count = original_types[old_type]
                self.log_cleaning_action(
                    f"Mapped {count} instances of '{old_type}' to '{new_type}'"
                )
        
        return cleaned_data
    
    def clean(self, data: pd.DataFrame) -> Tuple[pd.DataFrame, List[str]]:
        """Clean play-by-play data."""
        self.clear_log()
        cleaned_data = data.copy()
        
        # Clean team abbreviations
        cleaned_data = self.clean_team_abbreviations(cleaned_data, ['posteam', 'defteam'])
        
        # Clean play types
        cleaned_data = self.clean_play_types(cleaned_data)
        
        # Clean numeric fields
        numeric_fields = ['season', 'week', 'qtr', 'down', 'ydstogo', 'yardline_100', 
                         'yards_gained', 'ep', 'epa', 'wp', 'wpa']
        clip_ranges = {
            'season': (1999, datetime.now().year + 1),
            'week': (1, 22),
            'qtr': (1, 5),
            'down': (1, 4),
            'ydstogo': (0, 99),
            'yardline_100': (0, 100),
            'yards_gained': (-50, 100),
            'ep': (-10, 10),
            'epa': (-15, 15),
            'wp': (0, 1),
            'wpa': (-1, 1)
        }
        cleaned_data = self.clean_numeric_fields(cleaned_data, numeric_fields, clip_ranges)
        
        # Remove duplicates based on play_id
        cleaned_data = self.remove_duplicates(cleaned_data, subset=['play_id'])
        
        # Handle missing values
        fill_strategies = {
            'play_type': 'unknown',
            'posteam': 'UNK',
            'defteam': 'UNK'
        }
        cleaned_data = self.handle_missing_values(cleaned_data, fill_strategies)
        
        return cleaned_data, self.cleaning_log.copy()