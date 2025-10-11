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
from api.schemas import HealthResponse

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/health",
    tags=["Health Check"]
)

# Track server start time for uptime calculation
SERVER_START_TIME = time.time()


@router.get("/", response_model=HealthResponse)
async def health_check():
    """
    Health check endpoint
    Returns system status and basic information
    """
    logger.info("Health check requested")

    current_time = datetime.now(timezone.utc)
    uptime = time.time() - SERVER_START_TIME

    # Gather system information
    system_info = {
        "python_version": sys.version,
        "platform": sys.platform,
        "cwd": os.getcwd(),
        "pid": os.getpid(),
        "log_level": logging.getLevelName(logging.getLogger().level)
    }

    response = HealthResponse(
        status="healthy",
        message="Transformation Pipeline Server is running",
        timestamp=current_time.isoformat(),
        version="1.0.0",
        server="transformation_pipeline_server",
        uptime_seconds=round(uptime, 2),
        system=system_info
    )

    logger.info(f"Health check completed - uptime: {uptime:.2f}s")
    return response