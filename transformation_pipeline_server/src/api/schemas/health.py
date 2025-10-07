from typing import Dict, Any
from pydantic import BaseModel

class HealthResponse(BaseModel):
    """Health check response model"""
    status: str
    message: str
    timestamp: str
    version: str
    server: str
    uptime_seconds: float
    system: Dict[str, Any]