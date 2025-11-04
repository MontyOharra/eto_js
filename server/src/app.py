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
from shared.database.connection import DatabaseConnectionManager
from shared.database.access_connection import AccessConnectionManager
from shared.services.service_container import ServiceContainer
from shared.config.storage import get_storage_configuration
from shared.config.database import DatabaseConfig
from shared.exceptions.service import ObjectNotFoundError, ConflictError, ValidationError, ServiceError

logger = logging.getLogger(__name__)

# Global variables to store initialized database connections
_connection_manager = None  # Primary 'main' connection
_connection_managers = {}  # All named connections


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
    """Initialize all database connections from configuration"""
    global _connection_manager, _connection_managers

    try:
        logger.debug("Loading database configuration...")
        db_config = DatabaseConfig.from_environment()
        logger.info("Database configuration loaded successfully")

        # Initialize all configured connections
        _connection_managers = {}

        for conn_name, conn_config in db_config.get_all_connections().items():
            logger.debug(f"Initializing '{conn_name}' database connection (type: {conn_config.connection_type})...")

            # Create appropriate connection manager based on type
            if conn_config.connection_type == "access":
                # Use Access-specific connection manager
                manager = AccessConnectionManager(conn_config.connection_string)
                manager.initialize_connection()
                logger.info(f"Access database connection '{conn_name}' established and verified")
            else:
                # Use SQLAlchemy-based connection manager (default)
                manager = init_database_connection(conn_config.connection_string)
                logger.info(f"Database connection '{conn_name}' established and verified")

            _connection_managers[conn_name] = manager

        # Set primary connection manager for backward compatibility
        _connection_manager = _connection_managers.get('main')
        if not _connection_manager:
            raise DatabaseConnectionError("Primary 'main' database connection not configured")

        logger.info(f"Initialized {len(_connection_managers)} database connection(s)")

    except Exception as e:
        logger.error(f"Failed to initialize database connections: {e}", exc_info=True)
        raise DatabaseConnectionError(f"Database initialization failed: {e}")


async def initialize_services() -> None:
    """Initialize all services using the ServiceContainer singleton"""
    global _connection_manager, _connection_managers

    try:
        logger.debug("Initializing services via ServiceContainer...")

        if not _connection_manager:
            raise ServiceInitializationError("Database connection manager not available")

        pdf_storage_path = get_storage_configuration()

        logger.debug("Initializing ServiceContainer...")
        ServiceContainer.initialize(
            connection_manager=_connection_manager,
            pdf_storage_path=pdf_storage_path,
            connection_managers=_connection_managers
        )
        logger.info("ServiceContainer initialized successfully")

        # Eagerly initialize all services to ensure proper startup
        logger.info("Eagerly initializing all services...")

        # 1. Initialize modules service FIRST (triggers auto-discovery)
        try:
            modules_service = ServiceContainer.get_modules_service()
            logger.info("Modules service initialized (auto-discovery complete)")
        except Exception as e:
            logger.error(f"Failed to initialize modules service: {e}")
            # Continue - other services may still work

        # 2. Initialize core data services
        try:
            pdf_files_service = ServiceContainer.get_pdf_files_service()
            logger.info("PDF files service initialized")
        except Exception as e:
            logger.warning(f"Failed to initialize PDF files service: {e}")

        try:
            pipeline_service = ServiceContainer.get_pipeline_service()
            logger.info("Pipeline service initialized")
        except Exception as e:
            logger.warning(f"Failed to initialize pipeline service: {e}")

        try:
            pdf_template_service = ServiceContainer.get_pdf_template_service()
            logger.info("PDF template service initialized")
        except Exception as e:
            logger.warning(f"Failed to initialize PDF template service: {e}")

        # 3. Initialize ingestion services
        try:
            email_ingestion_service = ServiceContainer.get_email_ingestion_service()
            logger.info("Email ingestion service initialized")
        except Exception as e:
            logger.warning(f"Failed to initialize email ingestion service: {e}")

        try:
            email_config_service = ServiceContainer.get_email_config_service()
            logger.info("Email config service initialized")
        except Exception as e:
            logger.warning(f"Failed to initialize email config service: {e}")

        # 4. Initialize ETO processing services
        try:
            eto_runs_service = ServiceContainer.get_eto_runs_service()
            logger.info("ETO runs service initialized")
        except Exception as e:
            logger.warning(f"Failed to initialize ETO runs service: {e}")

        logger.info("All services initialized successfully")

        # Start email ingestion service (background workers)
        try:
            email_ingestion_service = ServiceContainer.get_email_ingestion_service()
            email_ingestion_service.startup()
            logger.info("Email ingestion service started successfully")
        except Exception as service_error:
            logger.warning(f"Email ingestion service startup failed: {service_error}")

        # Start ETO processing worker (background polling)
        try:
            eto_runs_service = ServiceContainer.get_eto_runs_service()
            worker_started = await eto_runs_service.startup()
            if worker_started:
                logger.info("ETO processing worker started successfully")
            else:
                logger.warning("ETO processing worker failed to start or is disabled")
        except Exception as service_error:
            logger.warning(f"ETO processing worker startup failed: {service_error}")


    except Exception as e:
        logger.error(f"Failed to initialize services: {e}", exc_info=True)
        # Don't re-raise - allow app to continue with limited functionality
        logger.info("Application will continue with limited functionality")


async def cleanup_services() -> None:
    """Cleanup services and database connections on shutdown"""
    global _connection_manager

    try:
        # Gracefully close all SSE connections first
        try:
            from shared.events.eto_events import eto_event_manager
            await eto_event_manager.shutdown()
            logger.info("SSE connections closed gracefully")
        except Exception as e:
            logger.warning(f"Failed to close SSE connections: {e}")

        if ServiceContainer.is_initialized():
            # Stop email ingestion service if running
            try:
                email_ingestion_service = ServiceContainer.get_email_ingestion_service()
                if hasattr(email_ingestion_service, 'shutdown'):
                    email_ingestion_service.shutdown()
                    logger.info("Email ingestion service stopped")
            except Exception as e:
                logger.warning(f"Failed to stop email ingestion service: {e}")

            # Stop ETO processing worker if running
            try:
                eto_runs_service = ServiceContainer.get_eto_runs_service()
                if hasattr(eto_runs_service, 'shutdown'):
                    await eto_runs_service.shutdown(graceful=True)
                    logger.info("ETO processing worker stopped gracefully")
            except Exception as e:
                logger.warning(f"Failed to stop ETO processing worker: {e}")


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
    async def schema_validation_exception_handler(request: Request, exc: RequestValidationError):
        """Handle Pydantic validation errors"""
        # Sanitize error details to avoid logging/serializing large binary data
        errors = exc.errors()
        sanitized_errors = []
        for error in errors:
            sanitized_error = error.copy()
            # If input is bytes, truncate for both logging and response
            if 'input' in sanitized_error and isinstance(sanitized_error['input'], bytes):
                input_bytes = sanitized_error['input']
                if len(input_bytes) > 100:
                    sanitized_error['input'] = f"<binary data, {len(input_bytes)} bytes>"
                else:
                    # Even small bytes can't be JSON serialized
                    sanitized_error['input'] = f"<binary data, {len(input_bytes)} bytes>"
            sanitized_errors.append(sanitized_error)

        # Log detailed validation errors
        logger.error(f"=" * 80)
        logger.error(f"REQUEST VALIDATION FAILED: {request.method} {request.url}")
        logger.error(f"Total validation errors: {len(sanitized_errors)}")
        logger.error(f"-" * 80)

        for idx, error in enumerate(sanitized_errors, 1):
            logger.error(f"Error {idx}:")
            logger.error(f"  Location: {' -> '.join(str(loc) for loc in error.get('loc', []))}")
            logger.error(f"  Type: {error.get('type', 'unknown')}")
            logger.error(f"  Message: {error.get('msg', 'unknown')}")

            # Smart input logging - don't log large structures
            if 'input' in error:
                input_val = error['input']
                # If it's a dict or list, just show type and size
                if isinstance(input_val, dict):
                    logger.error(f"  Input type: dict with {len(input_val)} keys")
                elif isinstance(input_val, list):
                    logger.error(f"  Input type: list with {len(input_val)} items")
                elif isinstance(input_val, str) and len(input_val) > 100:
                    logger.error(f"  Input (truncated): {input_val[:100]}...")
                else:
                    logger.error(f"  Input: {input_val}")

            if 'ctx' in error:
                logger.error(f"  Context: {error.get('ctx')}")

        logger.error(f"=" * 80)

        return JSONResponse(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            content={
                "error": "Validation error",
                "message": "The request data failed validation",
                "details": sanitized_errors,  # Return sanitized details (bytes can't be JSON serialized)
            }
        )

    @app.exception_handler(FastAPIHTTPException)
    async def http_exception_handler(request: Request, exc: FastAPIHTTPException):
        """Handle HTTP exceptions with consistent JSON response"""
        return JSONResponse(
            status_code=exc.status_code,
            content={
                "error": exc.detail,
                "message": exc.detail,
            }
        )
        
    @app.exception_handler(ValidationError)
    async def validation_exception_handler(request: Request, exc : ValidationError):
        """Handle 400 errors with consistent JSON response"""
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content={
                "error": "Validation error",
                "message": exc.args[0] if len(exc.args) > 0 else "The request data failed validation",
            }
        )

    @app.exception_handler(ObjectNotFoundError)
    async def not_found_handler(request: Request, exc : ObjectNotFoundError):
        """Handle 404 errors with consistent JSON response"""
        logger.info(f"Resource not found on {request.method} {request.url.path}: {exc}")
        return JSONResponse(
            status_code=status.HTTP_404_NOT_FOUND,
            content={
                "error": "Resource not found",
                "message": exc.args[0] if len(exc.args) > 0 else "The requested resource does not exist",
            }
        )

    @app.exception_handler(ConflictError)
    async def conflict_handler(request: Request, exc : ConflictError):
        """Handle 409 errors with consistent JSON response"""
        logger.warning(f"Conflict on {request.method} {request.url.path}: {exc}")
        return JSONResponse(
            status_code=status.HTTP_409_CONFLICT,
            content={
                "error": "Conflict",
                "message": exc.args[0] if len(exc.args) > 0 else "The request conflicts with current state",
            }
        )

    @app.exception_handler(ServiceError)
    async def service_error_handler(request: Request, exc : ServiceError):
        """Handle service-level errors with 500 response"""
        logger.error(f"Service error on {request.method} {request.url.path}: {exc}", exc_info=True)
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={
                "error": "Service error",
                "message": exc.args[0] if len(exc.args) > 0 else "An error occurred while processing the request",
            }
        )

    @app.exception_handler(Exception)
    async def internal_server_error_handler(request: Request, exc : Exception):
        """Handle 500 errors with consistent JSON response"""
        logger.error(f"Internal server error: {exc}", exc_info=True)
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={
                "error": "Internal server error",
                "message": "An unexpected error occurred on the server",
            }
        )


def register_routers(app: FastAPI) -> None:
    """Register FastAPI routers"""
    try:
        from .api.routers import (
            email_configs_router,
            pdf_files_router,
            pdf_templates_router,
            pipelines_router,
            modules_router,
            admin_router,
            eto_runs_router,
        )

        # Register all routers
        app.include_router(email_configs_router, prefix="/api")
        logger.info("Registered email configs router at /api/email-configs")

        app.include_router(pdf_files_router, prefix="/api")
        logger.info("Registered pdf files router at /api/pdf-files")

        app.include_router(pdf_templates_router, prefix="/api")
        logger.info("Registered pdf templates router at /api/pdf-templates")

        app.include_router(pipelines_router, prefix="/api")
        logger.info("Registered pipelines router at /api/pipelines")

        app.include_router(modules_router, prefix="/api")
        logger.info("Registered modules router at /api/modules")

        app.include_router(admin_router, prefix="/api")
        logger.info("Registered admin router at /api/admin")

        app.include_router(eto_runs_router, prefix="/api")
        logger.info("Registered eto runs router at /api/eto-runs")

    except ImportError as e:
        logger.error(f"Could not import routers: {e}", exc_info=True)
        raise
    except Exception as e:
        logger.error(f"Error registering routers: {e}", exc_info=True)
        raise
        

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
                "email_configs": "/api/email-configs",
                "pdf_files": "/api/pdf-files",
                "pdf_templates": "/api/pdf-templates",
                "pipelines": "/api/pipelines",
                "modules": "/api/modules",
                "admin": "/api/admin",
                "eto_runs": "/api/eto-runs"
            },
            "documentation": {
                "email_configs": "Email ingestion configuration management (CRUD, activation, discovery)",
                "pdf_files": "PDF file storage, extraction, and object retrieval",
                "pdf_templates": "PDF template creation, versioning, and activation",
                "pipelines": "Pipeline definition management (dev/testing - CRUD, compilation)",
                "modules": "Module catalog access (GET modules for pipeline building)",
                "admin": "Administrative endpoints (module sync, system management)",
                "eto_runs": "ETO run lifecycle management (list, view, reprocess, skip, delete)"
            },
            "features": {
                "email_ingestion": "Automated email monitoring with Outlook COM integration",
                "pdf_processing": "PDF extraction with pdfminer.six",
                "template_matching": "Signature-based template matching with versioning",
                "pipeline_execution": "Visual node-based transformation pipelines"
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
    port = int(os.getenv('PORT', 8000))
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