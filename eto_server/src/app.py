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

# Add the src directory to Python path to enable absolute imports
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from shared.utils import ServiceContainer

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

        # Auto-start email ingestion if active config exists
        try:
            email_service = _service_container.get_email_service()
            active_config = email_service.config_service.get_active_config()

            if active_config:
                logger.info(f"Found active configuration: {active_config.name} (ID: {active_config.id})")
                result = email_service.start(active_config.id)

                if result.success:
                    logger.info(f"Email ingestion service started successfully for config: {active_config.name}")
                else:
                    logger.warning(f"Failed to start email ingestion: {result.message}")
            else:
                logger.info("No active email ingestion configuration found - service ready for configuration")

        except Exception as service_error:
            logger.warning(f"Email ingestion auto-connect failed: {service_error}")

        # Auto-start ETO processing if enabled
        try:
            worker_enabled = os.getenv('ETO_WORKER_ENABLED', 'true').lower() == 'true'
            if worker_enabled:
                eto_service = _service_container.get_eto_service()
                eto_service.start()
                logger.info("ETO processing background worker started")
            else:
                logger.info("ETO processing service initialized but worker not started (ETO_WORKER_ENABLED=false)")
        except Exception as eto_error:
            logger.warning(f"ETO processing auto-start failed: {eto_error}")

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
                if hasattr(eto_service, 'stop'):
                    eto_service.stop()
                    logger.info("ETO processing service stopped")
            except Exception as e:
                logger.warning(f"Failed to stop ETO service: {e}")
            
            # Stop email ingestion service if running
            try:
                email_service = _service_container.get_email_service()
                if hasattr(email_service, 'stop'):
                    email_service.stop()
                    logger.info("Email ingestion service stopped")
            except Exception as e:
                logger.warning(f"Failed to stop email service: {e}")

        if _connection_manager:
            logger.info("Cleaning up database connections...")
            # Add database connection cleanup if needed

    except Exception as e:
        logger.error(f"Error during cleanup: {e}")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """FastAPI lifespan context manager for startup and shutdown"""
    # Startup
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
    try:
        # Import and register PDF templates router
        from .api.routers.pdf_templates import router as pdf_templates_router
        app.include_router(pdf_templates_router)
        logger.info("Registered PDF templates router")
        
    except ImportError as e:
        logger.warning(f"Could not import PDF templates router: {e}")
    except Exception as e:
        logger.error(f"Error registering routers: {e}")


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
                "email_configuration": "/api/email-configuration",
                "eto_processing": "/api/eto-runs",
                "pdf_templates": "/api/pdf_templates"
            },
            "documentation": {
                "health": "Service health and status monitoring",
                "email_configuration": "Email ingestion configuration management",
                "eto_processing": "ETO processing run management and results",
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
    uvicorn.run(
        "app-fastapi:create_app",
        factory=True,
        host=host,
        port=port,
        reload=debug,
        log_level="debug" if debug else "info",
        access_log=True
    )


if __name__ == "__main__":
    run_server()