"""
Transformation Pipeline Server - FastAPI Application
Node-based pipeline system with Dask execution
"""
import os
import logging
import sys
from contextlib import asynccontextmanager
from typing import Optional, Dict, Any

from fastapi import FastAPI, HTTPException, Request, status
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.exceptions import RequestValidationError, HTTPException as FastAPIHTTPException
from pydantic import ValidationError
import uvicorn

logger = logging.getLogger(__name__)

# Global variables to store initialized services and database connection
_connection_manager = None
_service_container = None


class DatabaseConnectionError(Exception):
    """Raised when database connection cannot be established"""
    pass


class ServiceInitializationError(Exception):
    """Raised when services cannot be initialized"""
    pass


def get_log_level() -> int:
    """Get logging level from environment variable"""
    log_level = os.getenv('LOG_LEVEL', 'INFO').upper()
    level_mapping = {
        'DEBUG': logging.DEBUG,
        'INFO': logging.INFO,
        'WARNING': logging.WARNING,
        'ERROR': logging.ERROR,
        'CRITICAL': logging.CRITICAL,
        'TRACE': 5,  # Custom level below DEBUG for very verbose tracing
        'MONITOR': 7  # Custom level for monitoring loops (between TRACE and DEBUG)
    }
    return level_mapping.get(log_level, logging.INFO)


def setup_custom_log_levels():
    """Setup custom logging levels"""
    # Add TRACE level (5) - for very detailed tracing
    logging.addLevelName(5, 'TRACE')
    def trace(self, message, *args, **kwargs):
        if self.isEnabledFor(5):
            self._log(5, message, args, **kwargs)
    logging.Logger.trace = trace

    # Add MONITOR level (7) - for monitoring loops
    logging.addLevelName(7, 'MONITOR')
    def monitor(self, message, *args, **kwargs):
        if self.isEnabledFor(7):
            self._log(7, message, args, **kwargs)
    logging.Logger.monitor = monitor


class ColoredFormatter(logging.Formatter):
    """Custom formatter with color support for different log levels"""

    # ANSI color codes
    COLORS = {
        'TRACE': '\033[37m',      # Light gray
        'MONITOR': '\033[90m',    # Dark gray
        'DEBUG': '\033[90m',      # Gray
        'INFO': '\033[94m',       # Blue
        'WARNING': '\033[93m',    # Yellow
        'ERROR': '\033[91m',      # Red
        'CRITICAL': '\033[91m',   # Red
        'RESET': '\033[0m'        # Reset
    }

    def __init__(self, fmt=None, datefmt=None, use_colors=True):
        super().__init__(fmt, datefmt)
        self.use_colors = use_colors

    def format(self, record):
        if self.use_colors:
            # Get color for this log level
            color = self.COLORS.get(record.levelname, self.COLORS['RESET'])
            reset = self.COLORS['RESET']

            # Format the message normally first
            formatted = super().format(record)

            # Check if the formatted message contains the separator between header and content
            if ':\n    ' in formatted:
                # Split at the separator to color only the header
                header, content = formatted.split(':\n    ', 1)
                return f"{color}{header}{reset}:\n    {content}"
            else:
                # If no separator, color the entire message (for simple logs)
                return f"{color}{formatted}{reset}"
        else:
            return super().format(record)


def configure_logging():
    """Configure comprehensive logging for the application"""
    setup_custom_log_levels()

    # Get logging configuration from environment
    log_level = get_log_level()
    log_format = os.getenv('LOG_FORMAT',
        '%(asctime)s | %(levelname)-8s | %(name)s:\n    %(message)s'
    )
    date_format = os.getenv('LOG_DATE_FORMAT', '%Y-%m-%d %H:%M:%S')
    use_colors = os.getenv('LOG_COLORS', 'true').lower() == 'true'

    # Create logs directory if it doesn't exist
    logs_dir = os.getenv('LOGS_DIR', 'logs')
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
        use_colors=use_colors
    )
    console_handler.setFormatter(console_formatter)
    root_logger.addHandler(console_handler)

    # File handler (always without colors)
    log_file = os.path.join(logs_dir, 'transformation_pipeline.log')
    file_handler = logging.FileHandler(log_file, encoding='utf-8')
    file_handler.setLevel(log_level)
    file_formatter = logging.Formatter(
        fmt=log_format,
        datefmt=date_format
    )
    file_handler.setFormatter(file_formatter)
    root_logger.addHandler(file_handler)

    # Reduce noise from external libraries
    logging.getLogger('urllib3').setLevel(logging.WARNING)
    logging.getLogger('requests').setLevel(logging.WARNING)
    logging.getLogger('uvicorn').setLevel(logging.INFO)
    logging.getLogger('uvicorn.access').setLevel(logging.INFO)
    logging.getLogger('fastapi').setLevel(logging.INFO)

    logger.info("Logging configured successfully")
    logger.info(f"Log level: {logging.getLevelName(log_level)}")
    logger.info(f"Console colors: {use_colors}")
    logger.info(f"Log file: {log_file}")


async def initialize_database_connection() -> None:
    """Initialize database connection and verify connectivity"""
    global _connection_manager

    try:
        database_url = os.getenv('DATABASE_URL')
        if not database_url:
            raise DatabaseConnectionError("DATABASE_URL environment variable is required")

        # Import database initialization (when you implement it)
        from .shared.database import init_database_connection
        _connection_manager = init_database_connection(database_url)

        # For now, just log that we would initialize the database
        logger.info(f"Would initialize database connection with URL: {database_url[:20]}...")
        logger.info("Database connection established and verified")

    except Exception as e:
        logger.error(f"Failed to initialize database: {e}")

        # Print available drivers for debugging
        try:
            import pyodbc
            drivers = pyodbc.drivers()
            logger.debug(f"Available ODBC drivers: {drivers}")
        except ImportError:
            logger.warning("pyodbc not available for driver debugging")
        except Exception:
            pass

        # Re-raise to prevent app startup with broken database
        raise DatabaseConnectionError(f"Database initialization failed: {e}")


async def initialize_services() -> None:
    """Initialize all services using the ServiceContainer singleton"""
    global _connection_manager, _service_container

    try:
        logger.debug("Initializing services via ServiceContainer...")

        # Initialize the service container with all services
        logger.info("Creating ServiceContainer singleton instance...")

        # Import service container
        from .shared.services.service_container import ServiceContainer

        # Create service container instance
        _service_container = ServiceContainer()
        logger.info(f"ServiceContainer instance created (ID: {id(_service_container)}), calling initialize")
        _service_container.initialize(_connection_manager)
        logger.info("ServiceContainer.initialize() completed successfully")

        logger.info("All services initialized successfully via ServiceContainer")

        # Auto-register default modules
        try:
            modules_service = _service_container.get_modules_service()
            # Register any additional modules here if needed
            logger.info("Modules service initialized and default modules registered")
        except Exception as service_error:
            logger.warning(f"Module service initialization warning: {service_error}")

    except Exception as e:
        logger.error(f"Failed to initialize services: {e}")
        # Don't re-raise - allow app to continue with limited functionality
        logger.info("Application will continue with limited functionality")


async def cleanup_services() -> None:
    """Cleanup services and database connections on shutdown"""
    global _service_container, _connection_manager

    try:
        if _service_container:
            logger.info("Stopping services...")
            # Any service-specific cleanup can go here

        if _connection_manager:
            logger.info("Cleaning up database connections...")
            # Add database connection cleanup when implemented
            # _connection_manager.close()

    except Exception as e:
        logger.error(f"Error during cleanup: {e}")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """FastAPI lifespan event handler for startup and shutdown"""
    # Startup
    # Configure logging first so we can see startup logs
    configure_logging()
    logger.info("Starting Transformation Pipeline Server...")

    try:
        await initialize_database_connection()
        await initialize_services()
        logger.info("Application startup completed successfully")
    except Exception as e:
        logger.error(f"Application startup failed: {e}")
        raise

    yield

    # Shutdown
    logger.info("Shutting down Transformation Pipeline Server...")
    await cleanup_services()
    logger.info("Application shutdown completed")


# Exception handlers
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """Handle Pydantic validation errors"""
    logger.warning(f"Validation error on {request.method} {request.url}: {exc}")
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={
            "error": "Validation Error",
            "detail": exc.errors(),
            "message": "Invalid request data"
        }
    )


async def http_exception_handler(request: Request, exc: FastAPIHTTPException):
    """Handle HTTP exceptions"""
    logger.warning(f"HTTP {exc.status_code} on {request.method} {request.url}: {exc.detail}")
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": "HTTP Error",
            "detail": exc.detail,
            "status_code": exc.status_code
        }
    )


async def general_exception_handler(request: Request, exc: Exception):
    """Handle unexpected exceptions"""
    logger.error(f"Unexpected error on {request.method} {request.url}: {exc}", exc_info=True)
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "error": "Internal Server Error",
            "detail": "An unexpected error occurred",
            "message": str(exc) if os.getenv('DEBUG', 'false').lower() == 'true' else "Internal server error"
        }
    )


def create_app() -> FastAPI:
    """Create and configure the FastAPI application"""
    # Note: Logging is now configured in lifespan startup

    # Create FastAPI app with lifespan
    app = FastAPI(
        title="Transformation Pipeline Server",
        description="Node-based transformation pipeline system with Dask execution",
        version="1.0.0",
        docs_url="/docs",
        redoc_url="/redoc",
        lifespan=lifespan
    )

    # Add exception handlers
    app.add_exception_handler(RequestValidationError, validation_exception_handler)
    app.add_exception_handler(FastAPIHTTPException, http_exception_handler)
    app.add_exception_handler(Exception, general_exception_handler)

    # Configure CORS
    app.add_middleware(
        CORSMiddleware,
        allow_origins=os.getenv("CORS_ORIGINS", "http://localhost:3000,http://localhost:5173,http://localhost:5002").split(","),
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Import and register routers
    from .api.routers.health import router as health_router
    from .api.routers.modules import router as modules_router
    from .api.routers.pipelines import router as pipelines_router

    app.include_router(health_router, prefix="/api", tags=["health"])
    app.include_router(modules_router, prefix="/api", tags=["modules"])
    app.include_router(pipelines_router, prefix="/api", tags=["pipelines"])

    logger.info("FastAPI application created and configured")

    return app


# This is used when running with uvicorn directly (not via main.py)
if __name__ == "__main__":
    app = create_app()
    uvicorn.run(app, host="0.0.0.0", port=8090)