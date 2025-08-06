"""Data ingestion and processing module."""

from .nfl_data_client import NFLDataClient, DataFetchConfig
from .data_loader import DataLoader, DataLoadResult
from .data_mapper import DataMapper
from .validators import (
    ValidationResult, ValidationSeverity, ValidationIssue,
    TeamDataValidator, PlayerDataValidator, GameDataValidator, PlayDataValidator
)
from .cleaners import (
    TeamDataCleaner, PlayerDataCleaner, GameDataCleaner, PlayDataCleaner
)
from .pipeline import DataValidationPipeline, PipelineConfig, PipelineResult

__all__ = [
    # Data integration
    'NFLDataClient',
    'DataFetchConfig',
    'DataLoader',
    'DataLoadResult',
    'DataMapper',
    
    # Validation
    'ValidationResult',
    'ValidationSeverity', 
    'ValidationIssue',
    'TeamDataValidator',
    'PlayerDataValidator', 
    'GameDataValidator',
    'PlayDataValidator',
    
    # Cleaning
    'TeamDataCleaner',
    'PlayerDataCleaner',
    'GameDataCleaner', 
    'PlayDataCleaner',
    
    # Pipeline
    'DataValidationPipeline',
    'PipelineConfig',
    'PipelineResult'
]