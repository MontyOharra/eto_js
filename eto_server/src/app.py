"""
Unified ETO Server - FastAPI Application
Feature-based architecture with clean separation of concerns
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

from .shared.database import init_database_connection
from .shared.utils.storage_config import get_storage_configuration
from .shared.services.service_container import ServiceContainer

# Add the src directory to Python path to enable absolute imports
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

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

            # Split on the message part (after the colon and newline)
            # Format: \n%(asctime)s - %(levelname)s - %(name)s:\n    %(message)s\n
            if ':\n    ' in formatted:
                header_part, message_part = formatted.split(':\n    ', 1)
                # Color only the header part, keep message uncolored
                return f"{color}{header_part}:{reset}\n    {message_part}"
            else:
                # Fallback if format doesn't match expected pattern
                return formatted
        else:
            return super().format(record)


def configure_logging():
    """Configure logging to work alongside Uvicorn - Environment configurable"""
    # Setup custom log levels first
    setup_custom_log_levels()

    # Get log level from environment
    log_level = get_log_level()

    # Get the root logger
    root_logger = logging.getLogger()

    # Create console handler with custom format
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(log_level)

    # Create formatter - configurable format and colors
    log_format = os.getenv('LOG_FORMAT', '\n%(asctime)s | %(levelname)s | %(name)s - line %(lineno)s:\n    %(message)s\n')
    use_colors = os.getenv('LOG_COLORS', 'true').lower() == 'true'
    formatter = ColoredFormatter(log_format, use_colors=use_colors)
    console_handler.setFormatter(formatter)

    # Add console handler to root logger if not already present
    if not any(isinstance(handler, logging.StreamHandler) for handler in root_logger.handlers):
        root_logger.addHandler(console_handler)

    # Add file logging if enabled
    enable_file_logging = os.getenv('LOG_TO_FILE', 'true').lower() == 'true'
    if enable_file_logging:
        # Create logs directory if it doesn't exist
        logs_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'logs')
        os.makedirs(logs_dir, exist_ok=True)

        # Create rotating file handler
        from logging.handlers import RotatingFileHandler
        log_file = os.path.join(logs_dir, 'eto_server.log')
        file_handler = RotatingFileHandler(
            log_file,
            maxBytes=10*1024*1024,  # 10MB
            backupCount=5,
            encoding='utf-8'
        )
        file_handler.setLevel(log_level)

        # Use plain formatter for file (no colors)
        file_formatter = logging.Formatter(log_format)
        file_handler.setFormatter(file_formatter)

        # Add file handler if not already present
        if not any(isinstance(handler, RotatingFileHandler) for handler in root_logger.handlers):
            root_logger.addHandler(file_handler)

    # Set root logger level from environment
    root_logger.setLevel(log_level)

    # Configure application loggers to inherit from root (no hardcoded levels)
    # This allows the LOG_LEVEL env var to control everything
    app_loggers = ['shared', 'features', 'api', 'src']
    for logger_name in app_loggers:
        app_logger = logging.getLogger(logger_name)
        app_logger.propagate = True  # Inherit from root logger
        # Don't set explicit levels - let them inherit from root

    # Configure external library loggers based on environment
    uvicorn_level = os.getenv('UVICORN_LOG_LEVEL', 'WARNING').upper()
    uvicorn_log_level = logging.getLevelName(uvicorn_level)
    if isinstance(uvicorn_log_level, int):
        logging.getLogger("uvicorn.access").setLevel(uvicorn_log_level)

    # Suppress noisy third-party library debug logs
    third_party_loggers = [
        'pdfminer',
        'pdfminer.cmapdb',
        'pdfminer.pdfparser',
        'pdfminer.pdfdocument',
        'pdfminer.pdfinterp',
        'pdfminer.converter',
        'pdfminer.layout',
        'urllib3',
        'requests',
        'matplotlib',
        'PIL'
    ]

    third_party_level = os.getenv('THIRD_PARTY_LOG_LEVEL', 'WARNING').upper()
    third_party_log_level = logging.getLevelName(third_party_level)
    if isinstance(third_party_log_level, int):
        for logger_name in third_party_loggers:
            logging.getLogger(logger_name).setLevel(third_party_log_level)

    logger.info(f"Logging configured: LOG_LEVEL={logging.getLevelName(log_level)}, COLORS={use_colors}, FILE_LOGGING={enable_file_logging}")
    if enable_file_logging:
        logger.info(f"Log file: {log_file}")
    logger.info(f"Uvicorn access log level: {uvicorn_level}")
    logger.info(f"Third-party library log level: {third_party_level} (suppresses pdfminer, urllib3, etc.)")


async def initialize_database_connection() -> None:
    """Initialize database connection and verify connectivity"""
    global _connection_manager

    try:
        database_url = os.getenv('DATABASE_URL')
        if not database_url:
            raise DatabaseConnectionError("DATABASE_URL environment variable is required")

        # Initialize database connection
        _connection_manager = init_database_connection(database_url)

        # Test connection
        if _connection_manager.test_connection():
            logger.info("Database connection established and verified")
        else:
            logger.warning("Database connection established but test failed")

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

        if not _connection_manager:
            raise ServiceInitializationError("Database connection manager not available")

        # Get PDF storage path from environment/config
        pdf_storage_path = get_storage_configuration()
        logger.debug(f"PDF storage path configured: {pdf_storage_path}")

        # Initialize the service container with all services
        logger.info("Creating ServiceContainer singleton instance...")

        # Create service container instance
        _service_container = ServiceContainer()
        logger.info(f"ServiceContainer instance created (ID: {id(_service_container)}), calling initialize with cm={type(_connection_manager)}")
        _service_container.initialize(_connection_manager, pdf_storage_path)
        logger.info("ServiceContainer.initialize() completed successfully")

        logger.info("All services initialized successfully via ServiceContainer")

        # Auto-start email ingestion with startup recovery
        try:
            email_ingestion_service = _service_container.get_email_ingestion_service()
            # Startup recovery will resume all active configurations
            email_ingestion_service.startup_recovery()
            logger.info("Email ingestion service startup recovery completed")
        except Exception as service_error:
            logger.warning(f"Email ingestion startup recovery failed: {service_error}")

        # Auto-start ETO processing if enabled
        try:
            worker_enabled = os.getenv('ETO_WORKER_ENABLED', 'true').lower() == 'true'
            if worker_enabled:
                eto_service = _service_container.get_eto_service()
                # Start the worker automatically
                worker_started = await eto_service.start_worker()
                if worker_started:
                    logger.info("ETO processing worker started automatically")
                else:
                    logger.warning("ETO processing worker failed to start automatically")
            else:
                logger.info("ETO processing service initialized but worker disabled (ETO_WORKER_ENABLED=false)")
        except Exception as eto_error:
            logger.exception(f"ETO processing service initialization failed: {eto_error}")

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
            # Stop ETO processing service if running
            try:
                eto_service = _service_container.get_eto_service()
                if hasattr(eto_service, 'stop_worker'):
                    worker_stopped = await eto_service.stop_worker(graceful=True)
                    if worker_stopped:
                        logger.info("ETO processing worker stopped gracefully")
                    else:
                        logger.info("ETO processing worker was not running")
                else:
                    logger.info("ETO processing service stopped")
            except Exception as e:
                logger.warning(f"Failed to stop ETO service: {e}")
            
            # Stop email ingestion service if running
            try:
                email_ingestion_service = _service_container.get_email_ingestion_service()
                if hasattr(email_ingestion_service, 'shutdown'):
                    email_ingestion_service.shutdown()
                    logger.info("Email ingestion service stopped")
            except Exception as e:
                logger.warning(f"Failed to stop email ingestion service: {e}")

        if _connection_manager:
            logger.info("Cleaning up database connections...")
            # Add database connection cleanup if needed

    except Exception as e:
        logger.error(f"Error during cleanup: {e}")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """FastAPI lifespan context manager for startup and shutdown"""
    # Startup
    # Configure logging first so we can see startup logs
    configure_logging()
    logger.info("Starting Unified ETO Server (FastAPI)...")
    try:
        await initialize_database_connection()
        await initialize_services()
        logger.info("Application startup completed successfully")
    except Exception as e:
        logger.error(f"Application startup failed: {e}")
        raise

    yield

    # Shutdown
    logger.info("Shutting down Unified ETO Server...")
    await cleanup_services()
    logger.info("Application shutdown completed")


def setup_cors_middleware(app: FastAPI) -> None:
    """Setup CORS middleware for FastAPI"""
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],  # Allow all origins for development
        allow_credentials=False,
        allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS", "HEAD", "PATCH"],
        allow_headers=["Content-Type", "Authorization", "X-Requested-With", "Accept", "Origin"],
        expose_headers=["Content-Range", "X-Content-Range"],
        max_age=86400
    )


def setup_exception_handlers(app: FastAPI) -> None:
    """Setup global exception handlers for consistent error responses"""

    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(request: Request, exc: RequestValidationError):
        """Handle Pydantic validation errors"""
        return JSONResponse(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            content={
                "success": False,
                "error": "Validation error",
                "message": "The request data failed validation",
                "details": exc.errors(),
                "status_code": 422
            }
        )

    @app.exception_handler(FastAPIHTTPException)
    async def http_exception_handler(request: Request, exc: FastAPIHTTPException):
        """Handle HTTP exceptions with consistent JSON response"""
        return JSONResponse(
            status_code=exc.status_code,
            content={
                "success": False,
                "error": exc.detail,
                "message": exc.detail,
                "status_code": exc.status_code
            }
        )

    @app.exception_handler(404)
    async def not_found_handler(request: Request, exc):
        """Handle 404 errors with consistent JSON response"""
        return JSONResponse(
            status_code=status.HTTP_404_NOT_FOUND,
            content={
                "success": False,
                "error": "Resource not found",
                "message": "The requested resource does not exist",
                "status_code": 404
            }
        )

    @app.exception_handler(500)
    async def internal_server_error_handler(request: Request, exc):
        """Handle 500 errors with consistent JSON response"""
        logger.error(f"Internal server error: {exc}")
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={
                "success": False,
                "error": "Internal server error",
                "message": "An unexpected error occurred on the server",
                "status_code": 500
            }
        )

    @app.exception_handler(405)
    async def method_not_allowed_handler(request: Request, exc):
        """Handle 405 errors with consistent JSON response"""
        return JSONResponse(
            status_code=status.HTTP_405_METHOD_NOT_ALLOWED,
            content={
                "success": False,
                "error": "Method not allowed",
                "message": "The HTTP method is not allowed for this endpoint",
                "status_code": 405
            }
        )


def register_routers(app: FastAPI) -> None:
    """Register FastAPI routers"""
    # Register health router first
    try:
        from .api.routers import health_router
        app.include_router(health_router, prefix="/api")
        logger.info("Registered health router")
    except ImportError as e:
        logger.warning(f"Could not import health router: {e}")
    except Exception as e:
        logger.error(f"Error registering health router: {e}")

    # Register PDF templates router
    try:
        from .api.routers import pdf_templates_router
        app.include_router(pdf_templates_router, prefix="/api")
        logger.info("Registered PDF templates router")
    except ImportError as e:
        logger.warning(f"Could not import PDF templates router: {e}")
    except Exception as e:
        logger.error(f"Error registering PDF templates router: {e}")

    # Register email configs router
    try:
        from .api.routers import email_configs_router
        app.include_router(email_configs_router, prefix="/api")
        logger.info("Registered email configs router")
    except ImportError as e:
        logger.warning(f"Could not import email configs router: {e}")
    except Exception as e:
        logger.error(f"Error registering email configs router: {e}")

    # Register ETO processing router
    try:
        from .api.routers import eto_router
        app.include_router(eto_router, prefix="/api")
        logger.info("Registered ETO processing router")
    except ImportError as e:
        logger.warning(f"Could not import ETO processing router: {e}")
    except Exception as e:
        logger.error(f"Error registering ETO processing router: {e}")


def register_info_endpoint(app: FastAPI) -> None:
    """Register application info endpoint"""

    @app.get("/", tags=["info"])
    async def app_info() -> Dict[str, Any]:
        """Application information endpoint"""
        return {
            "service": "Unified ETO Server",
            "description": "Email-to-Order processing system with feature-based architecture",
            "version": "2.0.0",
            "architecture": "feature-based",
            "framework": "FastAPI",
            "api_prefix": "/api",
            "endpoints": {
                "health": "/api/health",
                "email_configuration": "/api/email-configs",
                "eto_processing": "/api/eto-runs",
                "eto_worker": "/api/eto-runs/worker",
                "pdf_templates": "/api/pdf_templates"
            },
            "documentation": {
                "health": "Service health and status monitoring",
                "email_configuration": "Email ingestion configuration management",
                "eto_processing": "ETO processing run management and background processing",
                "eto_worker": "Background worker management (start/stop/pause/resume)",
                "pdf_templates": "PDF template creation and versioning"
            },
            "interactive_docs": "/docs",
            "openapi_schema": "/openapi.json"
        }


def get_service_container() -> ServiceContainer:
    """Dependency function to get the service container"""
    global _service_container
    if not _service_container:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Service container not initialized"
        )
    return _service_container


def create_app() -> FastAPI:
    """
    FastAPI application factory with feature-based architecture
    Creates and configures the FastAPI app with all services
    """
    # Create FastAPI app with lifespan management
    app = FastAPI(
        title="Unified ETO Server",
        description="Email-to-Order processing system with feature-based architecture",
        version="2.0.0",
        lifespan=lifespan,
        docs_url="/docs",
        redoc_url="/redoc",
        openapi_url="/openapi.json"
    )

    # Setup middleware and error handlers
    setup_cors_middleware(app)
    setup_exception_handlers(app)

    # Register routes and info endpoint
    register_routers(app)
    register_info_endpoint(app)

    logger.info("Unified ETO Server (FastAPI) application created successfully")
    return app


def run_server():
    """Run the FastAPI server with uvicorn"""
    # Get configuration from environment
    port = int(os.getenv('PORT', 8080))
    host = os.getenv('HOST', '0.0.0.0')
    debug = os.getenv('DEBUG', 'false').lower() == 'true'

    logger.info(f"Starting FastAPI server on {host}:{port}")

    if debug:
        logger.warning("Running in DEBUG mode - not suitable for production!")

    # Run with uvicorn
    if debug:
        # In debug mode, configure reload to only watch src/ directory
        uvicorn.run(
            "app-fastapi:create_app",
            factory=True,
            host=host,
            port=port,
            reload=True,
            reload_dirs=["./src"],  # Only watch src directory
            reload_excludes=["./storage", "./logs", "./data"],  # Exclude storage/logs/data directories
            log_level="debug",
            access_log=True
        )
    else:
        # Production mode - no reload
        uvicorn.run(
            "app-fastapi:create_app",
            factory=True,
            host=host,
            port=port,
            reload=False,
            log_level="info",
            access_log=True
        )


if __name__ == "__main__":
    run_server()