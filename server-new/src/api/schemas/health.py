"""
Health Check API Schemas
Pydantic models for health monitoring endpoints
"""
from typing import Dict, Any, Optional, Literal
from pydantic import BaseModel


# GET /health - Health Check Response
class ServerStatus(BaseModel):
    status: Literal["up"]  # If server responds, always "up"


class ServiceStatus(BaseModel):
    status: Literal["healthy", "unhealthy"]
    message: Optional[str] = None  # Optional error message if unhealthy


class ServicesStatus(BaseModel):
    email_ingestion: ServiceStatus
    eto_processing: ServiceStatus
    pdf_processing: ServiceStatus
    database: ServiceStatus
    # Additional services from service container can be added dynamically


class HealthCheckResponse(BaseModel):
    status: Literal["healthy", "degraded", "unhealthy"]
    server: ServerStatus
    services: Dict[str, ServiceStatus]  # Using Dict to allow dynamic service keys
