"""Shared exceptions for transformation pipeline system"""

from .repository import RepositoryError, ObjectNotFoundError, ValidationError, DatabaseConnectionError, DuplicateKeyError
from .pipeline_validation import PipelineValidationFailedException
from .module_definitions import NotImplementedError
from .service import ServiceError
from .eto_processing import (
    EtoProcessingError,
    EtoStatusValidationError,
    EtoTemplateMatchingError,
    EtoDataExtractionError,
    EtoTransformationError
)

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
    'NotImplementedError',
    
    # Service errors
    'ServiceError',
    
    # ETO processing errors
    'EtoProcessingError',
    'EtoStatusValidationError',
    'EtoTemplateMatchingError',
    'EtoDataExtractionError',
    'EtoTransformationError'
]