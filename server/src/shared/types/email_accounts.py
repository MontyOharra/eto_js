"""
Email Account Types

Pydantic models for email account management (credentials storage).
Decoupled from ingestion configs - accounts store credentials that can be
shared across multiple ingestion listeners and sending configs.
"""

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict


# =========================
# Provider Type
# =========================

ProviderType = Literal["standard"]


# =========================
# Provider Settings (connection config, no credentials)
# =========================

class StandardProviderSettings(BaseModel):
    """
    Standard email provider settings (IMAP + SMTP).

    IMAP is used for receiving/reading emails.
    SMTP is used for sending emails.
    """
    model_config = ConfigDict(frozen=True)

    # IMAP settings (receiving)
    imap_host: str
    imap_port: int

    # SMTP settings (sending)
    smtp_host: str
    smtp_port: int

    # Shared settings
    use_ssl: bool


# Union type for all provider settings
ProviderSettings = StandardProviderSettings


# =========================
# Credentials (sensitive data)
# =========================

class PasswordCredentials(BaseModel):
    """Simple username/password credentials"""
    model_config = ConfigDict(frozen=True)

    password: str


# Union type for all credential types
Credentials = PasswordCredentials


# =========================
# Email Account (full record from DB)
# =========================

class EmailAccount(BaseModel):
    """
    Full email account record from database.
    Contains credentials and connection settings.
    """
    model_config = ConfigDict(frozen=True)

    id: int
    name: str
    description: str | None
    provider_type: ProviderType
    email_address: str
    provider_settings: ProviderSettings
    credentials: Credentials
    is_validated: bool
    validated_at: datetime | None
    last_error_message: str | None
    last_error_at: datetime | None
    created_at: datetime
    updated_at: datetime


class EmailAccountSummary(BaseModel):
    """
    Lightweight email account summary for list/dropdown operations.
    Does NOT include credentials.
    """
    model_config = ConfigDict(frozen=True)

    id: int
    name: str
    email_address: str
    provider_type: ProviderType
    is_validated: bool


# =========================
# Create/Update DTOs
# =========================

class EmailAccountCreate(BaseModel):
    """Data for creating a new email account"""
    model_config = ConfigDict(frozen=True)

    name: str
    provider_type: ProviderType
    email_address: str
    provider_settings: ProviderSettings
    credentials: Credentials
    description: str | None = None


class EmailAccountUpdate(BaseModel):
    """
    Data for updating an email account.

    Uses Pydantic's model_fields_set to distinguish between:
    - Field not provided: not in model_fields_set (don't update)
    - Field set to None: in model_fields_set with None value (set NULL)
    - Field set to value: in model_fields_set with value (update)
    """
    name: str | None = None
    description: str | None = None
    provider_settings: ProviderSettings | None = None
    credentials: Credentials | None = None
    is_validated: bool | None = None
    validated_at: datetime | None = None
    last_error_message: str | None = None
    last_error_at: datetime | None = None


# =========================
# Validation Result
# =========================

class EmailAccountValidationResult(BaseModel):
    """Result of validating/testing an email account connection"""
    model_config = ConfigDict(frozen=True)

    success: bool
    message: str
    folder_count: int | None = None  # Number of folders discovered
