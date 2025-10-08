"""Shared exceptions for transformation pipeline system"""

from .repository import RepositoryError, ObjectNotFoundError, ValidationError, DatabaseConnectionError, DuplicateKeyError
from .pipeline_validation import PipelineValidationError, PipelineValidationErrorCode

__all__ = [
    # Repository errors
    'RepositoryError',
    'ObjectNotFoundError',
    'ValidationError',
    'DatabaseConnectionError',
    'DuplicateKeyError',
    
    # Pipeline validation errors
    'PipelineValidationError',
    'PipelineValidationErrorCode'
]