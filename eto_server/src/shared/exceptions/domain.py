"""Domain layer exceptions"""


class DomainError(Exception):
    """Base domain exception"""
    pass


class InvalidStateError(DomainError):
    """Domain object is in an invalid state"""
    pass


class DomainValidationError(DomainError):
    """Domain validation rules violated"""
    pass