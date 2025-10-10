"""Shared exceptions for transformation pipeline system"""

from .repository import RepositoryError, ObjectNotFoundError, ValidationError, DatabaseConnectionError, DuplicateKeyError
from .pipeline_validation import PipelineValidationFailedException
from .module_definitions import NotImplementedError

__all__ = [
    # Repository errors
    'RepositoryError',
    'ObjectNotFoundError',
    'ValidationError',
    'DatabaseConnectionError',
    'DuplicateKeyError',

    # Pipeline validation errors
    'PipelineValidationFailedException',

    # Module definitions errors
    'NotImplementedError'
]