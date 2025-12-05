"""
Email Integration Domain Types
Lightweight dataclass-based types for email integration layer
Uses dataclasses instead of Pydantic for better performance in domain layer
"""
from dataclasses import dataclass, field
from datetime import datetime


# ========== Core Email Types ==========

@dataclass(frozen=True)
class EmailAttachment:
    """Email attachment data carrier"""
    filename: str
    content_type: str
    size_bytes: int
    content: bytes
    content_id: str | None = None
    is_inline: bool = False


@dataclass(frozen=True)
class EmailMessage:
    """
    Standardized email message representation for all providers.
    Lightweight dataclass optimized for service layer usage.
    """
    message_id: str  # Email Message-ID header (globally unique)
    subject: str
    sender_email: str
    received_date: datetime
    folder_name: str

    # UID for tracking (IMAP UID, Graph API id, etc.)
    # Used for incremental fetching: "get all emails with uid > last_processed_uid"
    uid: int | None = None

    # Optional fields
    sender_name: str | None = None
    recipient_emails: list[str] = field(default_factory=list)
    body_text: str | None = None
    body_html: str | None = None
    body_preview: str | None = None

    # Attachment metadata
    has_attachments: bool = False
    attachment_count: int = 0
    attachment_filenames: list[str] = field(default_factory=list)

    # Email properties
    size_bytes: int = 0
    is_read: bool = False
    importance: str = "normal"

    # Performance optimization: cached attachments to avoid re-fetching
    cached_attachments: list[EmailAttachment] = field(default_factory=list)

    # Provider-specific data (if needed)
    raw_headers: dict[str, str] | None = None
    provider_specific_data: dict | None = None


@dataclass(frozen=True)
class EmailFolder:
    """Email folder/mailbox information"""
    name: str
    full_path: str
    message_count: int = 0
    unread_count: int = 0
    folder_type: str | None = None  # inbox, sent, drafts, etc.
    parent_folder: str | None = None


@dataclass(frozen=True)
class EmailAccountInfo:
    """Email account information returned from provider (transient)"""
    email_address: str
    display_name: str
    account_type: str  # Exchange, IMAP, etc.
    is_default: bool = False
    provider_specific_id: str | None = None


# ========== Search and Query Types ==========

@dataclass(frozen=True)
class EmailSearchCriteria:
    """Criteria for searching/filtering emails"""
    folder_name: str = "Inbox"

    # Text filters
    subject_contains: str | None = None
    sender_email: str | None = None
    sender_name: str | None = None

    # Date filters
    date_from: datetime | None = None
    date_to: datetime | None = None

    # Boolean filters
    has_attachments: bool | None = None
    has_pdf_attachments: bool | None = None
    is_unread: bool | None = None

    # Limit
    limit: int = 100


# ========== Connection and Testing Types ==========

@dataclass(frozen=True)
class ConnectionTestResult:
    """Result of email provider connection test"""
    success: bool
    message: str | None = None
    error: str | None = None
    details: dict | None = None
    capabilities: list[str] = field(default_factory=list)  # Server capabilities (IDLE, UIDPLUS, etc.)
    folder_count: int | None = None  # Number of folders discovered


# ========== Provider Configuration Types ==========

@dataclass(frozen=True)
class OutlookComConfig:
    """Configuration for Outlook COM integration (Windows)"""
    email_address: str | None = None
    folder_name: str = "Inbox"


@dataclass(frozen=True)
class GmailApiConfig:
    """Configuration for Gmail API integration"""
    credentials_path: str = "credentials.json"
    token_path: str = "token.json"
    email_address: str | None = None
    scopes: list[str] = field(default_factory=lambda: [
        "https://www.googleapis.com/auth/gmail.readonly"
    ])


@dataclass(frozen=True)
class ImapConfig:
    """Configuration for generic IMAP integration"""
    server: str
    port: int = 993
    username: str = ""
    password: str = ""
    use_ssl: bool = True
    email_address: str | None = None


@dataclass(frozen=True)
class OutlookGraphConfig:
    """Configuration for Microsoft Graph API integration"""
    client_id: str
    client_secret: str
    tenant_id: str
    email_address: str | None = None
    scopes: list[str] = field(default_factory=lambda: [
        "https://graph.microsoft.com/Mail.Read"
    ])


@dataclass(frozen=True)
class ExchangeConfig:
    """Configuration for Exchange Web Services integration"""
    server: str
    username: str
    password: str
    email_address: str | None = None
    use_oauth: bool = False
