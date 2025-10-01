"""Repository layer exceptions"""


class RepositoryError(Exception):
    """Base repository exception"""
    pass


class ObjectNotFoundError(RepositoryError):
    """Object with given ID not found"""
    def __init__(self, object_type: str, object_id: any):
        self.object_type = object_type
        self.object_id = object_id
        super().__init__(f"{object_type} with id {object_id} not found")


class ValidationError(RepositoryError):
    """Data validation failed"""
    pass


class DatabaseConnectionError(RepositoryError):
    """Database connection failed"""
    pass


class DuplicateKeyError(RepositoryError):
    """Attempt to create duplicate record"""
    pass