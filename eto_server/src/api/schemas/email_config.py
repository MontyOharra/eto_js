"""
Email Config API Schemas
Request and response models for email config API endpoints
"""

from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime
from shared.models.email_config import EmailFilterRule


class EmailConfigActivateRequest(BaseModel):
    """Request model for activating/deactivating email configuration"""
    is_active: bool = Field(..., description="Whether to activate or deactivate the config")

    class Config:
        from_attributes = True


class EmailConfigActivateResponse(BaseModel):
    """Response model for configuration activation"""
    success: bool = Field(True, description="Operation success status")
    config_id: int = Field(..., description="Configuration ID")
    config_name: str = Field(..., description="Configuration name")
    is_active: bool = Field(..., description="New active status")
    message: str = Field(..., description="Operation message")
    previous_active_config: Optional[str] = Field(None, description="Previously active configuration name")

    class Config:
        from_attributes = True


class EmailConfigDetailResponse(BaseModel):
    """Detailed config response with runtime info"""
    id: int
    name: str
    description: Optional[str]
    email_address: str
    folder_name: str
    filter_rules: List[EmailFilterRule]
    poll_interval_seconds: int
    max_backlog_hours: int
    error_retry_attempts: int
    is_active: bool
    is_running: bool  # From ingestion service
    emails_processed: int
    pdfs_found: int
    last_error_message: Optional[str]
    last_error_at: Optional[datetime]
    created_at: datetime
    updated_at: datetime
    last_used_at: Optional[datetime]
    cursor_statistics: Optional[Dict[str, Any]]  # From cursor service
    
    class Config:
        from_attributes = True