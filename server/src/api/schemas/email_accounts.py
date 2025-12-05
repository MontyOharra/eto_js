"""
Email Account API Schemas

Pydantic models for email account API requests and responses.
"""

from typing import Literal, Optional
from pydantic import BaseModel, Field


# ========== Provider Settings ==========

class ImapProviderSettingsSchema(BaseModel):
    """IMAP connection settings"""
    host: str = Field(..., description="IMAP server hostname")
    port: int = Field(993, description="IMAP server port")
    use_ssl: bool = Field(True, description="Use SSL/TLS connection")


ProviderSettingsSchema = ImapProviderSettingsSchema  # Union type for future expansion


# ========== Credentials ==========

class PasswordCredentialsSchema(BaseModel):
    """Password-based credentials"""
    type: Literal["password"] = "password"
    password: str = Field(..., description="Account password or app password")


class OAuthCredentialsSchema(BaseModel):
    """OAuth token credentials"""
    type: Literal["oauth"] = "oauth"
    access_token: str = Field(..., description="OAuth access token")
    refresh_token: Optional[str] = Field(None, description="OAuth refresh token")
    token_expiry: Optional[str] = Field(None, description="Token expiry ISO datetime")


CredentialsSchema = PasswordCredentialsSchema | OAuthCredentialsSchema


# ========== Validation ==========

class ValidateConnectionRequest(BaseModel):
    """Request to test email connection"""
    provider_type: str = Field(..., description="Provider type (imap, gmail_api, etc.)")
    email_address: str = Field(..., description="Email address")
    provider_settings: ImapProviderSettingsSchema = Field(..., description="Provider connection settings")
    credentials: PasswordCredentialsSchema = Field(..., description="Authentication credentials")


class ValidationResultResponse(BaseModel):
    """Response from connection validation"""
    success: bool = Field(..., description="Whether connection was successful")
    message: str = Field(..., description="Status message")
    capabilities: list[str] = Field(default_factory=list, description="Discovered server capabilities")
    folder_count: Optional[int] = Field(None, description="Number of folders discovered")


# ========== Account CRUD ==========

class CreateEmailAccountRequest(BaseModel):
    """Request to create a new email account"""
    name: str = Field(..., description="Display name for the account")
    description: Optional[str] = Field(None, description="Optional description")
    provider_type: str = Field(..., description="Provider type (imap, gmail_api, etc.)")
    email_address: str = Field(..., description="Email address")
    provider_settings: ImapProviderSettingsSchema = Field(..., description="Provider connection settings")
    credentials: PasswordCredentialsSchema = Field(..., description="Authentication credentials")
    capabilities: list[str] = Field(default_factory=list, description="Capabilities from validation")


class UpdateEmailAccountRequest(BaseModel):
    """Request to update an email account"""
    name: Optional[str] = Field(None, description="Display name for the account")
    description: Optional[str] = Field(None, description="Optional description")
    provider_settings: Optional[ImapProviderSettingsSchema] = Field(None, description="Provider settings")
    credentials: Optional[PasswordCredentialsSchema] = Field(None, description="Credentials")
    is_validated: Optional[bool] = Field(None, description="Validation status")
    capabilities: Optional[list[str]] = Field(None, description="Server capabilities")
    clear_errors: bool = Field(False, description="Clear error fields")


class EmailAccountSummaryResponse(BaseModel):
    """Summary of an email account (no credentials)"""
    id: int
    name: str
    email_address: str
    provider_type: str
    is_validated: bool
    capabilities: list[str]


class EmailAccountResponse(BaseModel):
    """Full email account response"""
    id: int
    name: str
    description: Optional[str]
    provider_type: str
    email_address: str
    provider_settings: ImapProviderSettingsSchema
    is_validated: bool
    validated_at: Optional[str]
    capabilities: list[str]
    last_error_message: Optional[str]
    last_error_at: Optional[str]
    created_at: str
    updated_at: str


class EmailAccountListResponse(BaseModel):
    """List of email account summaries"""
    accounts: list[EmailAccountSummaryResponse]
    total: int


class FolderListResponse(BaseModel):
    """List of folders for an email account"""
    account_id: int
    folders: list[str]
