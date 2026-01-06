"""
Email Account API Schemas

Pydantic models for email account API requests and responses.
Reuses domain types from shared/types where possible.
"""

from pydantic import BaseModel, Field

from shared.types.email_accounts import (
    ProviderType,
    StandardProviderSettings,
    PasswordCredentials,
    EmailAccount,
    EmailAccountSummary,
    EmailAccountCreate,
    EmailAccountUpdate,
)
from shared.types.email_integrations import ValidationResult


# ========== Validation ==========

class ValidateConnectionRequest(BaseModel):
    """Request to test email connection"""
    provider_type: ProviderType
    email_address: str
    provider_settings: StandardProviderSettings
    credentials: PasswordCredentials


# Reuse domain type for response
ValidationResultResponse = ValidationResult


# ========== Account CRUD ==========

# Reuse domain types directly for create/update requests
CreateEmailAccountRequest = EmailAccountCreate
UpdateEmailAccountRequest = EmailAccountUpdate

# Reuse domain types for responses
EmailAccountResponse = EmailAccount
EmailAccountSummaryResponse = EmailAccountSummary


class EmailAccountListResponse(BaseModel):
    """List of email account summaries"""
    accounts: list[EmailAccountSummary]
    total: int


class FolderListResponse(BaseModel):
    """List of folders for an email account"""
    account_id: int
    folders: list[str]


# ========== Email Sending ==========

class SendEmailRequest(BaseModel):
    """Request to send an email"""
    to_address: str = Field(..., description="Recipient email address")
    subject: str = Field(..., description="Email subject line")
    body: str = Field(..., description="Plain text email body")
    body_html: str | None = Field(None, description="Optional HTML email body")


class SendEmailResponse(BaseModel):
    """Response from sending an email"""
    success: bool
    message: str
