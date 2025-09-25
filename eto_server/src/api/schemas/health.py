"""
Health API Schemas
Request/response models for health and status endpoints
"""
from pydantic import BaseModel, Field
from typing import Optional, Dict, Any
from datetime import datetime
from api.schemas.common import APIResponse


class ServiceStatus(BaseModel):
    """Individual service status"""
    status: str = Field(..., description="Service status (healthy, unhealthy, error)")
    message: str = Field(..., description="Status description")
    details: Optional[Dict[str, Any]] = Field(default=None, description="Additional service details")


class WorkerStatus(BaseModel):
    """ETO worker status details"""
    enabled: bool
    running: bool
    paused: bool
    pending_runs: int
    processing_runs: int


class EtoServiceStatus(ServiceStatus):
    """ETO service status with worker information"""
    worker: Optional[WorkerStatus] = Field(default=None, description="ETO background worker status")


class DatabaseStatus(ServiceStatus):
    """Database connection status"""
    pass


class StorageStatus(ServiceStatus):
    """Storage system status"""
    pass


class HealthCheckResponse(APIResponse):
    """Basic health check response"""
    service: str = "ETO Server"
    status: str = "healthy"
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class DetailedStatusData(BaseModel):
    """Detailed status data"""
    overall_status: str
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    services: Dict[str, ServiceStatus] = Field(default_factory=dict)
    database: DatabaseStatus
    storage: StorageStatus


class DetailedStatusResponse(APIResponse):
    """Detailed service status response"""
    data: Optional[DetailedStatusData] = Field(default=None)


class ReadinessCheckData(BaseModel):
    """Readiness check data"""
    ready: bool
    message: str
    timestamp: datetime = Field(default_factory=datetime.utcnow)