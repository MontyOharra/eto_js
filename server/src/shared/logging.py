"""
Logging utilities with custom levels and configuration.

Custom log levels:
- TRACE (5): Very detailed tracing, below DEBUG
- MONITOR (7): Monitoring loops, between TRACE and DEBUG

Usage:
    from shared.logging import configure_logging, get_logger

    # At app startup:
    configure_logging()

    # In modules:
    logger = get_logger(__name__)
    logger.trace("Very detailed trace message")
    logger.monitor("Monitoring loop message")
    logger.debug("Standard debug message")
"""
import logging
from logging.handlers import RotatingFileHandler
import os
import sys
from typing import Any


# =============================================================================
# Custom Log Levels
# =============================================================================

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
    logging.addLevelName(TRACE, "TRACE")
    logging.addLevelName(MONITOR, "MONITOR")
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


# =============================================================================
# Log Configuration
# =============================================================================

def get_log_level() -> int:
    """Get logging level from environment variable."""
    log_level = os.getenv("LOG_LEVEL", "INFO").upper()
    level_mapping = {
        "DEBUG": logging.DEBUG,
        "INFO": logging.INFO,
        "WARNING": logging.WARNING,
        "ERROR": logging.ERROR,
        "CRITICAL": logging.CRITICAL,
        "TRACE": TRACE,
        "MONITOR": MONITOR,
    }
    return level_mapping.get(log_level, logging.INFO)


class ColoredFormatter(logging.Formatter):
    """Custom formatter with color support for different log levels and automatic traceback inclusion."""

    COLORS = {
        "TRACE": "\033[37m",      # Light gray
        "MONITOR": "\033[90m",    # Dark gray
        "DEBUG": "\033[90m",      # Gray
        "INFO": "\033[94m",       # Blue
        "WARNING": "\033[93m",    # Yellow
        "ERROR": "\033[91m",      # Red
        "CRITICAL": "\033[91m",   # Red
        "RESET": "\033[0m",       # Reset
    }

    def __init__(
        self,
        fmt: str | None = None,
        datefmt: str | None = None,
        use_colors: bool = True,
        include_traceback_on_error: bool = True,
    ):
        super().__init__(fmt, datefmt)
        self.use_colors = use_colors
        self.include_traceback_on_error = include_traceback_on_error

    def format(self, record: logging.LogRecord) -> str:
        # Automatically add exc_info for ERROR and CRITICAL levels if an exception is present
        if self.include_traceback_on_error and record.levelno >= logging.ERROR:
            if not record.exc_info and hasattr(record, "exc_text") and record.exc_text is None:
                if sys.exc_info()[0] is not None:
                    record.exc_info = sys.exc_info()

        if self.use_colors:
            color = self.COLORS.get(record.levelname, self.COLORS["RESET"])
            reset = self.COLORS["RESET"]

            formatted = super().format(record)

            # Check if the formatted message contains the separator between header and content
            if ":\n    " in formatted:
                header, content = formatted.split(":\n    ", 1)
                return f"{color}{header}{reset}:\n    {content}"
            else:
                return f"{color}{formatted}{reset}"
        else:
            return super().format(record)


# Third-party loggers to reduce noise from
THIRD_PARTY_LOGGERS = [
    "pdfminer",
    "pdfminer.cmapdb",
    "pdfminer.pdfparser",
    "pdfminer.pdfdocument",
    "pdfminer.pdfinterp",
    "pdfminer.converter",
    "pdfminer.layout",
    "urllib3",
    "requests",
    "matplotlib",
    "PIL",
]


def configure_logging() -> None:
    """
    Configure comprehensive logging for the application.

    Reads configuration from environment variables:
    - LOG_LEVEL: Logging level (default: INFO)
    - LOG_FORMAT: Log message format
    - LOG_DATE_FORMAT: Date format (default: %Y-%m-%d %H:%M:%S)
    - LOG_COLORS: Enable console colors (default: true)
    - LOG_TRACEBACKS: Include tracebacks on errors (default: true)
    - LOGS_DIR: Directory for log files (default: logs)
    - LOG_MAX_BYTES: Max log file size before rotation (default: 10485760 = 10 MB)
    - LOG_BACKUP_COUNT: Number of backup files to keep (default: 5)
    - THIRD_PARTY_LOG_LEVEL: Log level for third-party libraries (default: WARNING)

    Should be called once at application startup.
    """
    # Initialize custom log levels first
    setup_logger_class()

    # Get logging configuration from environment
    log_level = get_log_level()
    log_format = os.getenv(
        "LOG_FORMAT",
        "\n%(asctime)s | %(levelname)s | %(name)s - line %(lineno)s:\n    %(message)s\n",
    )
    date_format = os.getenv("LOG_DATE_FORMAT", "%Y-%m-%d %H:%M:%S")
    use_colors = os.getenv("LOG_COLORS", "true").lower() == "true"
    include_traceback = os.getenv("LOG_TRACEBACKS", "true").lower() == "true"

    # Create logs directory if it doesn't exist
    logs_dir = os.getenv("LOGS_DIR", "logs")
    os.makedirs(logs_dir, exist_ok=True)

    # Configure root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(log_level)

    # Remove existing handlers to avoid duplicates
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)

    # Console handler with colors
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(log_level)
    console_formatter = ColoredFormatter(
        fmt=log_format,
        datefmt=date_format,
        use_colors=use_colors,
        include_traceback_on_error=include_traceback,
    )
    console_handler.setFormatter(console_formatter)
    root_logger.addHandler(console_handler)

    # File handler with rotation (always without colors, but with tracebacks)
    # Rotates when file reaches max size, keeps backup_count old files
    log_file = os.path.join(logs_dir, "app.log")
    max_bytes = int(os.getenv("LOG_MAX_BYTES", 10 * 1024 * 1024))  # 10 MB default
    backup_count = int(os.getenv("LOG_BACKUP_COUNT", 5))  # 5 backups default
    file_handler = RotatingFileHandler(
        log_file,
        maxBytes=max_bytes,
        backupCount=backup_count,
        encoding="utf-8"
    )
    file_handler.setLevel(log_level)
    file_formatter = ColoredFormatter(
        fmt=log_format,
        datefmt=date_format,
        use_colors=False,
        include_traceback_on_error=include_traceback,
    )
    file_handler.setFormatter(file_formatter)
    root_logger.addHandler(file_handler)

    # Reduce noise from external libraries
    logging.getLogger("urllib3").setLevel(logging.WARNING)
    logging.getLogger("requests").setLevel(logging.WARNING)
    logging.getLogger("uvicorn").setLevel(logging.INFO)
    logging.getLogger("uvicorn.access").setLevel(logging.INFO)
    logging.getLogger("fastapi").setLevel(logging.INFO)

    third_party_level = os.getenv("THIRD_PARTY_LOG_LEVEL", "WARNING").upper()
    third_party_log_level = logging.getLevelName(third_party_level)
    if isinstance(third_party_log_level, int):
        for logger_name in THIRD_PARTY_LOGGERS:
            logging.getLogger(logger_name).setLevel(third_party_log_level)

    # Log configuration summary
    logger = get_logger(__name__)
    logger.info(
        f"Logging configured: level={logging.getLevelName(log_level)}, "
        f"file={log_file}, max_size={max_bytes // 1024 // 1024}MB, backups={backup_count}"
    )
