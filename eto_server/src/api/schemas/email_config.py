"""
Email Config API Schemas
Request and response models for email config API endpoints
"""

from pydantic import BaseModel, Field
from typing import Optional, List
from shared.models.email_config import EmailFilterRule, EmailConfigMonitoringSettings


class EmailConfigCreate(BaseModel):
    """Request model for creating new email configurations"""
    name: str = Field(..., min_length=1, max_length=255, description="Configuration name")
    description: Optional[str] = Field(None, max_length=1000, description="Configuration description")
    email_address: str = Field(..., description="Email address to monitor")
    folder_name: str = Field(..., description="Email folder name")
    filter_rules: List[EmailFilterRule] = Field(default_factory=list, description="Email filter rules")
    monitoring: EmailConfigMonitoringSettings = Field(default_factory=EmailConfigMonitoringSettings, description="Monitoring settings")
    created_by: str = Field(..., description="User who created the configuration")

    class Config:
        from_attributes = True


class EmailConfigUpdate(BaseModel):
    """Request model for updating existing email configurations"""
    description: Optional[str] = Field(None, max_length=1000, description="Configuration description")
    filter_rules: Optional[List[EmailFilterRule]] = Field(None, description="Email filter rules")
    monitoring: Optional[EmailConfigMonitoringSettings] = Field(None, description="Monitoring settings")

    class Config:
        from_attributes = True


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