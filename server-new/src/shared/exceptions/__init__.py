"""Shared exceptions for transformation pipeline system"""

from .repository import RepositoryError, ObjectNotFoundError, ValidationError, DatabaseConnectionError, DuplicateKeyError
from .service import ServiceError, ConflictError

__all__ = [
    # Repository errors
    'RepositoryError',
    'ObjectNotFoundError',
    'ValidationError',
    'DatabaseConnectionError',
    'DuplicateKeyError',

    # Service errors
    'ServiceError',
    'ConflictError',
]