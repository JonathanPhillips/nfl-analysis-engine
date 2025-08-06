"""Data validation and cleaning pipeline for NFL data."""

import logging
from typing import Dict, Any, List, Optional, Tuple
import pandas as pd
from datetime import datetime
from dataclasses import dataclass, field

from .validators import (
    ValidationResult, ValidationSeverity, ValidationIssue,
    TeamDataValidator, PlayerDataValidator, GameDataValidator, PlayDataValidator
)
from .cleaners import (
    TeamDataCleaner, PlayerDataCleaner, GameDataCleaner, PlayDataCleaner
)

logger = logging.getLogger(__name__)


@dataclass
class PipelineConfig:
    """Configuration for the validation and cleaning pipeline."""
    
    # Validation settings
    strict_validation: bool = False
    min_validation_rate: float = 0.8  # Minimum acceptable validation rate (80%)
    fail_on_critical: bool = True
    fail_on_errors: bool = False
    
    # Cleaning settings
    enable_cleaning: bool = True
    strict_cleaning: bool = False
    preserve_original: bool = True
    
    # Output settings
    detailed_logging: bool = True
    generate_report: bool = True


@dataclass
class PipelineResult:
    """Results from the validation and cleaning pipeline."""
    
    # Input data info
    original_records: int
    data_type: str
    
    # Validation results
    validation_result: ValidationResult
    validation_passed: bool
    
    # Cleaning results
    cleaning_enabled: bool
    cleaning_actions: List[str] = field(default_factory=list)
    cleaned_records: int = 0
    
    # Final data
    processed_data: Optional[pd.DataFrame] = None
    
    # Metadata
    processing_time: Optional[float] = None
    timestamp: datetime = field(default_factory=datetime.now)
    
    def to_summary(self) -> Dict[str, Any]:
        """Generate a summary of pipeline results."""
        summary = {
            'timestamp': self.timestamp.isoformat(),
            'data_type': self.data_type,
            'original_records': self.original_records,
            'validation': self.validation_result.to_summary(),
            'validation_passed': self.validation_passed,
            'cleaning_enabled': self.cleaning_enabled,
            'processing_time_seconds': self.processing_time
        }
        
        if self.cleaning_enabled:
            summary['cleaning'] = {
                'actions_count': len(self.cleaning_actions),
                'cleaned_records': self.cleaned_records,
                'actions': self.cleaning_actions
            }
        
        return summary


class DataValidationPipeline:
    """Orchestrates data validation and cleaning for NFL data."""
    
    def __init__(self, config: Optional[PipelineConfig] = None):
        """Initialize the pipeline.
        
        Args:
            config: Pipeline configuration, defaults to PipelineConfig()
        """
        self.config = config or PipelineConfig()
        
        # Initialize validators
        self.validators = {
            'teams': TeamDataValidator(strict_mode=self.config.strict_validation),
            'players': PlayerDataValidator(strict_mode=self.config.strict_validation),
            'games': GameDataValidator(strict_mode=self.config.strict_validation),
            'plays': PlayDataValidator(strict_mode=self.config.strict_validation)
        }
        
        # Initialize cleaners
        self.cleaners = {
            'teams': TeamDataCleaner(strict_mode=self.config.strict_cleaning),
            'players': PlayerDataCleaner(strict_mode=self.config.strict_cleaning),
            'games': GameDataCleaner(strict_mode=self.config.strict_cleaning),
            'plays': PlayDataCleaner(strict_mode=self.config.strict_cleaning)
        }
    
    def validate_data(self, data: pd.DataFrame, data_type: str) -> ValidationResult:
        """Validate data using the appropriate validator.
        
        Args:
            data: DataFrame to validate
            data_type: Type of data ('teams', 'players', 'games', 'plays')
            
        Returns:
            ValidationResult with validation details
            
        Raises:
            ValueError: If data_type is not supported
        """
        if data_type not in self.validators:
            raise ValueError(f"Unsupported data type: {data_type}. "
                           f"Supported types: {list(self.validators.keys())}")
        
        validator = self.validators[data_type]
        
        if self.config.detailed_logging:
            logger.info(f"Starting validation for {len(data)} {data_type} records")
        
        validation_result = validator.validate(data)
        
        if self.config.detailed_logging:
            logger.info(f"Validation completed: {validation_result.validation_rate:.1f}% valid, "
                       f"{len(validation_result.issues)} issues found")
        
        return validation_result
    
    def clean_data(self, data: pd.DataFrame, data_type: str) -> Tuple[pd.DataFrame, List[str]]:
        """Clean data using the appropriate cleaner.
        
        Args:
            data: DataFrame to clean
            data_type: Type of data ('teams', 'players', 'games', 'plays')
            
        Returns:
            Tuple of (cleaned_data, cleaning_actions)
            
        Raises:
            ValueError: If data_type is not supported
        """
        if data_type not in self.cleaners:
            raise ValueError(f"Unsupported data type: {data_type}. "
                           f"Supported types: {list(self.cleaners.keys())}")
        
        cleaner = self.cleaners[data_type]
        
        if self.config.detailed_logging:
            logger.info(f"Starting cleaning for {len(data)} {data_type} records")
        
        cleaned_data, cleaning_actions = cleaner.clean(data)
        
        if self.config.detailed_logging:
            logger.info(f"Cleaning completed: {len(cleaning_actions)} actions performed, "
                       f"{len(cleaned_data)} records remaining")
        
        return cleaned_data, cleaning_actions
    
    def check_validation_requirements(self, validation_result: ValidationResult) -> bool:
        """Check if validation results meet pipeline requirements.
        
        Args:
            validation_result: Results from validation
            
        Returns:
            True if validation passes requirements, False otherwise
        """
        # Check for critical issues
        if self.config.fail_on_critical and validation_result.critical_count > 0:
            logger.error(f"Pipeline failed: {validation_result.critical_count} critical issues found")
            return False
        
        # Check for error issues
        if self.config.fail_on_errors and validation_result.error_count > 0:
            logger.error(f"Pipeline failed: {validation_result.error_count} error issues found")
            return False
        
        # Check validation rate
        if validation_result.validation_rate < self.config.min_validation_rate * 100:
            logger.error(f"Pipeline failed: validation rate {validation_result.validation_rate:.1f}% "
                        f"below minimum {self.config.min_validation_rate * 100:.1f}%")
            return False
        
        return True
    
    def process_data(self, data: pd.DataFrame, data_type: str) -> PipelineResult:
        """Process data through the complete validation and cleaning pipeline.
        
        Args:
            data: DataFrame to process
            data_type: Type of data ('teams', 'players', 'games', 'plays')
            
        Returns:
            PipelineResult with all processing information
        """
        start_time = datetime.now()
        
        if self.config.detailed_logging:
            logger.info(f"Starting pipeline processing for {len(data)} {data_type} records")
        
        # Preserve original data if requested
        original_data = data.copy() if self.config.preserve_original else None
        
        # Step 1: Validation
        validation_result = self.validate_data(data, data_type)
        validation_passed = self.check_validation_requirements(validation_result)
        
        # Step 2: Cleaning (if enabled and validation didn't completely fail)
        cleaned_data = data
        cleaning_actions = []
        
        if self.config.enable_cleaning and (validation_passed or not self.config.fail_on_errors):
            cleaned_data, cleaning_actions = self.clean_data(data, data_type)
            
            # Re-validate cleaned data
            if cleaning_actions:  # Only re-validate if cleaning actions were performed
                if self.config.detailed_logging:
                    logger.info("Re-validating cleaned data")
                
                post_cleaning_validation = self.validate_data(cleaned_data, data_type)
                
                # Update validation result if cleaning improved it
                if post_cleaning_validation.validation_rate > validation_result.validation_rate:
                    validation_result = post_cleaning_validation
                    validation_passed = self.check_validation_requirements(validation_result)
                    
                    if self.config.detailed_logging:
                        logger.info(f"Cleaning improved validation rate to {validation_result.validation_rate:.1f}%")
        
        # Calculate processing time
        processing_time = (datetime.now() - start_time).total_seconds()
        
        # Create result
        result = PipelineResult(
            original_records=len(data),
            data_type=data_type,
            validation_result=validation_result,
            validation_passed=validation_passed,
            cleaning_enabled=self.config.enable_cleaning,
            cleaning_actions=cleaning_actions,
            cleaned_records=len(cleaned_data) if cleaned_data is not None else 0,
            processed_data=cleaned_data,
            processing_time=processing_time
        )
        
        if self.config.detailed_logging:
            logger.info(f"Pipeline processing completed in {processing_time:.2f}s")
        
        return result
    
    def generate_validation_report(self, results: List[PipelineResult]) -> Dict[str, Any]:
        """Generate a comprehensive validation report from multiple pipeline results.
        
        Args:
            results: List of PipelineResult objects
            
        Returns:
            Comprehensive report dictionary
        """
        report = {
            'generated_at': datetime.now().isoformat(),
            'pipeline_config': {
                'strict_validation': self.config.strict_validation,
                'min_validation_rate': self.config.min_validation_rate,
                'fail_on_critical': self.config.fail_on_critical,
                'fail_on_errors': self.config.fail_on_errors,
                'enable_cleaning': self.config.enable_cleaning
            },
            'summary': {
                'total_datasets': len(results),
                'total_records_processed': sum(r.original_records for r in results),
                'datasets_passed': sum(1 for r in results if r.validation_passed),
                'total_processing_time': sum(r.processing_time for r in results if r.processing_time),
                'cleaning_actions_performed': sum(len(r.cleaning_actions) for r in results)
            },
            'results_by_type': {}
        }
        
        # Group results by data type
        for result in results:
            data_type = result.data_type
            if data_type not in report['results_by_type']:
                report['results_by_type'][data_type] = []
            
            report['results_by_type'][data_type].append(result.to_summary())
        
        # Calculate aggregate statistics
        if results:
            all_issues = []
            for result in results:
                all_issues.extend(result.validation_result.issues)
            
            # Issue statistics
            issue_stats = {
                'total_issues': len(all_issues),
                'critical_issues': len([i for i in all_issues if i.severity == ValidationSeverity.CRITICAL]),
                'error_issues': len([i for i in all_issues if i.severity == ValidationSeverity.ERROR]),
                'warning_issues': len([i for i in all_issues if i.severity == ValidationSeverity.WARNING]),
                'info_issues': len([i for i in all_issues if i.severity == ValidationSeverity.INFO])
            }
            
            # Most common issues
            issue_messages = [issue.message for issue in all_issues]
            from collections import Counter
            most_common_issues = Counter(issue_messages).most_common(10)
            
            report['issue_analysis'] = {
                'statistics': issue_stats,
                'most_common_issues': [
                    {'message': msg, 'count': count} 
                    for msg, count in most_common_issues
                ]
            }
        
        return report
    
    def batch_process(self, datasets: Dict[str, pd.DataFrame]) -> Dict[str, PipelineResult]:
        """Process multiple datasets in batch.
        
        Args:
            datasets: Dictionary mapping data_type to DataFrame
            
        Returns:
            Dictionary mapping data_type to PipelineResult
        """
        results = {}
        
        logger.info(f"Starting batch processing for {len(datasets)} datasets")
        
        for data_type, data in datasets.items():
            try:
                result = self.process_data(data, data_type)
                results[data_type] = result
                
                if result.validation_passed:
                    logger.info(f"✓ {data_type}: {result.original_records} records processed successfully")
                else:
                    logger.warning(f"⚠ {data_type}: validation failed but processing completed")
                    
            except Exception as e:
                logger.error(f"✗ {data_type}: processing failed - {str(e)}")
                # Create a failure result
                results[data_type] = PipelineResult(
                    original_records=len(data),
                    data_type=data_type,
                    validation_result=ValidationResult(
                        total_records=len(data),
                        valid_records=0,
                        issues=[ValidationIssue(
                            field='pipeline',
                            severity=ValidationSeverity.CRITICAL,
                            message=f"Pipeline processing failed: {str(e)}"
                        )]
                    ),
                    validation_passed=False,
                    cleaning_enabled=self.config.enable_cleaning
                )
        
        logger.info(f"Batch processing completed: {len(results)} datasets processed")
        
        return results