"""Repository layer exceptions"""


class RepositoryError(Exception):
    """Base repository exception"""
    pass


class ValidationError(RepositoryError):
    """Data validation failed"""
    pass


class DatabaseConnectionError(RepositoryError):
    """Database connection failed"""
    pass


class DuplicateKeyError(RepositoryError):
    """Attempt to create duplicate record"""
    pass