"""
Health and Status FastAPI Router
System health check and service status endpoints with proper typing
"""
import logging
from datetime import datetime
from fastapi import APIRouter, HTTPException, Depends, status

from shared.services.service_container import ServiceContainer, get_service_container, is_service_container_initialized
from shared.utils import DateTimeUtils
from api.schemas.health import (
    HealthCheckResponse, DetailedStatusResponse, ReadinessCheckResponse,
    DetailedStatusData, ServiceStatus, EtoServiceStatus, WorkerStatus,
    DatabaseStatus, StorageStatus, ReadinessCheckData
)

logger = logging.getLogger(__name__)

# Create router with prefix and tags
router = APIRouter(prefix="/health", tags=["Health"])


@router.get("/", response_model=HealthCheckResponse)
async def health_check() -> HealthCheckResponse:
    """
    Basic health check endpoint - returns OK if app is running

    Returns basic health status of the application
    """
    return HealthCheckResponse(
        success=True,
        message="Service is running",
        service="ETO Server",
        status="healthy",
        timestamp=DateTimeUtils.utc_now()
    )


@router.get("/status", response_model=DetailedStatusResponse)
async def service_status(
    container: ServiceContainer = Depends(get_service_container)
) -> DetailedStatusResponse:
    """
    Detailed status check for all services

    Returns comprehensive status of all services and system components
    """
    try:
        # Check if service container is initialized
        if not is_service_container_initialized():
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Service container not initialized"
            )

        # Initialize status data
        overall_status = "healthy"
        services = {}

        # Check database connection
        database_status = _check_database_status(container)
        if database_status.status != "healthy":
            overall_status = "degraded"

        # Check storage
        storage_status = _check_storage_status(container)
        if storage_status.status not in ["healthy", "warning"]:
            overall_status = "degraded"

        # Check PDF processing service
        pdf_status = _check_pdf_service_status(container)
        services["pdf_processing"] = pdf_status
        if pdf_status.status != "healthy":
            overall_status = "degraded"

        # Check email ingestion service
        email_status = _check_email_service_status(container)
        services["email_ingestion"] = email_status
        if email_status.status != "healthy":
            overall_status = "degraded"

        # Check PDF template service
        template_status = _check_template_service_status(container)
        services["pdf_templates"] = template_status
        if template_status.status != "healthy":
            overall_status = "degraded"

        # Check ETO processing service
        eto_status = _check_eto_service_status(container)
        services["eto_processing"] = eto_status
        if eto_status.status != "healthy":
            overall_status = "degraded"

        # Build response
        status_data = DetailedStatusData(
            overall_status=overall_status,
            timestamp=DateTimeUtils.utc_now(),
            services=services,
            database=database_status,
            storage=storage_status
        )

        # Return with appropriate HTTP status
        if overall_status != "healthy":
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail=f"System status: {overall_status}"
            )

        return DetailedStatusResponse(
            success=True,
            message="All services operational",
            data=status_data
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Status check failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to check service status"
        )


@router.get("/ready", response_model=ReadinessCheckResponse)
async def readiness_check(
    container: ServiceContainer = Depends(get_service_container)
) -> ReadinessCheckResponse:
    """
    Readiness check - returns OK only if all critical services are ready

    Used by orchestrators to determine if the service is ready to receive traffic
    """
    try:
        # Check if service container is initialized
        if not is_service_container_initialized():
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Services not initialized"
            )

        # Test database connection
        connection_manager = container.get_connection_manager()
        if not connection_manager.test_connection():
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Database not ready"
            )

        # Test that core services are available
        container.get_pdf_service()
        container.get_email_ingestion_service()
        container.get_pdf_template_service()
        container.get_eto_service()

        return ReadinessCheckResponse(
            success=True,
            message="All critical services ready",
            data=ReadinessCheckData(
                ready=True,
                message="All critical services ready",
                timestamp=DateTimeUtils.utc_now()
            )
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Readiness check failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Service readiness check failed: {str(e)}"
        )


# Helper functions for service status checks

def _check_database_status(container: ServiceContainer) -> DatabaseStatus:
    """Check database connection status"""
    try:
        connection_manager = container.get_connection_manager()
        if connection_manager.test_connection():
            return DatabaseStatus(
                status="healthy",
                message="Database connection successful"
            )
        else:
            return DatabaseStatus(
                status="unhealthy",
                message="Database connection failed"
            )
    except Exception as e:
        return DatabaseStatus(
            status="error",
            message=f"Database check failed: {str(e)}"
        )


def _check_storage_status(container: ServiceContainer) -> StorageStatus:
    """Check PDF storage status"""
    try:
        pdf_service = container.get_pdf_service()
        storage_info = pdf_service.get_storage_info()
        return StorageStatus(
            status="healthy",
            message="PDF storage accessible",
            details=storage_info
        )
    except Exception as e:
        return StorageStatus(
            status="warning",
            message=f"Storage check failed: {str(e)}"
        )


def _check_pdf_service_status(container: ServiceContainer) -> ServiceStatus:
    """Check PDF processing service status"""
    try:
        pdf_service = container.get_pdf_service()
        pdf_healthy = pdf_service.is_healthy()
        return ServiceStatus(
            status="healthy" if pdf_healthy else "unhealthy",
            message="PDF processing service operational" if pdf_healthy else "PDF processing service not operational"
        )
    except Exception as e:
        return ServiceStatus(
            status="error",
            message=f"PDF processing service error: {str(e)}"
        )


def _check_email_service_status(container: ServiceContainer) -> ServiceStatus:
    """Check email ingestion service status"""
    try:
        email_service = container.get_email_ingestion_service()
        email_healthy = email_service.is_healthy()
        return ServiceStatus(
            status="healthy" if email_healthy else "unhealthy",
            message="Email ingestion service operational" if email_healthy else "Email ingestion service not operational"
        )
    except Exception as e:
        return ServiceStatus(
            status="error",
            message=f"Email ingestion service error: {str(e)}"
        )


def _check_template_service_status(container: ServiceContainer) -> ServiceStatus:
    """Check PDF template service status"""
    try:
        template_service = container.get_pdf_template_service()
        template_healthy = template_service.is_healthy()
        return ServiceStatus(
            status="healthy" if template_healthy else "unhealthy",
            message="PDF template service operational" if template_healthy else "PDF template service not operational"
        )
    except Exception as e:
        return ServiceStatus(
            status="error",
            message=f"PDF template service error: {str(e)}"
        )


def _check_eto_service_status(container: ServiceContainer) -> EtoServiceStatus:
    """Check ETO processing service status"""
    try:
        eto_service = container.get_eto_service()
        eto_healthy = eto_service.is_healthy()
        worker_status_raw = eto_service.get_worker_status()

        worker_status = WorkerStatus(
            enabled=worker_status_raw.get("worker_enabled", False),
            running=worker_status_raw.get("worker_running", False),
            paused=worker_status_raw.get("worker_paused", False),
            pending_runs=worker_status_raw.get("pending_runs_count", 0),
            processing_runs=worker_status_raw.get("currently_processing_count", 0)
        )

        return EtoServiceStatus(
            status="healthy" if eto_healthy else "unhealthy",
            message="ETO processing service operational" if eto_healthy else "ETO processing service not operational",
            worker=worker_status
        )
    except Exception as e:
        return EtoServiceStatus(
            status="error",
            message=f"ETO processing service error: {str(e)}"
        )