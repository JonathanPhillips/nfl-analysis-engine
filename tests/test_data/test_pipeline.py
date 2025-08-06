"""Tests for data validation and cleaning pipeline."""

import pytest
import pandas as pd
from datetime import datetime

from src.data.pipeline import (
    PipelineConfig, PipelineResult, DataValidationPipeline
)
from src.data.validators import ValidationSeverity, ValidationIssue, ValidationResult


class TestPipelineConfig:
    """Test PipelineConfig class."""
    
    def test_default_config(self):
        """Test default pipeline configuration."""
        config = PipelineConfig()
        
        assert config.strict_validation is False
        assert config.min_validation_rate == 0.8
        assert config.fail_on_critical is True
        assert config.fail_on_errors is False
        assert config.enable_cleaning is True
        assert config.strict_cleaning is False
        assert config.preserve_original is True
        assert config.detailed_logging is True
        assert config.generate_report is True
    
    def test_custom_config(self):
        """Test custom pipeline configuration."""
        config = PipelineConfig(
            strict_validation=True,
            min_validation_rate=0.9,
            fail_on_errors=True,
            enable_cleaning=False
        )
        
        assert config.strict_validation is True
        assert config.min_validation_rate == 0.9
        assert config.fail_on_errors is True
        assert config.enable_cleaning is False


class TestPipelineResult:
    """Test PipelineResult class."""
    
    def test_pipeline_result_creation(self):
        """Test PipelineResult creation."""
        validation_result = ValidationResult(
            total_records=100,
            valid_records=90,
            issues=[]
        )
        
        result = PipelineResult(
            original_records=100,
            data_type='teams',
            validation_result=validation_result,
            validation_passed=True,
            cleaning_enabled=True,
            cleaning_actions=['Action 1', 'Action 2'],
            cleaned_records=95
        )
        
        assert result.original_records == 100
        assert result.data_type == 'teams'
        assert result.validation_passed is True
        assert result.cleaning_enabled is True
        assert len(result.cleaning_actions) == 2
        assert result.cleaned_records == 95
    
    def test_to_summary(self):
        """Test PipelineResult to_summary method."""
        validation_result = ValidationResult(
            total_records=100,
            valid_records=85,
            issues=[
                ValidationIssue('field1', ValidationSeverity.WARNING, 'Warning 1'),
                ValidationIssue('field2', ValidationSeverity.ERROR, 'Error 1')
            ]
        )
        
        result = PipelineResult(
            original_records=100,
            data_type='players',
            validation_result=validation_result,
            validation_passed=True,
            cleaning_enabled=True,
            cleaning_actions=['Cleaned names', 'Removed duplicates'],
            cleaned_records=98,
            processing_time=1.5
        )
        
        summary = result.to_summary()
        
        assert summary['data_type'] == 'players'
        assert summary['original_records'] == 100
        assert summary['validation_passed'] is True
        assert summary['cleaning_enabled'] is True
        assert summary['processing_time_seconds'] == 1.5
        assert summary['validation']['total_records'] == 100
        assert summary['validation']['valid_records'] == 85
        assert summary['cleaning']['actions_count'] == 2
        assert summary['cleaning']['cleaned_records'] == 98


class TestDataValidationPipeline:
    """Test DataValidationPipeline class."""
    
    @pytest.fixture
    def pipeline(self):
        """Create basic pipeline."""
        return DataValidationPipeline()
    
    @pytest.fixture
    def strict_pipeline(self):
        """Create strict pipeline."""
        config = PipelineConfig(
            strict_validation=True,
            fail_on_errors=True,
            min_validation_rate=0.95
        )
        return DataValidationPipeline(config)
    
    def test_pipeline_initialization(self, pipeline):
        """Test pipeline initialization."""
        assert pipeline.config.enable_cleaning is True
        assert len(pipeline.validators) == 4
        assert len(pipeline.cleaners) == 4
        assert 'teams' in pipeline.validators
        assert 'players' in pipeline.validators
        assert 'games' in pipeline.validators
        assert 'plays' in pipeline.validators
    
    def test_validate_data_teams(self, pipeline):
        """Test data validation for teams."""
        data = pd.DataFrame({
            'team_abbr': ['SF', 'KC', 'DAL'],
            'team_name': ['San Francisco', 'Kansas City', 'Dallas']
        })
        
        result = pipeline.validate_data(data, 'teams')
        
        assert isinstance(result, ValidationResult)
        assert result.total_records == 3
        assert result.validation_rate == 100.0
        assert len(result.issues) == 0
    
    def test_validate_data_invalid_type(self, pipeline):
        """Test validation with invalid data type."""
        data = pd.DataFrame()
        
        with pytest.raises(ValueError, match="Unsupported data type"):
            pipeline.validate_data(data, 'invalid_type')
    
    def test_clean_data_teams(self, pipeline):
        """Test data cleaning for teams."""
        data = pd.DataFrame({
            'team_abbr': ['sf', 'OAK', 'DAL'],
            'team_name': ['san francisco', 'Oakland', 'Dallas']
        })
        
        cleaned_data, cleaning_actions = pipeline.clean_data(data, 'teams')
        
        assert len(cleaned_data) == 3
        assert len(cleaning_actions) > 0
        assert cleaned_data['team_abbr'].iloc[0] == 'SF'  # Uppercase
        assert cleaned_data['team_abbr'].iloc[1] == 'LV'  # OAK -> LV mapping
    
    def test_clean_data_invalid_type(self, pipeline):
        """Test cleaning with invalid data type."""
        data = pd.DataFrame()
        
        with pytest.raises(ValueError, match="Unsupported data type"):
            pipeline.clean_data(data, 'invalid_type')
    
    def test_check_validation_requirements_pass(self, pipeline):
        """Test validation requirements check - passing."""
        validation_result = ValidationResult(
            total_records=100,
            valid_records=85,
            issues=[
                ValidationIssue('field1', ValidationSeverity.WARNING, 'Warning 1')
            ]
        )
        
        assert pipeline.check_validation_requirements(validation_result) is True
    
    def test_check_validation_requirements_fail_critical(self, pipeline):
        """Test validation requirements check - fail on critical."""
        validation_result = ValidationResult(
            total_records=100,
            valid_records=90,
            issues=[
                ValidationIssue('field1', ValidationSeverity.CRITICAL, 'Critical error')
            ]
        )
        
        assert pipeline.check_validation_requirements(validation_result) is False
    
    def test_check_validation_requirements_fail_rate(self, pipeline):
        """Test validation requirements check - fail on low rate."""
        validation_result = ValidationResult(
            total_records=100,
            valid_records=70,  # 70% < 80% minimum
            issues=[]
        )
        
        assert pipeline.check_validation_requirements(validation_result) is False
    
    def test_check_validation_requirements_strict_errors(self, strict_pipeline):
        """Test validation requirements check with strict error handling."""
        validation_result = ValidationResult(
            total_records=100,
            valid_records=85,
            issues=[
                ValidationIssue('field1', ValidationSeverity.ERROR, 'Error 1')
            ]
        )
        
        assert strict_pipeline.check_validation_requirements(validation_result) is False
    
    def test_process_data_success(self, pipeline):
        """Test successful data processing."""
        data = pd.DataFrame({
            'team_abbr': ['sf', 'KC', 'OAK'],
            'team_name': ['san francisco', 'Kansas City', 'Oakland']
        })
        
        result = pipeline.process_data(data, 'teams')
        
        assert isinstance(result, PipelineResult)
        assert result.original_records == 3
        assert result.data_type == 'teams'
        assert result.validation_passed is True
        assert result.cleaning_enabled is True
        assert len(result.cleaning_actions) > 0
        assert result.processed_data is not None
        assert len(result.processed_data) == 3
        assert result.processing_time > 0
        
        # Check that OAK was mapped to LV
        assert 'LV' in result.processed_data['team_abbr'].values
    
    def test_process_data_validation_failure(self, strict_pipeline):
        """Test data processing with validation failure."""
        data = pd.DataFrame({
            'team_abbr': ['SF', 'INVALID_TEAM'],
            'team_name': ['San Francisco', 'Invalid']
        })
        
        result = strict_pipeline.process_data(data, 'teams')
        
        assert result.validation_passed is False
        assert len(result.validation_result.issues) > 0
        # Even with validation failure, cleaning should still run
        assert result.cleaning_enabled is True
    
    def test_process_data_players(self, pipeline):
        """Test processing player data."""
        data = pd.DataFrame({
            'player_id': ['00-0012345', '00-0012346'],
            'full_name': ['  john doe  ', 'Jane Smith'],
            'team_abbr': ['sf', 'KC'],
            'position': ['qb', 'RB'],
            'height': ['6-2', '5-9']
        })
        
        result = pipeline.process_data(data, 'players')
        
        assert result.validation_passed is True
        assert result.processed_data is not None
        
        # Check cleaning was applied
        assert result.processed_data['full_name'].iloc[0] == 'John Doe'  # Name cleaned
        assert result.processed_data['team_abbr'].iloc[0] == 'SF'  # Uppercase
        assert result.processed_data['position'].iloc[0] == 'QB'  # Uppercase
        assert result.processed_data['height'].iloc[0] == 74  # Height parsed
    
    def test_process_data_games(self, pipeline):
        """Test processing game data."""
        data = pd.DataFrame({
            'game_id': ['2023_01_sf_kc', '2023_02_dal_gb'],
            'season': [2023, 2023],
            'home_team': ['kc', 'gb'],
            'away_team': ['sf', 'dal'],
            'game_date': ['2023-09-10', '2023-09-17']
        })
        
        result = pipeline.process_data(data, 'games')
        
        assert result.validation_passed is True
        assert result.processed_data is not None
        
        # Check cleaning was applied
        assert result.processed_data['game_id'].iloc[0] == '2023_01_SF_KC'  # ID cleaned
        assert result.processed_data['home_team'].iloc[0] == 'KC'  # Uppercase
        assert result.processed_data['away_team'].iloc[0] == 'SF'  # Uppercase
    
    def test_process_data_plays(self, pipeline):
        """Test processing play data."""
        data = pd.DataFrame({
            'play_id': ['2023_01_SF_KC_1', '2023_01_SF_KC_2'],
            'game_id': ['2023_01_SF_KC', '2023_01_SF_KC'],
            'season': [2023, 2023],
            'posteam': ['sf', 'kc'],
            'play_type': ['Pass', 'rushing']
        })
        
        result = pipeline.process_data(data, 'plays')
        
        assert result.validation_passed is True
        assert result.processed_data is not None
        
        # Check cleaning was applied
        assert result.processed_data['posteam'].iloc[0] == 'SF'  # Uppercase
        assert result.processed_data['play_type'].iloc[0] == 'pass'  # Standardized
        assert result.processed_data['play_type'].iloc[1] == 'run'  # Mapped
    
    def test_batch_process(self, pipeline):
        """Test batch processing of multiple datasets."""
        datasets = {
            'teams': pd.DataFrame({
                'team_abbr': ['SF', 'KC'],
                'team_name': ['San Francisco', 'Kansas City']
            }),
            'players': pd.DataFrame({
                'player_id': ['00-0012345', '00-0012346'],
                'full_name': ['John Doe', 'Jane Smith']
            })
        }
        
        results = pipeline.batch_process(datasets)
        
        assert len(results) == 2
        assert 'teams' in results
        assert 'players' in results
        
        assert results['teams'].validation_passed is True
        assert results['players'].validation_passed is True
        
        assert results['teams'].data_type == 'teams'
        assert results['players'].data_type == 'players'
    
    def test_batch_process_with_error(self, pipeline):
        """Test batch processing with one dataset causing an error."""
        datasets = {
            'teams': pd.DataFrame({
                'team_abbr': ['SF', 'KC'],
                'team_name': ['San Francisco', 'Kansas City']
            }),
            'invalid': pd.DataFrame({
                'some_field': ['value1', 'value2']
            })
        }
        
        results = pipeline.batch_process(datasets)
        
        assert len(results) == 2
        assert results['teams'].validation_passed is True
        assert results['invalid'].validation_passed is False
        assert len(results['invalid'].validation_result.issues) > 0
    
    def test_generate_validation_report(self, pipeline):
        """Test validation report generation."""
        # Create some sample results
        results = [
            PipelineResult(
                original_records=100,
                data_type='teams',
                validation_result=ValidationResult(100, 95, [
                    ValidationIssue('field1', ValidationSeverity.WARNING, 'Warning 1')
                ]),
                validation_passed=True,
                cleaning_enabled=True,
                cleaning_actions=['Action 1'],
                cleaned_records=98,
                processing_time=1.0
            ),
            PipelineResult(
                original_records=50,
                data_type='players',
                validation_result=ValidationResult(50, 45, [
                    ValidationIssue('field2', ValidationSeverity.ERROR, 'Error 1')
                ]),
                validation_passed=False,
                cleaning_enabled=True,
                cleaning_actions=['Action 2', 'Action 3'],
                cleaned_records=48,
                processing_time=0.5
            )
        ]
        
        report = pipeline.generate_validation_report(results)
        
        assert 'generated_at' in report
        assert 'pipeline_config' in report
        assert 'summary' in report
        assert 'results_by_type' in report
        assert 'issue_analysis' in report
        
        # Check summary
        summary = report['summary']
        assert summary['total_datasets'] == 2
        assert summary['total_records_processed'] == 150
        assert summary['datasets_passed'] == 1
        assert summary['total_processing_time'] == 1.5
        assert summary['cleaning_actions_performed'] == 3
        
        # Check results by type
        assert 'teams' in report['results_by_type']
        assert 'players' in report['results_by_type']
        assert len(report['results_by_type']['teams']) == 1
        assert len(report['results_by_type']['players']) == 1
        
        # Check issue analysis
        assert report['issue_analysis']['statistics']['total_issues'] == 2
        assert report['issue_analysis']['statistics']['warning_issues'] == 1
        assert report['issue_analysis']['statistics']['error_issues'] == 1
        assert len(report['issue_analysis']['most_common_issues']) > 0
    
    def test_generate_validation_report_empty(self, pipeline):
        """Test validation report generation with empty results."""
        results = []
        
        report = pipeline.generate_validation_report(results)
        
        assert report['summary']['total_datasets'] == 0
        assert report['summary']['total_records_processed'] == 0
        assert len(report['results_by_type']) == 0
        # Should not have issue_analysis for empty results
        assert 'issue_analysis' not in report
    
    def test_pipeline_config_effects(self):
        """Test that pipeline configuration affects behavior."""
        # Test with cleaning disabled
        no_clean_config = PipelineConfig(enable_cleaning=False)
        no_clean_pipeline = DataValidationPipeline(no_clean_config)
        
        data = pd.DataFrame({
            'team_abbr': ['sf', 'OAK'],
            'team_name': ['san francisco', 'Oakland']
        })
        
        result = no_clean_pipeline.process_data(data, 'teams')
        
        assert result.cleaning_enabled is False
        assert len(result.cleaning_actions) == 0
        # Data should not be cleaned
        assert result.processed_data['team_abbr'].iloc[0] == 'sf'  # Not uppercased
    
    def test_pipeline_preserves_original(self):
        """Test that pipeline preserves original data when configured."""
        config = PipelineConfig(preserve_original=True)
        pipeline = DataValidationPipeline(config)
        
        original_data = pd.DataFrame({
            'team_abbr': ['sf', 'KC'],
            'team_name': ['san francisco', 'Kansas City']
        })
        
        result = pipeline.process_data(original_data, 'teams')
        
        # Original data should be unchanged
        assert original_data['team_abbr'].iloc[0] == 'sf'
        # But processed data should be cleaned
        assert result.processed_data['team_abbr'].iloc[0] == 'SF'