"""Data validation and cleaning utilities for NFL data."""

import logging
from typing import List, Dict, Any, Optional, Tuple, Set
from datetime import date, datetime
import pandas as pd
from dataclasses import dataclass
from enum import Enum
import re

logger = logging.getLogger(__name__)


class ValidationSeverity(Enum):
    """Severity levels for validation issues."""
    INFO = "info"
    WARNING = "warning" 
    ERROR = "error"
    CRITICAL = "critical"


@dataclass
class ValidationIssue:
    """Represents a data validation issue."""
    field: str
    severity: ValidationSeverity
    message: str
    record_id: Optional[str] = None
    expected_value: Optional[Any] = None
    actual_value: Optional[Any] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            'field': self.field,
            'severity': self.severity.value,
            'message': self.message,
            'record_id': self.record_id,
            'expected_value': self.expected_value,
            'actual_value': self.actual_value
        }


@dataclass 
class ValidationResult:
    """Results of data validation."""
    total_records: int
    valid_records: int
    issues: List[ValidationIssue]
    cleaned_data: Optional[pd.DataFrame] = None
    
    @property
    def invalid_records(self) -> int:
        """Number of records with issues."""
        return self.total_records - self.valid_records
    
    @property
    def validation_rate(self) -> float:
        """Percentage of valid records."""
        if self.total_records == 0:
            return 0.0
        return (self.valid_records / self.total_records) * 100
    
    @property
    def error_count(self) -> int:
        """Count of error-level issues."""
        return len([i for i in self.issues if i.severity == ValidationSeverity.ERROR])
    
    @property
    def warning_count(self) -> int:
        """Count of warning-level issues."""
        return len([i for i in self.issues if i.severity == ValidationSeverity.WARNING])
    
    @property
    def critical_count(self) -> int:
        """Count of critical-level issues."""
        return len([i for i in self.issues if i.severity == ValidationSeverity.CRITICAL])
    
    def get_issues_by_severity(self, severity: ValidationSeverity) -> List[ValidationIssue]:
        """Get issues filtered by severity level."""
        return [issue for issue in self.issues if issue.severity == severity]
    
    def get_issues_by_field(self, field: str) -> List[ValidationIssue]:
        """Get issues for a specific field."""
        return [issue for issue in self.issues if issue.field == field]
    
    def to_summary(self) -> Dict[str, Any]:
        """Generate validation summary."""
        return {
            'total_records': self.total_records,
            'valid_records': self.valid_records,
            'invalid_records': self.invalid_records,
            'validation_rate': round(self.validation_rate, 2),
            'total_issues': len(self.issues),
            'critical_issues': self.critical_count,
            'error_issues': self.error_count,
            'warning_issues': self.warning_count,
            'info_issues': len([i for i in self.issues if i.severity == ValidationSeverity.INFO])
        }


class BaseValidator:
    """Base class for data validators."""
    
    def __init__(self, strict_mode: bool = False):
        """Initialize validator.
        
        Args:
            strict_mode: If True, treat warnings as errors
        """
        self.strict_mode = strict_mode
        self.issues: List[ValidationIssue] = []
    
    def add_issue(self, field: str, severity: ValidationSeverity, message: str,
                  record_id: Optional[str] = None, expected_value: Optional[Any] = None,
                  actual_value: Optional[Any] = None) -> None:
        """Add a validation issue."""
        if self.strict_mode and severity == ValidationSeverity.WARNING:
            severity = ValidationSeverity.ERROR
            
        issue = ValidationIssue(
            field=field,
            severity=severity,
            message=message,
            record_id=record_id,
            expected_value=expected_value,
            actual_value=actual_value
        )
        self.issues.append(issue)
    
    def clear_issues(self) -> None:
        """Clear all validation issues."""
        self.issues.clear()
    
    def validate(self, data: pd.DataFrame) -> ValidationResult:
        """Validate data and return results."""
        raise NotImplementedError("Subclasses must implement validate method")


class NFLDataValidator(BaseValidator):
    """Comprehensive validator for NFL data."""
    
    # Valid NFL team abbreviations
    VALID_TEAMS = {
        'ARI', 'ATL', 'BAL', 'BUF', 'CAR', 'CHI', 'CIN', 'CLE', 
        'DAL', 'DEN', 'DET', 'GB', 'HOU', 'IND', 'JAX', 'KC',
        'LV', 'LAC', 'LAR', 'MIA', 'MIN', 'NE', 'NO', 'NYG',
        'NYJ', 'PHI', 'PIT', 'SF', 'SEA', 'TB', 'TEN', 'WAS'
    }
    
    # Historical teams that may appear in older data
    HISTORICAL_TEAMS = {'OAK', 'SD', 'STL'}
    
    # Valid positions
    VALID_POSITIONS = {
        'QB', 'RB', 'FB', 'WR', 'TE', 'OL', 'C', 'G', 'T', 'OT', 'OG',
        'DL', 'DE', 'DT', 'NT', 'LB', 'ILB', 'OLB', 'MLB', 'DB', 'CB', 
        'S', 'SS', 'FS', 'K', 'P', 'LS', 'LS/TE', 'WR/PR', 'RB/KR'
    }
    
    # Valid season types
    VALID_SEASON_TYPES = {'REG', 'POST', 'PRE'}
    
    def __init__(self, strict_mode: bool = False, 
                 min_season: int = 1999, max_season: Optional[int] = None):
        """Initialize NFL data validator.
        
        Args:
            strict_mode: If True, treat warnings as errors
            min_season: Minimum valid season year
            max_season: Maximum valid season year (defaults to current year)
        """
        super().__init__(strict_mode)
        self.min_season = min_season
        self.max_season = max_season or datetime.now().year
    
    def validate_team_abbreviations(self, data: pd.DataFrame, 
                                   team_columns: List[str]) -> None:
        """Validate team abbreviations in specified columns."""
        valid_teams = self.VALID_TEAMS | self.HISTORICAL_TEAMS
        
        for column in team_columns:
            if column not in data.columns:
                continue
                
            invalid_teams = data[~data[column].isin(valid_teams) & 
                               data[column].notna()][column].unique()
            
            for team in invalid_teams:
                self.add_issue(
                    field=column,
                    severity=ValidationSeverity.ERROR,
                    message=f"Invalid team abbreviation: {team}",
                    expected_value=f"One of {sorted(valid_teams)}",
                    actual_value=team
                )
    
    def validate_seasons(self, data: pd.DataFrame, season_column: str = 'season') -> None:
        """Validate season years."""
        if season_column not in data.columns:
            return
            
        invalid_seasons = data[
            (data[season_column] < self.min_season) | 
            (data[season_column] > self.max_season) |
            data[season_column].isna()
        ][season_column].unique()
        
        for season in invalid_seasons:
            if pd.isna(season):
                self.add_issue(
                    field=season_column,
                    severity=ValidationSeverity.ERROR,
                    message="Missing season value",
                    expected_value=f"Year between {self.min_season} and {self.max_season}",
                    actual_value=None
                )
            else:
                self.add_issue(
                    field=season_column,
                    severity=ValidationSeverity.ERROR,
                    message=f"Invalid season year: {season}",
                    expected_value=f"Year between {self.min_season} and {self.max_season}",
                    actual_value=season
                )
    
    def validate_positions(self, data: pd.DataFrame, position_column: str = 'position') -> None:
        """Validate player positions."""
        if position_column not in data.columns:
            return
            
        invalid_positions = data[
            ~data[position_column].isin(self.VALID_POSITIONS) & 
            data[position_column].notna()
        ][position_column].unique()
        
        for position in invalid_positions:
            self.add_issue(
                field=position_column,
                severity=ValidationSeverity.WARNING,
                message=f"Unusual position: {position}",
                expected_value=f"One of {sorted(self.VALID_POSITIONS)}",
                actual_value=position
            )
    
    def validate_season_types(self, data: pd.DataFrame, 
                             season_type_column: str = 'season_type') -> None:
        """Validate season types."""
        if season_type_column not in data.columns:
            return
            
        invalid_types = data[
            ~data[season_type_column].isin(self.VALID_SEASON_TYPES) & 
            data[season_type_column].notna()
        ][season_type_column].unique()
        
        for season_type in invalid_types:
            self.add_issue(
                field=season_type_column,
                severity=ValidationSeverity.ERROR,
                message=f"Invalid season type: {season_type}",
                expected_value=f"One of {sorted(self.VALID_SEASON_TYPES)}",
                actual_value=season_type
            )
    
    def validate_dates(self, data: pd.DataFrame, date_columns: List[str]) -> None:
        """Validate date formats and ranges."""
        for column in date_columns:
            if column not in data.columns:
                continue
                
            # Check for invalid date formats
            for idx, value in data[column].items():
                if pd.isna(value):
                    self.add_issue(
                        field=column,
                        severity=ValidationSeverity.WARNING,
                        message=f"Missing date value at index {idx}",
                        record_id=str(idx)
                    )
                    continue
                
                try:
                    if isinstance(value, str):
                        parsed_date = pd.to_datetime(value).date()
                    elif isinstance(value, datetime):
                        parsed_date = value.date()
                    elif isinstance(value, date):
                        parsed_date = value
                    else:
                        raise ValueError(f"Unexpected date type: {type(value)}")
                    
                    # Check reasonable date ranges for NFL data
                    if parsed_date.year < 1920 or parsed_date.year > datetime.now().year + 1:
                        self.add_issue(
                            field=column,
                            severity=ValidationSeverity.WARNING,
                            message=f"Date outside expected range: {parsed_date}",
                            record_id=str(idx),
                            actual_value=parsed_date
                        )
                        
                except Exception as e:
                    self.add_issue(
                        field=column,
                        severity=ValidationSeverity.ERROR,
                        message=f"Invalid date format: {value} - {str(e)}",
                        record_id=str(idx),
                        actual_value=value
                    )
    
    def validate_numeric_ranges(self, data: pd.DataFrame, 
                               numeric_rules: Dict[str, Tuple[float, float]]) -> None:
        """Validate numeric fields are within expected ranges.
        
        Args:
            data: DataFrame to validate
            numeric_rules: Dict mapping column names to (min, max) tuples
        """
        for column, (min_val, max_val) in numeric_rules.items():
            if column not in data.columns:
                continue
            
            # Only validate numeric columns
            if not pd.api.types.is_numeric_dtype(data[column]):
                # Log non-numeric values for numeric fields
                non_numeric_count = data[column].notna().sum()
                if non_numeric_count > 0:
                    self.add_issue(
                        field=column,
                        severity=ValidationSeverity.WARNING,
                        message=f"Non-numeric values in numeric field: {non_numeric_count} values",
                        expected_value="Numeric values",
                        actual_value=f"{non_numeric_count} non-numeric values"
                    )
                continue
                
            # Check for values outside range
            try:
                invalid_mask = (
                    (data[column] < min_val) | 
                    (data[column] > max_val)
                ) & data[column].notna()
                
                invalid_values = data[invalid_mask][column]
                for idx, value in invalid_values.items():
                    self.add_issue(
                        field=column,
                        severity=ValidationSeverity.WARNING,
                        message=f"Value outside expected range: {value}",
                        record_id=str(idx),
                        expected_value=f"Between {min_val} and {max_val}",
                        actual_value=value
                    )
            except Exception as e:
                # Handle any comparison errors
                self.add_issue(
                    field=column,
                    severity=ValidationSeverity.WARNING,
                    message=f"Unable to validate numeric range due to data type issues: {str(e)}",
                    actual_value=str(data[column].dtype)
                )


class TeamDataValidator(NFLDataValidator):
    """Validator specifically for team data."""
    
    def validate(self, data: pd.DataFrame) -> ValidationResult:
        """Validate team data."""
        self.clear_issues()
        original_count = len(data)
        
        # Required fields validation
        required_fields = ['team_abbr', 'team_name']
        for field in required_fields:
            if field not in data.columns:
                self.add_issue(
                    field=field,
                    severity=ValidationSeverity.CRITICAL,
                    message=f"Required field missing: {field}"
                )
            else:
                null_count = data[field].isna().sum()
                if null_count > 0:
                    self.add_issue(
                        field=field,
                        severity=ValidationSeverity.ERROR,
                        message=f"{null_count} records missing required field"
                    )
        
        # Team abbreviation validation
        self.validate_team_abbreviations(data, ['team_abbr'])
        
        # Team abbreviation format validation
        if 'team_abbr' in data.columns:
            invalid_format = data[
                ~data['team_abbr'].str.match(r'^[A-Z]{2,3}$', na=False)
            ]['team_abbr'].dropna().unique()
            
            for abbr in invalid_format:
                self.add_issue(
                    field='team_abbr',
                    severity=ValidationSeverity.ERROR,
                    message=f"Invalid abbreviation format: {abbr}",
                    expected_value="2-3 uppercase letters",
                    actual_value=abbr
                )
        
        # Duplicate team abbreviations
        if 'team_abbr' in data.columns:
            duplicates = data[data.duplicated('team_abbr', keep=False)]['team_abbr'].unique()
            for dup in duplicates:
                self.add_issue(
                    field='team_abbr',
                    severity=ValidationSeverity.ERROR,
                    message=f"Duplicate team abbreviation: {dup}",
                    actual_value=dup
                )
        
        # Calculate valid records (excluding critical and error issues)
        error_records = set()
        for issue in self.issues:
            if issue.severity in [ValidationSeverity.CRITICAL, ValidationSeverity.ERROR]:
                if issue.record_id:
                    error_records.add(issue.record_id)
        
        valid_count = original_count - len(error_records)
        
        return ValidationResult(
            total_records=original_count,
            valid_records=max(0, valid_count),
            issues=self.issues.copy()
        )


class PlayerDataValidator(NFLDataValidator):
    """Validator specifically for player data."""
    
    def validate(self, data: pd.DataFrame) -> ValidationResult:
        """Validate player data."""
        self.clear_issues()
        original_count = len(data)
        
        # Required fields validation
        required_fields = ['player_id', 'full_name']
        for field in required_fields:
            if field not in data.columns:
                self.add_issue(
                    field=field,
                    severity=ValidationSeverity.CRITICAL,
                    message=f"Required field missing: {field}"
                )
            else:
                null_count = data[field].isna().sum()
                if null_count > 0:
                    self.add_issue(
                        field=field,
                        severity=ValidationSeverity.ERROR,
                        message=f"{null_count} records missing required field"
                    )
        
        # Player ID format validation
        if 'player_id' in data.columns:
            invalid_ids = data[
                ~data['player_id'].str.match(r'^[0-9]{2}-[0-9]{7}$', na=False)
            ]['player_id'].dropna()
            
            for idx, player_id in invalid_ids.items():
                self.add_issue(
                    field='player_id',
                    severity=ValidationSeverity.WARNING,
                    message=f"Unusual player ID format: {player_id}",
                    record_id=str(idx),
                    expected_value="Format: XX-XXXXXXX",
                    actual_value=player_id
                )
        
        # Team abbreviation validation
        self.validate_team_abbreviations(data, ['team_abbr'])
        
        # Position validation
        self.validate_positions(data)
        
        # Physical attributes validation
        physical_rules = {
            'height': (60, 84),  # 5'0" to 7'0" in inches
            'weight': (150, 400),  # pounds
            'age': (18, 50),  # years
            'jersey_number': (0, 99)
        }
        self.validate_numeric_ranges(data, physical_rules)
        
        # Rookie year validation
        if 'rookie_year' in data.columns:
            current_year = datetime.now().year
            invalid_rookie_years = data[
                (data['rookie_year'] < 1920) | 
                (data['rookie_year'] > current_year)
            ]['rookie_year'].dropna()
            
            for idx, year in invalid_rookie_years.items():
                self.add_issue(
                    field='rookie_year',
                    severity=ValidationSeverity.WARNING,
                    message=f"Invalid rookie year: {year}",
                    record_id=str(idx),
                    expected_value=f"Year between 1920 and {current_year}",
                    actual_value=year
                )
        
        # Calculate valid records
        error_records = set()
        for issue in self.issues:
            if issue.severity in [ValidationSeverity.CRITICAL, ValidationSeverity.ERROR]:
                if issue.record_id:
                    error_records.add(issue.record_id)
        
        valid_count = original_count - len(error_records)
        
        return ValidationResult(
            total_records=original_count,
            valid_records=max(0, valid_count),
            issues=self.issues.copy()
        )


class GameDataValidator(NFLDataValidator):
    """Validator specifically for game data."""
    
    def validate(self, data: pd.DataFrame) -> ValidationResult:
        """Validate game data."""
        self.clear_issues()
        original_count = len(data)
        
        # Required fields validation
        required_fields = ['game_id', 'season', 'home_team', 'away_team']
        for field in required_fields:
            if field not in data.columns:
                self.add_issue(
                    field=field,
                    severity=ValidationSeverity.CRITICAL,
                    message=f"Required field missing: {field}"
                )
            else:
                null_count = data[field].isna().sum()
                if null_count > 0:
                    self.add_issue(
                        field=field,
                        severity=ValidationSeverity.ERROR,
                        message=f"{null_count} records missing required field"
                    )
        
        # Game ID format validation
        if 'game_id' in data.columns:
            invalid_ids = data[
                ~data['game_id'].str.match(r'^\d{4}_\d{2}_[A-Z]{2,3}_[A-Z]{2,3}$', na=False)
            ]['game_id'].dropna()
            
            for idx, game_id in invalid_ids.items():
                self.add_issue(
                    field='game_id',
                    severity=ValidationSeverity.WARNING,
                    message=f"Unusual game ID format: {game_id}",
                    record_id=str(idx),
                    expected_value="Format: YYYY_WW_AWAY_HOME",
                    actual_value=game_id
                )
        
        # Season validation
        self.validate_seasons(data)
        
        # Season type validation
        self.validate_season_types(data)
        
        # Team validation
        self.validate_team_abbreviations(data, ['home_team', 'away_team'])
        
        # Same team validation
        if 'home_team' in data.columns and 'away_team' in data.columns:
            same_team_games = data[data['home_team'] == data['away_team']]
            for idx, row in same_team_games.iterrows():
                self.add_issue(
                    field='home_team',
                    severity=ValidationSeverity.ERROR,
                    message=f"Team cannot play against itself: {row['home_team']}",
                    record_id=str(idx),
                    actual_value=row['home_team']
                )
        
        # Date validation
        date_columns = ['game_date', 'gameday']
        for col in date_columns:
            if col in data.columns:
                self.validate_dates(data, [col])
        
        # Score validation
        score_rules = {
            'home_score': (0, 100),
            'away_score': (0, 100)
        }
        self.validate_numeric_ranges(data, score_rules)
        
        # Week validation
        if 'week' in data.columns:
            invalid_weeks = data[
                (data['week'] < 1) | (data['week'] > 22)  # Including playoffs
            ]['week'].dropna()
            
            for idx, week in invalid_weeks.items():
                self.add_issue(
                    field='week',
                    severity=ValidationSeverity.WARNING,
                    message=f"Week outside normal range: {week}",
                    record_id=str(idx),
                    expected_value="Week 1-22",
                    actual_value=week
                )
        
        # Calculate valid records
        error_records = set()
        for issue in self.issues:
            if issue.severity in [ValidationSeverity.CRITICAL, ValidationSeverity.ERROR]:
                if issue.record_id:
                    error_records.add(issue.record_id)
        
        valid_count = original_count - len(error_records)
        
        return ValidationResult(
            total_records=original_count,
            valid_records=max(0, valid_count),
            issues=self.issues.copy()
        )


class PlayDataValidator(NFLDataValidator):
    """Validator specifically for play-by-play data."""
    
    VALID_PLAY_TYPES = {
        'pass', 'run', 'punt', 'field_goal', 'extra_point', 
        'kickoff', 'qb_kneel', 'qb_spike', 'timeout', 'two_minute_warning',
        'end_period', 'safety', 'no_play'
    }
    
    def validate(self, data: pd.DataFrame) -> ValidationResult:
        """Validate play-by-play data."""
        self.clear_issues()
        original_count = len(data)
        
        # Required fields validation
        required_fields = ['play_id', 'game_id', 'season']
        for field in required_fields:
            if field not in data.columns:
                self.add_issue(
                    field=field,
                    severity=ValidationSeverity.CRITICAL,
                    message=f"Required field missing: {field}"
                )
            else:
                null_count = data[field].isna().sum()
                if null_count > 0:
                    self.add_issue(
                        field=field,
                        severity=ValidationSeverity.ERROR,
                        message=f"{null_count} records missing required field"
                    )
        
        # Season validation
        self.validate_seasons(data)
        
        # Team validation
        team_columns = ['posteam', 'defteam']
        self.validate_team_abbreviations(data, team_columns)
        
        # Play type validation
        if 'play_type' in data.columns:
            invalid_play_types = data[
                ~data['play_type'].isin(self.VALID_PLAY_TYPES) & 
                data['play_type'].notna()
            ]['play_type'].unique()
            
            for play_type in invalid_play_types:
                self.add_issue(
                    field='play_type',
                    severity=ValidationSeverity.WARNING,
                    message=f"Unusual play type: {play_type}",
                    expected_value=f"One of {sorted(self.VALID_PLAY_TYPES)}",
                    actual_value=play_type
                )
        
        # Down validation
        if 'down' in data.columns:
            invalid_downs = data[
                (data['down'] < 1) | (data['down'] > 4)
            ]['down'].dropna()
            
            for idx, down in invalid_downs.items():
                self.add_issue(
                    field='down',
                    severity=ValidationSeverity.WARNING,
                    message=f"Invalid down: {down}",
                    record_id=str(idx),
                    expected_value="1, 2, 3, or 4",
                    actual_value=down
                )
        
        # Quarter validation
        if 'qtr' in data.columns:
            invalid_qtrs = data[
                (data['qtr'] < 1) | (data['qtr'] > 5)  # Including overtime
            ]['qtr'].dropna()
            
            for idx, qtr in invalid_qtrs.items():
                self.add_issue(
                    field='qtr',
                    severity=ValidationSeverity.WARNING,
                    message=f"Quarter outside normal range: {qtr}",
                    record_id=str(idx),
                    expected_value="1-5 (including overtime)",
                    actual_value=qtr
                )
        
        # Field position validation
        field_rules = {
            'yardline_100': (0, 100),
            'ydstogo': (0, 99),
            'yards_gained': (-50, 100)
        }
        self.validate_numeric_ranges(data, field_rules)
        
        # Advanced metrics validation
        advanced_rules = {
            'ep': (-10, 10),  # Expected Points
            'epa': (-15, 15),  # Expected Points Added
            'wp': (0, 1),  # Win Probability
            'wpa': (-1, 1)  # Win Probability Added
        }
        self.validate_numeric_ranges(data, advanced_rules)
        
        # Calculate valid records
        error_records = set()
        for issue in self.issues:
            if issue.severity in [ValidationSeverity.CRITICAL, ValidationSeverity.ERROR]:
                if issue.record_id:
                    error_records.add(issue.record_id)
        
        valid_count = original_count - len(error_records)
        
        return ValidationResult(
            total_records=original_count,
            valid_records=max(0, valid_count),
            issues=self.issues.copy()
        )