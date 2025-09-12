"""
Global logging helper utilities
Provides consistent error logging with tracebacks across the application
"""
import logging
import functools
from typing import Callable, Any, Optional


def log_exceptions(logger_name: Optional[str] = None):
    """
    Decorator to automatically log exceptions with full tracebacks.
    
    Usage:
    @log_exceptions()
    def my_function():
        # If this raises an exception, it will be logged with traceback
        pass
        
    @log_exceptions("custom.logger")  
    def my_function():
        # Uses custom logger name
        pass
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            # Get logger - use provided name, or infer from module
            if logger_name:
                logger = logging.getLogger(logger_name)
            else:
                logger = logging.getLogger(func.__module__)
            
            try:
                return func(*args, **kwargs)
            except Exception as e:
                logger.exception(f"Exception in {func.__name__}: {e}")
                raise  # Re-raise the exception
        return wrapper
    return decorator


def handle_service_exception(logger: logging.Logger, operation: str, exception: Exception) -> dict:
    """
    Standard exception handler for service methods.
    Logs the exception and returns a consistent error response.
    
    Args:
        logger: The logger instance to use
        operation: Description of the operation that failed (e.g., "creating configuration")
        exception: The caught exception
        
    Returns:
        Dict with success=False, error, and message fields
    """
    logger.exception(f"Error {operation}: {exception}")
    return {
        "success": False,
        "error": str(exception),
        "message": f"Failed {operation}"
    }


class LoggingMixin:
    """
    Mixin class that provides logging utilities to any class.
    
    Usage:
    class MyService(LoggingMixin):
        def __init__(self):
            self.setup_logging(__name__)  # Sets up self.logger
            
        def my_method(self):
            try:
                # ... do work
                pass
            except Exception as e:
                return self.handle_exception("processing data", e)
    """
    
    def setup_logging(self, name: str):
        """Set up the logger for this class"""
        self.logger = logging.getLogger(name)
    
    def handle_exception(self, operation: str, exception: Exception) -> dict:
        """Handle an exception with consistent logging and return format"""
        return handle_service_exception(self.logger, operation, exception)


# Global exception handler for Flask routes
def handle_api_exception(logger: logging.Logger, operation: str, exception: Exception, status_code: int = 500) -> tuple:
    """
    Handle exceptions in API routes with consistent logging and response format.
    
    Args:
        logger: Logger instance
        operation: Description of the failed operation  
        exception: The caught exception
        status_code: HTTP status code to return
        
    Returns:
        Tuple of (response_dict, status_code) for Flask jsonify
    """
    logger.exception(f"API error during {operation}: {exception}")
    
    response = {
        "success": False,
        "error": str(exception),
        "message": f"Failed to {operation}"
    }
    
    return response, status_code