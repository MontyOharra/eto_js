"""
Email Config API Schemas
Request and response models for email config API endpoints
"""

from pydantic import BaseModel, Field
from typing import Optional, List
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