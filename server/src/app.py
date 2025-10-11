"""
Transformation Pipeline Server - FastAPI Application
Node-based pipeline system with Dask execution
"""
import os
import logging
import sys
from typing import Dict, Any

# Add src directory to path BEFORE any local imports
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from contextlib import asynccontextmanager

from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.exceptions import RequestValidationError, HTTPException as FastAPIHTTPException
import uvicorn

from shared.database import init_database_connection
from shared.services.service_container import ServiceContainer
from shared.utils.storage_config import get_storage_configuration

logger = logging.getLogger(__name__)

# Global variables to store initialized database connection
_connection_manager = None


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
    setattr(logging.Logger, 'trace', trace)  # Use setattr to avoid type checker warnings

    # Add MONITOR level (7) - for monitoring loops
    logging.addLevelName(7, 'MONITOR')
    def monitor(self, message, *args, **kwargs):
        if self.isEnabledFor(7):
            self._log(7, message, args, **kwargs)
    setattr(logging.Logger, 'monitor', monitor)  # Use setattr to avoid type checker warnings


class ColoredFormatter(logging.Formatter):
    """Custom formatter with color support for different log levels and automatic traceback inclusion"""

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

    def __init__(self, fmt=None, datefmt=None, use_colors=True, include_traceback_on_error=True):
        super().__init__(fmt, datefmt)
        self.use_colors = use_colors
        self.include_traceback_on_error = include_traceback_on_error

    def format(self, record):
        # Automatically add exc_info for ERROR and CRITICAL levels if an exception is present
        if self.include_traceback_on_error and record.levelno >= logging.ERROR:
            # Check if there's an exception available but exc_info wasn't explicitly set
            if not record.exc_info and hasattr(record, 'exc_text') and record.exc_text is None:
                # Try to get the current exception from sys
                import sys
                if sys.exc_info()[0] is not None:
                    record.exc_info = sys.exc_info()

        if self.use_colors:
            # Get color for this log level
            color = self.COLORS.get(record.levelname, self.COLORS['RESET'])
            reset = self.COLORS['RESET']

            # Format the message normally first (this will include traceback if exc_info is set)
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
         '\n%(asctime)s | %(levelname)s | %(name)s - line %(lineno)s:\n    %(message)s\n'
    )
    date_format = os.getenv('LOG_DATE_FORMAT', '%Y-%m-%d %H:%M:%S')
    use_colors = os.getenv('LOG_COLORS', 'true').lower() == 'true'
    include_traceback = os.getenv('LOG_TRACEBACKS', 'true').lower() == 'true'

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
        use_colors=use_colors,
        include_traceback_on_error=include_traceback
    )
    console_handler.setFormatter(console_formatter)
    root_logger.addHandler(console_handler)

    # File handler (always without colors, but with tracebacks)
    log_file = os.path.join(logs_dir, 'transformation_pipeline.log')
    file_handler = logging.FileHandler(log_file, encoding='utf-8')
    file_handler.setLevel(log_level)
    file_formatter = ColoredFormatter(
        fmt=log_format,
        datefmt=date_format,
        use_colors=False,
        include_traceback_on_error=include_traceback
    )
    file_handler.setFormatter(file_formatter)
    root_logger.addHandler(file_handler)

    # Reduce noise from external libraries
    logging.getLogger('urllib3').setLevel(logging.WARNING)
    logging.getLogger('requests').setLevel(logging.WARNING)
    logging.getLogger('uvicorn').setLevel(logging.INFO)
    logging.getLogger('uvicorn.access').setLevel(logging.INFO)
    logging.getLogger('fastapi').setLevel(logging.INFO)

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

    logger.info("Logging configured successfully")
    logger.info(f"Log level: {logging.getLevelName(log_level)}")
    logger.info(f"Console colors: {use_colors}")
    logger.info(f"Full tracebacks: {include_traceback}")
    logger.info(f"Log file: {log_file}")


async def initialize_database_connection() -> None:
    """Initialize database connection and verify connectivity"""
    global _connection_manager

    try:
        logger.debug("Initializing database connection...")
        database_url = os.getenv('DATABASE_URL')
        if not database_url:
            raise DatabaseConnectionError("DATABASE_URL environment variable is required")

        _connection_manager = init_database_connection(database_url)
        logger.info("Database connection established and verified")

    except Exception as e:
        logger.error(f"Failed to initialize database: {e}", exc_info=True)
        raise DatabaseConnectionError(f"Database initialization failed: {e}")


async def initialize_services() -> None:
    """Initialize all services using the ServiceContainer singleton"""
    global _connection_manager

    try:
        logger.debug("Initializing services via ServiceContainer...")

        if not _connection_manager:
            raise ServiceInitializationError("Database connection manager not available")

        pdf_storage_path = get_storage_configuration()

        logger.debug("Initializing ServiceContainer...")
        ServiceContainer.initialize(_connection_manager, pdf_storage_path)
        logger.info("ServiceContainer initialized successfully")

        logger.info("All services initialized successfully via ServiceContainer")

        # Try email startup recovery
        try:
            email_ingestion_service = ServiceContainer.get_email_ingestion_service()
            email_ingestion_service.startup_recovery()
            logger.info("Modules service initialized successfully")
        except Exception as service_error:
            logger.warning(f"Email ingestion startup recovery failed: {service_error}")

        # Auto-start ETO processing if enabled
        try:
            worker_enabled = os.getenv('ETO_WORKER_ENABLED', 'true').lower() == 'true'
            if worker_enabled:
                eto_service = ServiceContainer.get_eto_processing_service()
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
        logger.error(f"Failed to initialize services: {e}", exc_info=True)
        # Don't re-raise - allow app to continue with limited functionality
        logger.info("Application will continue with limited functionality")


async def cleanup_services() -> None:
    """Cleanup services and database connections on shutdown"""
    global _connection_manager

    try:
        if ServiceContainer.is_initialized():
            try:
                eto_service = ServiceContainer.get_eto_processing_service()
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
                email_ingestion_service = ServiceContainer.get_email_ingestion_service()
                if hasattr(email_ingestion_service, 'shutdown'):
                    email_ingestion_service.shutdown()
                    logger.info("Email ingestion service stopped")
            except Exception as e:
                logger.warning(f"Failed to stop email ingestion service: {e}")


        if _connection_manager:
            logger.info("Cleaning up database connections...")
            # Add database connection cleanup when implemented
            # _connection_manager.close()

    except Exception as e:
        logger.error(f"Error during cleanup: {e}", exc_info=True)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """FastAPI lifespan event handler for startup and shutdown"""
    
    configure_logging()
    logger.info("Starting Transformation Pipeline Server...")

    try:
        await initialize_database_connection()
        await initialize_services()
        logger.info("Application startup completed successfully")
    except Exception as e:
        logger.error(f"Application startup failed: {e}", exc_info=True)
        raise

    yield

    # Shutdown
    logger.info("Shutting down Transformation Pipeline Server...")
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
    """Setup exception handlers for FastAPI"""
    
    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(request: Request, exc: RequestValidationError):
        """Handle Pydantic validation errors"""
        logger.warning(f"Validation error on {request.method} {request.url}: {exc}")
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
        logger.error(f"Internal server error: {exc}", exc_info=True)
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
        logger.error(f"Error registering health router: {e}", exc_info=True)

    # Register modules router
    try:
        from .api.routers import modules_router
        app.include_router(modules_router, prefix="/api")
        logger.info("Registered modules router")
    except ImportError as e:
        logger.warning(f"Could not import modules router: {e}")
    except Exception as e:
        logger.error(f"Error registering modules router: {e}", exc_info=True)

    # Register pipelines router
    try:
        from .api.routers import pipelines_router
        app.include_router(pipelines_router, prefix="/api")
        logger.info("Registered pipelines router")
    except ImportError as e:
        logger.warning(f"Could not import pipelines router: {e}")
    except Exception as e:
        logger.error(f"Error registering pipelines router: {e}", exc_info=True)
        
    try:
        from .api.routers import eto_router
        app.include_router(eto_router, prefix="/api")
        logger.info("Registered ETO processing router")
    except ImportError as e:
        logger.warning(f"Could not import ETO processing router: {e}")
    except Exception as e:
        logger.error(f"Error registering ETO processing router: {e}", exc_info=True)
        
    try:
        from .api.routers import pdf_templates_router
        app.include_router(pdf_templates_router, prefix="/api")
        logger.info("Registered pdf templates router")
    except ImportError as e:
        logger.warning(f"Could not import pdf templates router: {e}")
    except Exception as e:
        logger.error(f"Error registering pdf templates router: {e}", exc_info=True)
        
    try:
        from .api.routers import email_configs_router
        app.include_router(email_configs_router, prefix="/api")
        logger.info("Registered email configs router")
    except ImportError as e:
        logger.warning(f"Could not import email configs router: {e}")
    except Exception as e:
        logger.error(f"Error registering email configs router: {e}", exc_info=True)


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
        openapi_url="/openapi.json",
        lifespan=lifespan,
    )

    
    setup_cors_middleware(app)
    setup_exception_handlers(app)
    register_routers(app)
    register_info_endpoint(app)

    logger.info("FastAPI application created and configured")

    return app


def run_server():
    """Run the FastAPI server with uvicorn"""
    # Get configuration from environment
    port = int(os.getenv('PORT', 8090))
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