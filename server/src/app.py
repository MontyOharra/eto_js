"""
Transformation Pipeline Server - FastAPI Application
Node-based pipeline system with Dask execution
"""
import os
import sys
from typing import Any

# Add src directory to path BEFORE any local imports
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Setup custom logger class BEFORE any loggers are created
from shared.logging import configure_logging, get_logger, setup_logger_class
setup_logger_class()

from contextlib import asynccontextmanager

from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.exceptions import RequestValidationError, HTTPException as FastAPIHTTPException

from shared.database import init_database_connection
from shared.database.access_connection import AccessConnectionManager
from shared.services.service_container import ServiceContainer
from shared.config.storage import get_storage_configuration
from shared.config.database import load_database_connections
from shared.exceptions.service import ObjectNotFoundError, ConflictError, ValidationError, ServiceError

logger = get_logger(__name__)

# Global variables to store initialized database connections
_main_connection = None  # SQL Server system database (via SQLAlchemy)
_access_connection_manager = None  # Access databases (via pyodbc)


class DatabaseConnectionError(Exception):
    """Raised when database connection cannot be established"""
    pass


class ServiceInitializationError(Exception):
    """Raised when services cannot be initialized"""
    pass


async def initialize_database_connection() -> None:
    """Initialize all database connections from configuration"""
    global _main_connection, _access_connection_manager

    try:
        logger.debug("Loading database configuration...")
        db_connections = load_database_connections()
        logger.info("Database configuration loaded successfully")

        # Separate main (SQL Server) from Access databases
        access_connection_strings = {}

        for conn_name, conn_info in db_connections.items():
            logger.debug(f"Processing '{conn_name}' database connection (type: {conn_info.connection_type})...")

            if conn_name == 'main':
                # Main SQL Server database - use SQLAlchemy
                _main_connection = init_database_connection(conn_info.connection_string)
                logger.info("Main SQL Server database connection established")
            elif conn_info.connection_type == "access":
                # Collect Access database connection strings
                access_connection_strings[conn_name] = conn_info.connection_string
            else:
                logger.warning(f"Unknown connection type '{conn_info.connection_type}' for '{conn_name}', skipping")

        # Validate main connection exists
        if not _main_connection:
            raise DatabaseConnectionError("Primary 'main' database connection not configured")

        # Initialize all Access databases
        if access_connection_strings:
            _access_connection_manager = AccessConnectionManager(access_connection_strings)
            logger.info(f"AccessConnectionManager initialized with {len(access_connection_strings)} database(s)")
        else:
            logger.warning("No Access databases configured")

        total_connections = 1 + len(access_connection_strings)  # main + Access databases
        logger.info(f"Initialized {total_connections} database connection(s)")

    except Exception as e:
        logger.error(f"Failed to initialize database connections: {e}", exc_info=True)
        raise DatabaseConnectionError(f"Database initialization failed: {e}")


async def initialize_services() -> None:
    """Initialize all services using the ServiceContainer singleton"""
    global _main_connection, _access_connection_manager

    try:
        logger.debug("Initializing services via ServiceContainer...")

        if not _main_connection:
            raise ServiceInitializationError("Main database connection not available")

        pdf_storage_path = get_storage_configuration()

        logger.debug("Initializing ServiceContainer...")
        ServiceContainer.initialize(
            main_connection=_main_connection,
            pdf_storage_path=pdf_storage_path,
            access_connection_manager=_access_connection_manager
        )
        logger.info("ServiceContainer initialized successfully")

        # Eagerly initialize all services to ensure proper startup
        logger.info("Eagerly initializing all services...")

        # 1. Initialize storage config FIRST (used by pdf_files)
        try:
            storage_config = ServiceContainer.get('storage_config')
            logger.info("Storage config service initialized")
        except Exception as e:
            logger.warning(f"Failed to initialize storage config: {e}")

        # 2. Initialize modules service (triggers auto-discovery)
        try:
            modules_service = ServiceContainer.get_modules_service()
            logger.info("Modules service initialized (auto-discovery complete)")
        except Exception as e:
            logger.error(f"Failed to initialize modules service: {e}")
            # Continue - other services may still work"""

        # 3. Initialize core data services
        try:
            pdf_files_service = ServiceContainer.get_pdf_files_service()
            logger.info("PDF files service initialized")
        except Exception as e:
            logger.warning(f"Failed to initialize PDF files service: {e}")

        try:
            pipeline_execution_service = ServiceContainer.get_pipeline_execution_service()
            logger.info("Pipeline execution service initialized")
        except Exception as e:
            logger.warning(f"Failed to initialize pipeline execution service: {e}")

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

        # 4. Initialize ingestion services and start email polling
        try:
            email_service = ServiceContainer.get_email_service()
            logger.info("Email service initialized")
            # Start polling for active email configs
            email_service.startup()
            logger.info("Email service startup complete (pollers started for active configs)")
        except Exception as e:
            logger.warning(f"Failed to initialize/start email service: {e}")

        # 5. Initialize HTC integration service (needed by output_processing and order_management)
        htc_integration_service = None
        try:
            htc_integration_service = ServiceContainer.get_htc_integration_service()
            logger.info("HTC integration service initialized")
        except Exception as e:
            logger.warning(f"Failed to initialize HTC integration service: {e}")

        # 7. Initialize ETO runs service
        try:
            eto_runs_service = ServiceContainer.get_eto_runs_service()
            logger.info("ETO runs service initialized")
        except Exception as e:
            logger.warning(f"Failed to initialize ETO runs service: {e}")

        # 9. Initialize auth service (for user authentication)
        try:
            auth_service = ServiceContainer.get_auth_service()
            if auth_service.is_available():
                logger.info("Auth service initialized (staff database connected)")
            else:
                logger.warning("Auth service initialized but staff database not available")
        except Exception as e:
            logger.warning(f"Failed to initialize auth service: {e}")

        logger.info("All services initialized successfully")

        # Sync modules and output channels to database
        try:
            modules_service.sync_registry_to_database()
            logger.info("Module registry synced to database")
        except Exception as e:
            logger.warning(f"Failed to sync module registry: {e}")

        try:
            result = modules_service.sync_output_channel_types()
            logger.info(f"Output channel types synced: {result['total']} types ({result['created']} created, {result['updated']} updated)")
        except Exception as e:
            logger.warning(f"Failed to sync output channel types: {e}")

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
    global _main_connection, _access_connection_manager

    try:
        # Note: SSE connections are handled by uvicorn's task cancellation.
        # The SSE generators handle CancelledError gracefully and unregister.
        # Clients are responsible for detecting disconnection and reconnecting.

        if ServiceContainer.is_initialized():
            # Stop email service pollers
            try:
                email_service = ServiceContainer.get_email_service()
                email_service.shutdown()
                logger.info("Email service shutdown complete (pollers stopped)")
            except Exception as e:
                logger.warning(f"Failed to stop email service: {e}")

            # Stop ETO processing worker if running
            try:
                eto_runs_service = ServiceContainer.get_eto_runs_service()
                if hasattr(eto_runs_service, 'shutdown'):
                    await eto_runs_service.shutdown(graceful=True)
                    logger.info("ETO processing worker stopped gracefully")
            except Exception as e:
                logger.warning(f"Failed to stop ETO processing worker: {e}")

        # Cleanup database connections
        if _main_connection:
            logger.info("Closing main database connection...")
            _main_connection.close()

        if _access_connection_manager:
            logger.info("Closing Access database connections...")
            _access_connection_manager.close_all()

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
            email_accounts_router,
            email_ingestion_configs_router,
            pdf_files_router,
            pdf_templates_router,
            pipelines_router,
            modules_router,
            admin_router,
            eto_runs_router,
            system_settings_router,
            auth_router,
        )

        # Register all routers
        app.include_router(email_accounts_router, prefix="/api")
        logger.info("Registered email accounts router at /api/email-accounts")

        app.include_router(email_ingestion_configs_router, prefix="/api")
        logger.info("Registered email ingestion configs router at /api/email-ingestion-configs")

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

        app.include_router(system_settings_router, prefix="/api")
        logger.info("Registered system settings router at /api/settings")

        app.include_router(auth_router, prefix="/api")
        logger.info("Registered auth router at /api/auth")

    except ImportError as e:
        logger.error(f"Could not import routers: {e}", exc_info=True)
        raise
    except Exception as e:
        logger.error(f"Error registering routers: {e}", exc_info=True)
        raise
        

def register_info_endpoint(app: FastAPI) -> None:
    """Register application info endpoint"""

    @app.get("/", tags=["info"])
    async def app_info() -> dict[str, Any]:
        """Application information endpoint"""
        return {
            "service": "Unified ETO Server",
            "description": "Email-to-Order processing system with feature-based architecture",
            "version": "2.0.0",
            "architecture": "feature-based",
            "framework": "FastAPI",
            "api_prefix": "/api",
            "endpoints": {
                "email_accounts": "/api/email-accounts",
                "email_ingestion_configs": "/api/email-ingestion-configs",
                "pdf_files": "/api/pdf-files",
                "pdf_templates": "/api/pdf-templates",
                "pipelines": "/api/pipelines",
                "modules": "/api/modules",
                "admin": "/api/admin",
                "eto_runs": "/api/eto-runs"
            },
            "documentation": {
                "email_accounts": "Email account management (credentials, validation, CRUD)",
                "email_ingestion_configs": "Email ingestion config management (folders, filters, polling)",
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


# Entry point has been moved to main.py
# This file only contains the FastAPI app factory and configuration