"""
System Settings API Schemas

Pydantic models for system settings API requests and responses.
"""
from pydantic import BaseModel, Field


# ========== Email Settings ==========

class EmailSettingsResponse(BaseModel):
    """Response for email-specific settings"""
    default_sender_account_id: int | None = Field(
        None,
        description="ID of the email account to use for sending emails"
    )


class UpdateEmailSettingsRequest(BaseModel):
    """Request to update email settings"""
    default_sender_account_id: int | None = Field(
        None,
        description="ID of the email account to use for sending (null to clear)"
    )


# ========== Order Management Settings ==========

class OrderManagementSettingsResponse(BaseModel):
    """Response for order management settings"""
    auto_create_enabled: bool = Field(
        True,
        description="Whether orders are automatically created when ready (default: True)"
    )


class UpdateOrderManagementSettingsRequest(BaseModel):
    """Request to update order management settings"""
    auto_create_enabled: bool = Field(
        ...,
        description="Whether to enable automatic order creation"
    )
