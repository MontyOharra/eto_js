"""Shared exceptions for the ETO system"""

from .repository import (
    RepositoryError,
    ObjectNotFoundError,
    ValidationError,
    DatabaseConnectionError,
    DuplicateKeyError
)
from .service import (
    ServiceError,
    BusinessLogicError,
    ExternalServiceError
)
from .domain import (
    DomainError,
    InvalidStateError,
    DomainValidationError
)
from .eto_processing import (
    EtoProcessingError,
    EtoStatusValidationError,
    EtoTemplateMatchingError,
    EtoDataExtractionError,
    EtoTransformationError
)

__all__ = [
    # Repository
    'RepositoryError', 'ObjectNotFoundError', 'ValidationError',
    'DatabaseConnectionError', 'DuplicateKeyError',
    # Service
    'ServiceError', 'BusinessLogicError', 'ExternalServiceError',
    # Domain
    'DomainError', 'InvalidStateError', 'DomainValidationError',
    # ETO Processing
    'EtoProcessingError', 'EtoStatusValidationError',
    'EtoTemplateMatchingError', 'EtoDataExtractionError', 'EtoTransformationError'
]