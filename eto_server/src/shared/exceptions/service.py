"""Service layer exceptions"""


class ServiceError(Exception):
    """Base service exception"""
    pass


class BusinessLogicError(ServiceError):
    """Business logic validation failed"""
    pass


class ExternalServiceError(ServiceError):
    """External service communication failed"""
    pass