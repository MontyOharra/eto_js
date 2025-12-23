"""Email integration exceptions"""


class EmailIntegrationError(Exception):
    """Base exception for email integration issues."""
    pass


class PermanentEmailError(EmailIntegrationError):
    """
    Error that won't resolve with retries.

    Examples:
    - Folder doesn't exist
    - Authentication failed (credentials changed)
    - Account disabled

    When raised, the poller should deactivate the config immediately.
    """
    pass


class TransientEmailError(EmailIntegrationError):
    """
    Error that may resolve with retries.

    Examples:
    - Network timeout
    - Connection dropped
    - Server temporarily unavailable

    When raised, the poller should retry up to MAX_CONSECUTIVE_ERRORS times
    before deactivating.
    """
    pass
