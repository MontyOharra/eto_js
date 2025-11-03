"""Service layer exceptions"""


class ServiceError(Exception):
    """Base service exception"""
    pass


class ObjectNotFoundError(ServiceError):
    """Resource not found (404)"""
    pass

class BusinessLogicError(ServiceError):
    """Business logic validation failed"""
    pass

class ValidationError(ServiceError):
    """Data validation failed (400)"""
    pass

class ConflictError(ServiceError):
    """Resource state conflict (409)"""
    pass

class ExternalServiceError(ServiceError):
    """External service communication failed"""
    pass