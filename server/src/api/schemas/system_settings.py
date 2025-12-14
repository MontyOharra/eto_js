"""
System Settings API Schemas

Pydantic models for system settings API requests and responses.
"""

from typing import Optional
from pydantic import BaseModel, Field


class SystemSettingResponse(BaseModel):
    """Response for a single system setting"""
    key: str = Field(..., description="Setting key")
    value: Optional[str] = Field(None, description="Setting value (null if not set)")


class SystemSettingsResponse(BaseModel):
    """Response for multiple system settings"""
    settings: dict[str, Optional[str]] = Field(
        default_factory=dict,
        description="Dictionary of setting key -> value"
    )


class SetSystemSettingRequest(BaseModel):
    """Request to set a system setting value"""
    value: Optional[str] = Field(None, description="Setting value (null to clear)")


# ========== Email Settings Specific ==========

class EmailSettingsResponse(BaseModel):
    """Response for email-specific settings"""
    default_sender_account_id: Optional[int] = Field(
        None,
        description="ID of the email account to use for sending emails"
    )


class UpdateEmailSettingsRequest(BaseModel):
    """Request to update email settings"""
    default_sender_account_id: Optional[int] = Field(
        None,
        description="ID of the email account to use for sending (null to clear)"
    )
