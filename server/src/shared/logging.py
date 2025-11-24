"""
Custom logging utilities with TRACE and MONITOR levels.

Usage:
    from shared.logging import get_logger
    logger = get_logger(__name__)

    logger.trace("Very detailed trace message")
    logger.monitor("Monitoring loop message")
    logger.debug("Standard debug message")
"""
import logging
from typing import Any

# Custom log levels
TRACE = 5
MONITOR = 7


class MonitorLogger(logging.Logger):
    """
    Extended Logger class with trace() and monitor() methods.

    This class is set as the default logger class so that all
    logging.getLogger() calls return instances with these methods.
    """

    def trace(self, msg: str, *args: Any, **kwargs: Any) -> None:
        """
        Log at TRACE level (5) - for very detailed tracing.
        Below DEBUG level, used for verbose diagnostic output.
        """
        if self.isEnabledFor(TRACE):
            self._log(TRACE, msg, args, **kwargs)

    def monitor(self, msg: str, *args: Any, **kwargs: Any) -> None:
        """
        Log at MONITOR level (7) - for monitoring loops.
        Between TRACE and DEBUG, used for periodic status messages
        that would be too verbose at DEBUG but useful for monitoring.
        """
        if self.isEnabledFor(MONITOR):
            self._log(MONITOR, msg, args, **kwargs)


def setup_logger_class() -> None:
    """
    Configure the logging module to use MonitorLogger as the default logger class.
    Also registers the custom level names.

    This should be called once at application startup, before any loggers are created.
    """
    # Register custom level names
    logging.addLevelName(TRACE, 'TRACE')
    logging.addLevelName(MONITOR, 'MONITOR')

    # Set our custom logger class as the default
    logging.setLoggerClass(MonitorLogger)


def get_logger(name: str) -> MonitorLogger:
    """
    Get a logger instance with trace() and monitor() methods.

    This is a typed wrapper around logging.getLogger() that returns
    the correct type for static analysis.

    Args:
        name: Logger name (typically __name__)

    Returns:
        MonitorLogger instance
    """
    return logging.getLogger(name)  # type: ignore[return-value]
