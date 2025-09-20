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

__all__ = [
    # Repository
    'RepositoryError', 'ObjectNotFoundError', 'ValidationError',
    'DatabaseConnectionError', 'DuplicateKeyError',
    # Service
    'ServiceError', 'BusinessLogicError', 'ExternalServiceError',
    # Domain
    'DomainError', 'InvalidStateError', 'DomainValidationError'
]