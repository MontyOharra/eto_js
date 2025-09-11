"""
Shared Types
Common types, enums, and constants used across all features
"""

from .common import *
from .email import *
from .pipeline import *

__all__ = [
    # Common types
    'Status',
    'ProcessingStatus',
    
    # Email types
    'EmailConnectionConfig',
    'ConnectionStatus', 
    'EmailData',
    'ConnectionSettings',
    'FilterRule',
    'FilterConfig',
    'MonitoringSettings',
    'ConfigurationData',
    
    # Pipeline types will be added here
]