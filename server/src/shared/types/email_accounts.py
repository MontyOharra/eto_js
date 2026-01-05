"""
Email Account Types

Dataclasses for email account management (credentials storage).
Decoupled from ingestion configs - accounts store credentials that can be
shared across multiple ingestion listeners and sending configs.
"""

from dataclasses import dataclass
from datetime import datetime


# =========================
# Provider Settings (connection config, no credentials)
# =========================

@dataclass(frozen=True)
class StandardProviderSettings:
    """
    Standard email provider settings (IMAP + SMTP).

    IMAP is used for receiving/reading emails.
    SMTP is used for sending emails.
    """
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

@dataclass(frozen=True)
class PasswordCredentials:
    """Simple username/password credentials"""
    password: str


@dataclass(frozen=True)
class OAuthCredentials:
    """OAuth token credentials (for Gmail API, etc.)"""
    access_token: str
    refresh_token: str | None = None
    token_expiry: datetime | None = None


# Union type for all credential types
Credentials = PasswordCredentials | OAuthCredentials


# =========================
# Email Account (full record)
# =========================

@dataclass(frozen=True)
class EmailAccount:
    """
    Full email account record from database.
    Contains credentials and connection settings.
    """
    id: int
    name: str
    description: str | None
    provider_type: str  # "imap", "gmail_api", "outlook_com"
    email_address: str
    provider_settings: ProviderSettings
    credentials: Credentials
    is_validated: bool
    validated_at: datetime | None
    last_error_message: str | None
    last_error_at: datetime | None
    created_at: datetime
    updated_at: datetime


@dataclass(frozen=True)
class EmailAccountSummary:
    """
    Lightweight email account summary for list/dropdown operations.
    Does NOT include credentials.
    """
    id: int
    name: str
    email_address: str
    provider_type: str
    is_validated: bool


# =========================
# Create/Update DTOs
# =========================

@dataclass(frozen=True)
class EmailAccountCreate:
    """Data for creating a new email account"""
    name: str
    provider_type: str
    email_address: str
    provider_settings: ProviderSettings
    credentials: Credentials
    description: str | None = None


@dataclass(frozen=True)
class EmailAccountUpdate:
    """
    Data for updating an email account.
    All fields optional - only provided fields are updated.
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

@dataclass(frozen=True)
class EmailAccountValidationResult:
    """Result of validating/testing an email account connection"""
    success: bool
    message: str
    folder_count: int | None = None  # Number of folders discovered
