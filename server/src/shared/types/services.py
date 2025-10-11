from pydantic import BaseModel
from enum import Enum


class ServiceHealth(str, Enum):
    """Simple service health status"""
    UP = "up"
    DOWN = "down"


class ServiceStatusResponse(BaseModel):
    """Simple service status response"""
    service: str
    status: ServiceHealth
    message: str = ""