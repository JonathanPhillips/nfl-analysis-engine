"""Tests for data validators."""

import pytest
import pandas as pd
from datetime import date, datetime

from src.data.validators import (
    ValidationSeverity, ValidationIssue, ValidationResult,
    NFLDataValidator, TeamDataValidator, PlayerDataValidator,
    GameDataValidator, PlayDataValidator
)


class TestValidationIssue:
    """Test ValidationIssue class."""
    
    def test_validation_issue_creation(self):
        """Test ValidationIssue creation."""
        issue = ValidationIssue(
            field='test_field',
            severity=ValidationSeverity.ERROR,
            message='Test error message',
            record_id='123',
            expected_value='expected',
            actual_value='actual'
        )
        
        assert issue.field == 'test_field'
        assert issue.severity == ValidationSeverity.ERROR
        assert issue.message == 'Test error message'
        assert issue.record_id == '123'
        assert issue.expected_value == 'expected'
        assert issue.actual_value == 'actual'
    
    def test_validation_issue_to_dict(self):
        """Test ValidationIssue to_dict conversion."""
        issue = ValidationIssue(
            field='test_field',
            severity=ValidationSeverity.WARNING,
            message='Test warning'
        )
        
        result = issue.to_dict()
        
        assert result['field'] == 'test_field'
        assert result['severity'] == 'warning'
        assert result['message'] == 'Test warning'
        assert result['record_id'] is None
        assert result['expected_value'] is None
        assert result['actual_value'] is None


class TestValidationResult:
    """Test ValidationResult class."""
    
    def test_validation_result_properties(self):
        """Test ValidationResult properties."""
        issues = [
            ValidationIssue('field1', ValidationSeverity.ERROR, 'Error 1'),
            ValidationIssue('field2', ValidationSeverity.WARNING, 'Warning 1'),
            ValidationIssue('field3', ValidationSeverity.CRITICAL, 'Critical 1'),
            ValidationIssue('field4', ValidationSeverity.INFO, 'Info 1')
        ]
        
        result = ValidationResult(
            total_records=100,
            valid_records=80,
            issues=issues
        )
        
        assert result.total_records == 100
        assert result.valid_records == 80
        assert result.invalid_records == 20
        assert result.validation_rate == 80.0
        assert result.error_count == 1
        assert result.warning_count == 1
        assert result.critical_count == 1
    
    def test_validation_result_zero_records(self):
        """Test ValidationResult with zero records."""
        result = ValidationResult(
            total_records=0,
            valid_records=0,
            issues=[]
        )
        
        assert result.validation_rate == 0.0
        assert result.invalid_records == 0
    
    def test_get_issues_by_severity(self):
        """Test filtering issues by severity."""
        issues = [
            ValidationIssue('field1', ValidationSeverity.ERROR, 'Error 1'),
            ValidationIssue('field2', ValidationSeverity.ERROR, 'Error 2'),
            ValidationIssue('field3', ValidationSeverity.WARNING, 'Warning 1')
        ]
        
        result = ValidationResult(100, 90, issues)
        
        error_issues = result.get_issues_by_severity(ValidationSeverity.ERROR)
        warning_issues = result.get_issues_by_severity(ValidationSeverity.WARNING)
        
        assert len(error_issues) == 2
        assert len(warning_issues) == 1
        assert all(i.severity == ValidationSeverity.ERROR for i in error_issues)
    
    def test_get_issues_by_field(self):
        """Test filtering issues by field."""
        issues = [
            ValidationIssue('field1', ValidationSeverity.ERROR, 'Error 1'),
            ValidationIssue('field1', ValidationSeverity.WARNING, 'Warning 1'),
            ValidationIssue('field2', ValidationSeverity.ERROR, 'Error 2')
        ]
        
        result = ValidationResult(100, 90, issues)
        
        field1_issues = result.get_issues_by_field('field1')
        field2_issues = result.get_issues_by_field('field2')
        
        assert len(field1_issues) == 2
        assert len(field2_issues) == 1
        assert all(i.field == 'field1' for i in field1_issues)
    
    def test_to_summary(self):
        """Test ValidationResult to_summary."""
        issues = [
            ValidationIssue('field1', ValidationSeverity.ERROR, 'Error 1'),
            ValidationIssue('field2', ValidationSeverity.WARNING, 'Warning 1')
        ]
        
        result = ValidationResult(100, 90, issues)
        summary = result.to_summary()
        
        assert summary['total_records'] == 100
        assert summary['valid_records'] == 90
        assert summary['invalid_records'] == 10
        assert summary['validation_rate'] == 90.0
        assert summary['total_issues'] == 2
        assert summary['error_issues'] == 1
        assert summary['warning_issues'] == 1


class TestTeamDataValidator:
    """Test TeamDataValidator class."""
    
    @pytest.fixture
    def validator(self):
        """Create team data validator."""
        return TeamDataValidator()
    
    def test_valid_team_data(self, validator):
        """Test validation of valid team data."""
        data = pd.DataFrame({
            'team_abbr': ['SF', 'KC', 'DAL'],
            'team_name': ['San Francisco', 'Kansas City', 'Dallas'],
            'team_nick': ['49ers', 'Chiefs', 'Cowboys']
        })
        
        result = validator.validate(data)
        
        assert result.total_records == 3
        assert result.valid_records == 3
        assert result.validation_rate == 100.0
        assert len(result.issues) == 0
    
    def test_missing_required_fields(self, validator):
        """Test validation with missing required fields."""
        data = pd.DataFrame({
            'team_name': ['San Francisco', 'Kansas City']
            # Missing team_abbr
        })
        
        result = validator.validate(data)
        
        assert result.total_records == 2
        critical_issues = result.get_issues_by_severity(ValidationSeverity.CRITICAL)
        assert len(critical_issues) == 1
        assert 'team_abbr' in critical_issues[0].message
    
    def test_invalid_team_abbreviations(self, validator):
        """Test validation with invalid team abbreviations."""
        data = pd.DataFrame({
            'team_abbr': ['SF', 'INVALID', 'DAL'],
            'team_name': ['San Francisco', 'Invalid Team', 'Dallas']
        })
        
        result = validator.validate(data)
        
        error_issues = result.get_issues_by_severity(ValidationSeverity.ERROR)
        invalid_team_issues = [i for i in error_issues if 'Invalid team abbreviation' in i.message]
        assert len(invalid_team_issues) == 1
        assert 'INVALID' in invalid_team_issues[0].message
    
    def test_duplicate_team_abbreviations(self, validator):
        """Test validation with duplicate team abbreviations."""
        data = pd.DataFrame({
            'team_abbr': ['SF', 'SF', 'DAL'],
            'team_name': ['San Francisco', 'San Francisco Duplicate', 'Dallas']
        })
        
        result = validator.validate(data)
        
        error_issues = result.get_issues_by_severity(ValidationSeverity.ERROR)
        duplicate_issues = [i for i in error_issues if 'Duplicate team abbreviation' in i.message]
        assert len(duplicate_issues) == 1
        assert 'SF' in duplicate_issues[0].message
    
    def test_invalid_abbreviation_format(self, validator):
        """Test validation with invalid abbreviation format."""
        data = pd.DataFrame({
            'team_abbr': ['SF', 'kc', '1DAL', 'TOOLONG'],
            'team_name': ['San Francisco', 'Kansas City', 'Dallas', 'Too Long']
        })
        
        result = validator.validate(data)
        
        error_issues = result.get_issues_by_severity(ValidationSeverity.ERROR)
        format_issues = [i for i in error_issues if 'Invalid abbreviation format' in i.message]
        assert len(format_issues) == 3  # kc, 1DAL, TOOLONG


class TestPlayerDataValidator:
    """Test PlayerDataValidator class."""
    
    @pytest.fixture
    def validator(self):
        """Create player data validator."""
        return PlayerDataValidator()
    
    def test_valid_player_data(self, validator):
        """Test validation of valid player data."""
        data = pd.DataFrame({
            'player_id': ['00-0012345', '00-0012346'],
            'full_name': ['John Doe', 'Jane Smith'],
            'team_abbr': ['SF', 'KC'],
            'position': ['QB', 'RB'],
            'height': [74, 70],
            'weight': [220, 180],
            'age': [28, 25],
            'jersey_number': [12, 23]
        })
        
        result = validator.validate(data)
        
        assert result.total_records == 2
        assert result.valid_records == 2
        assert result.validation_rate == 100.0
        assert len(result.issues) == 0
    
    def test_missing_required_fields(self, validator):
        """Test validation with missing required fields."""
        data = pd.DataFrame({
            'full_name': ['John Doe', 'Jane Smith']
            # Missing player_id
        })
        
        result = validator.validate(data)
        
        critical_issues = result.get_issues_by_severity(ValidationSeverity.CRITICAL)
        assert len(critical_issues) == 1
        assert 'player_id' in critical_issues[0].message
    
    def test_unusual_player_id_format(self, validator):
        """Test validation with unusual player ID format."""
        data = pd.DataFrame({
            'player_id': ['00-0012345', 'UNUSUAL_ID', '123456789'],
            'full_name': ['John Doe', 'Jane Smith', 'Bob Johnson']
        })
        
        result = validator.validate(data)
        
        warning_issues = result.get_issues_by_severity(ValidationSeverity.WARNING)
        id_issues = [i for i in warning_issues if 'Unusual player ID format' in i.message]
        assert len(id_issues) == 2  # UNUSUAL_ID and 123456789
    
    def test_invalid_physical_attributes(self, validator):
        """Test validation with invalid physical attributes."""
        data = pd.DataFrame({
            'player_id': ['00-0012345', '00-0012346', '00-0012347'],
            'full_name': ['John Doe', 'Jane Smith', 'Bob Johnson'],
            'height': [50, 74, 90],  # Too short, normal, too tall
            'weight': [100, 220, 500],  # Too light, normal, too heavy
            'age': [15, 28, 60],  # Too young, normal, too old
            'jersey_number': [-1, 12, 150]  # Invalid, normal, invalid
        })
        
        result = validator.validate(data)
        
        warning_issues = result.get_issues_by_severity(ValidationSeverity.WARNING)
        range_issues = [i for i in warning_issues if 'outside expected range' in i.message]
        assert len(range_issues) == 8  # 2 for each attribute


class TestGameDataValidator:
    """Test GameDataValidator class."""
    
    @pytest.fixture
    def validator(self):
        """Create game data validator."""
        return GameDataValidator()
    
    def test_valid_game_data(self, validator):
        """Test validation of valid game data."""
        data = pd.DataFrame({
            'game_id': ['2023_01_SF_KC', '2023_02_DAL_GB'],
            'season': [2023, 2023],
            'season_type': ['REG', 'REG'],
            'home_team': ['KC', 'GB'],
            'away_team': ['SF', 'DAL'],
            'week': [1, 2],
            'home_score': [24, 28],
            'away_score': [21, 14]
        })
        
        result = validator.validate(data)
        
        assert result.total_records == 2
        assert result.valid_records == 2
        assert result.validation_rate == 100.0
        assert len(result.issues) == 0
    
    def test_same_team_playing_itself(self, validator):
        """Test validation when team plays against itself."""
        data = pd.DataFrame({
            'game_id': ['2023_01_SF_SF'],
            'season': [2023],
            'home_team': ['SF'],
            'away_team': ['SF']
        })
        
        result = validator.validate(data)
        
        error_issues = result.get_issues_by_severity(ValidationSeverity.ERROR)
        same_team_issues = [i for i in error_issues if 'cannot play against itself' in i.message]
        assert len(same_team_issues) == 1
    
    def test_invalid_season_type(self, validator):
        """Test validation with invalid season type."""
        data = pd.DataFrame({
            'game_id': ['2023_01_SF_KC'],
            'season': [2023],
            'season_type': ['INVALID'],
            'home_team': ['KC'],
            'away_team': ['SF']
        })
        
        result = validator.validate(data)
        
        error_issues = result.get_issues_by_severity(ValidationSeverity.ERROR)
        season_type_issues = [i for i in error_issues if 'Invalid season type' in i.message]
        assert len(season_type_issues) == 1
    
    def test_invalid_week_numbers(self, validator):
        """Test validation with invalid week numbers."""
        data = pd.DataFrame({
            'game_id': ['2023_00_SF_KC', '2023_25_DAL_GB'],
            'season': [2023, 2023],
            'home_team': ['KC', 'GB'],
            'away_team': ['SF', 'DAL'],
            'week': [0, 25]  # Invalid weeks
        })
        
        result = validator.validate(data)
        
        warning_issues = result.get_issues_by_severity(ValidationSeverity.WARNING)
        week_issues = [i for i in warning_issues if 'Week outside normal range' in i.message]
        assert len(week_issues) == 2


class TestPlayDataValidator:
    """Test PlayDataValidator class."""
    
    @pytest.fixture
    def validator(self):
        """Create play data validator."""
        return PlayDataValidator()
    
    def test_valid_play_data(self, validator):
        """Test validation of valid play data."""
        data = pd.DataFrame({
            'play_id': ['2023_01_SF_KC_1', '2023_01_SF_KC_2'],
            'game_id': ['2023_01_SF_KC', '2023_01_SF_KC'],
            'season': [2023, 2023],
            'posteam': ['SF', 'KC'],
            'defteam': ['KC', 'SF'],
            'play_type': ['pass', 'run'],
            'qtr': [1, 1],
            'down': [1, 2],
            'ydstogo': [10, 7],
            'yardline_100': [75, 68],
            'yards_gained': [12, 5]
        })
        
        result = validator.validate(data)
        
        assert result.total_records == 2
        assert result.valid_records == 2
        assert result.validation_rate == 100.0
        assert len(result.issues) == 0
    
    def test_invalid_down_numbers(self, validator):
        """Test validation with invalid down numbers."""
        data = pd.DataFrame({
            'play_id': ['2023_01_SF_KC_1', '2023_01_SF_KC_2'],
            'game_id': ['2023_01_SF_KC', '2023_01_SF_KC'],
            'season': [2023, 2023],
            'down': [0, 5]  # Invalid downs
        })
        
        result = validator.validate(data)
        
        warning_issues = result.get_issues_by_severity(ValidationSeverity.WARNING)
        down_issues = [i for i in warning_issues if 'Invalid down' in i.message]
        assert len(down_issues) == 2
    
    def test_invalid_quarter_numbers(self, validator):
        """Test validation with invalid quarter numbers."""
        data = pd.DataFrame({
            'play_id': ['2023_01_SF_KC_1', '2023_01_SF_KC_2'],
            'game_id': ['2023_01_SF_KC', '2023_01_SF_KC'],
            'season': [2023, 2023],
            'qtr': [0, 6]  # Invalid quarters
        })
        
        result = validator.validate(data)
        
        warning_issues = result.get_issues_by_severity(ValidationSeverity.WARNING)
        qtr_issues = [i for i in warning_issues if 'Quarter outside normal range' in i.message]
        assert len(qtr_issues) == 2
    
    def test_unusual_play_types(self, validator):
        """Test validation with unusual play types."""
        data = pd.DataFrame({
            'play_id': ['2023_01_SF_KC_1', '2023_01_SF_KC_2'],
            'game_id': ['2023_01_SF_KC', '2023_01_SF_KC'],
            'season': [2023, 2023],
            'play_type': ['unusual_play', 'weird_play']
        })
        
        result = validator.validate(data)
        
        warning_issues = result.get_issues_by_severity(ValidationSeverity.WARNING)
        play_type_issues = [i for i in warning_issues if 'Unusual play type' in i.message]
        assert len(play_type_issues) == 2


class TestNFLDataValidator:
    """Test base NFLDataValidator functionality."""
    
    @pytest.fixture
    def validator(self):
        """Create NFL data validator."""
        return NFLDataValidator(strict_mode=False)
    
    @pytest.fixture 
    def strict_validator(self):
        """Create strict NFL data validator."""
        return NFLDataValidator(strict_mode=True)
    
    def test_strict_mode_converts_warnings_to_errors(self, strict_validator):
        """Test that strict mode converts warnings to errors."""
        strict_validator.add_issue(
            field='test_field',
            severity=ValidationSeverity.WARNING,
            message='Test warning'
        )
        
        assert len(strict_validator.issues) == 1
        assert strict_validator.issues[0].severity == ValidationSeverity.ERROR
    
    def test_normal_mode_preserves_warnings(self, validator):
        """Test that normal mode preserves warnings."""
        validator.add_issue(
            field='test_field',
            severity=ValidationSeverity.WARNING,
            message='Test warning'
        )
        
        assert len(validator.issues) == 1
        assert validator.issues[0].severity == ValidationSeverity.WARNING
    
    def test_clear_issues(self, validator):
        """Test clearing validation issues."""
        validator.add_issue('field1', ValidationSeverity.ERROR, 'Error 1')
        validator.add_issue('field2', ValidationSeverity.WARNING, 'Warning 1')
        
        assert len(validator.issues) == 2
        
        validator.clear_issues()
        assert len(validator.issues) == 0
    
    def test_validate_team_abbreviations(self, validator):
        """Test team abbreviation validation."""
        data = pd.DataFrame({
            'home_team': ['SF', 'INVALID', 'KC'],
            'away_team': ['DAL', 'GB', 'BADTEAM']
        })
        
        validator.validate_team_abbreviations(data, ['home_team', 'away_team'])
        
        error_issues = [i for i in validator.issues if i.severity == ValidationSeverity.ERROR]
        assert len(error_issues) == 2  # INVALID and BADTEAM
        
        invalid_teams = [i.actual_value for i in error_issues]
        assert 'INVALID' in invalid_teams
        assert 'BADTEAM' in invalid_teams
    
    def test_validate_seasons(self, validator):
        """Test season validation."""
        data = pd.DataFrame({
            'season': [2023, 1990, 2050, None]  # valid, too old, too new, missing
        })
        
        validator.validate_seasons(data)
        
        error_issues = [i for i in validator.issues if i.severity == ValidationSeverity.ERROR]
        assert len(error_issues) == 3  # 1990, 2050, None
    
    def test_validate_dates(self, validator):
        """Test date validation."""
        data = pd.DataFrame({
            'game_date': ['2023-09-10', 'invalid-date', '1800-01-01', None]
        })
        
        validator.validate_dates(data, ['game_date'])
        
        # Should have issues for invalid date, old date, and missing date
        issues = validator.issues
        assert len(issues) == 3
        
        error_issues = [i for i in issues if i.severity == ValidationSeverity.ERROR]
        warning_issues = [i for i in issues if i.severity == ValidationSeverity.WARNING]
        
        assert len(error_issues) == 1  # invalid-date
        assert len(warning_issues) == 2  # 1800-01-01, None