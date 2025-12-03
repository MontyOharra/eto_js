"""Exceptions for output execution processing"""


class OutputExecutionError(Exception):
    """
    Exception raised when output execution processing fails.

    This can occur during:
    - Order creation/update in the Access database
    - Email sending
    - Address resolution
    - Any other step in the output execution pipeline
    """
    pass
