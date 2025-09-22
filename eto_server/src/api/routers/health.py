"""
Health and Status FastAPI Router
System health check and service status endpoints
"""
import logging
from datetime import datetime, timezone
from typing import Dict, Any
from fastapi import APIRouter, HTTPException, status
from fastapi.responses import JSONResponse

from shared.services.service_container import get_service_container, is_service_container_initialized

logger = logging.getLogger(__name__)

# Create router with prefix and tags
router = APIRouter(prefix="/health", tags=["health", "system"])


@router.get("/", summary="Basic health check")
async def health_check() -> Dict[str, Any]:
    """
    Basic health check endpoint - returns OK if app is running

    Returns:
        Simple health status
    """
    return {
        "status": "healthy",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "service": "ETO Server"
    }


@router.get("/status", summary="Detailed service status")
async def service_status() -> Dict[str, Any]:
    """
    Detailed status check for all services

    Returns:
        Status of each service and overall system health
    """
    status_data = {
        "overall_status": "healthy",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "services": {},
        "database": {"status": "unknown"},
        "storage": {"status": "unknown"}
    }

    try:
        # Check if service container is initialized
        if not is_service_container_initialized():
            status_data["overall_status"] = "degraded"
            status_data["services"]["container"] = {
                "status": "not_initialized",
                "message": "Service container not initialized"
            }
            return JSONResponse(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                content=status_data
            )

        # Get service container
        container = get_service_container()

        # Check database connection
        try:
            connection_manager = container.get_connection_manager()
            if connection_manager.test_connection():
                status_data["database"] = {
                    "status": "healthy",
                    "message": "Database connection successful"
                }
            else:
                status_data["database"] = {
                    "status": "unhealthy",
                    "message": "Database connection failed"
                }
                status_data["overall_status"] = "degraded"
        except Exception as e:
            status_data["database"] = {
                "status": "error",
                "message": f"Database check failed: {str(e)}"
            }
            status_data["overall_status"] = "degraded"

        # Check PDF processing service
        try:
            pdf_service = container.get_pdf_service()
            status_data["services"]["pdf_processing"] = {
                "status": "healthy",
                "message": "PDF processing service available"
            }

            # Get storage info if available
            try:
                storage_info = pdf_service.get_storage_info()
                status_data["storage"] = {
                    "status": "healthy",
                    "message": "PDF storage accessible",
                    "details": storage_info
                }
            except Exception as e:
                status_data["storage"] = {
                    "status": "warning",
                    "message": f"Storage check failed: {str(e)}"
                }

        except Exception as e:
            status_data["services"]["pdf_processing"] = {
                "status": "error",
                "message": f"PDF processing service error: {str(e)}"
            }
            status_data["overall_status"] = "degraded"

        # Check email ingestion service
        try:
            email_service = container.get_email_ingestion_service()
            status_data["services"]["email_ingestion"] = {
                "status": "healthy",
                "message": "Email ingestion service available"
            }
        except Exception as e:
            status_data["services"]["email_ingestion"] = {
                "status": "error",
                "message": f"Email ingestion service error: {str(e)}"
            }
            status_data["overall_status"] = "degraded"

        # Check PDF template service
        try:
            template_service = container.get_pdf_template_service()
            status_data["services"]["pdf_templates"] = {
                "status": "healthy",
                "message": "PDF template service available"
            }
        except Exception as e:
            status_data["services"]["pdf_templates"] = {
                "status": "error",
                "message": f"PDF template service error: {str(e)}"
            }
            status_data["overall_status"] = "degraded"

        # Return appropriate HTTP status based on overall health
        if status_data["overall_status"] == "healthy":
            return status_data
        else:
            return JSONResponse(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                content=status_data
            )

    except Exception as e:
        logger.error(f"Status check failed: {e}")
        error_status = {
            "overall_status": "error",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "error": str(e),
            "message": "Failed to check service status"
        }
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content=error_status
        )


@router.get("/ready", summary="Readiness check")
async def readiness_check() -> Dict[str, Any]:
    """
    Readiness check - returns OK only if all critical services are ready

    Returns:
        Ready status based on critical service availability
    """
    try:
        if not is_service_container_initialized():
            return JSONResponse(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                content={
                    "ready": False,
                    "message": "Services not initialized",
                    "timestamp": datetime.now(timezone.utc).isoformat()
                }
            )

        # Check critical services
        container = get_service_container()

        # Test database connection
        connection_manager = container.get_connection_manager()
        if not connection_manager.test_connection():
            return JSONResponse(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                content={
                    "ready": False,
                    "message": "Database not ready",
                    "timestamp": datetime.now(timezone.utc).isoformat()
                }
            )

        # Test that core services are available
        container.get_pdf_service()
        container.get_email_ingestion_service()
        container.get_pdf_template_service()

        return {
            "ready": True,
            "message": "All critical services ready",
            "timestamp": datetime.now(timezone.utc).isoformat()
        }

    except Exception as e:
        logger.error(f"Readiness check failed: {e}")
        return JSONResponse(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            content={
                "ready": False,
                "message": f"Service readiness check failed: {str(e)}",
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
        )