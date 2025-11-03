"""
Common API Schemas
Shared request/response models used across all API endpoints
"""
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime


class APIResponse(BaseModel):
    """Standard API response format"""
    success: bool
    message: Optional[str] = None
    data: Optional[Any] = None
    error: Optional[str] = None


class SuccessResponse(BaseModel):
    """Success API response"""
    success: bool = True
    message: Optional[str] = None
    data: Optional[Any] = None


class ErrorResponse(BaseModel):
    """Error API response"""
    success: bool = False
    error: str
    message: Optional[str] = None


class PaginationParams(BaseModel):
    """Standard pagination parameters"""
    page: int = Field(1, ge=1, description="Page number (1-based)")
    limit: int = Field(20, ge=1, le=100, description="Items per page")
    order_by: Optional[str] = Field(None, description="Field to order by")
    desc: bool = Field(False, description="Descending order")


class PaginatedResponse(BaseModel):
    """Paginated API response"""
    success: bool = True
    data: List[Any]
    pagination: Dict[str, Any] = Field(
        description="Pagination metadata including total, page, limit, etc."
    )
    message: Optional[str] = None


class HealthCheck(BaseModel):
    """Health check response format"""
    success: bool = True
    service: str
    status: str
    message: str
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    uptime_seconds: Optional[int] = None
    version: Optional[str] = None


class ValidationError(BaseModel):
    """Validation error details"""
    field: str
    error: str
    value: Optional[Any] = None


class ValidationResponse(BaseModel):
    """Validation response format"""
    valid: bool
    errors: List[ValidationError] = Field(default_factory=list)
    warnings: List[str] = Field(default_factory=list)