"""
Email Configuration Feature
Manages email ingestion configuration settings
"""
from .service import EmailConfigurationService
from .types import (
    EmailIngestionConfig,
    EmailFilterRule, 
    EmailConfigSummary,
    EmailConfigStats
)

__all__ = [
    'EmailConfigurationService',
    'EmailIngestionConfig',
    'EmailFilterRule',
    'EmailConfigSummary', 
    'EmailConfigStats'
]