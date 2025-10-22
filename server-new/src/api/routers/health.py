"""
Health Check Router for Transformation Pipeline Server
Provides system status and health monitoring endpoints
"""
import logging
import os
import sys
import time
from datetime import datetime, timezone
from fastapi import APIRouter

from api.schemas.health import HealthCheckResponse

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/health",
    tags=["Health Check"]
)


@router.get("", response_model=HealthCheckResponse)
async def get_health() -> HealthCheckResponse:
    """Get system health status (server + all services)"""
    try:
        # Service layer call will go here to check all services
        # Health endpoint should ALWAYS return 200 if server is up
        # Errors are reported in the response body with degraded/unhealthy status
        # NOT as HTTPException
        pass
    except Exception as e:
        # Even if health check fails, return 200 with degraded status
        # This allows the frontend to see that server is up but services are down
        logger.error(f"Error during health check: {e}")
        # Return degraded/unhealthy response instead of raising HTTPException
        pass
