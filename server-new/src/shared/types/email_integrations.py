"""
Email Integration Domain Types
Lightweight dataclass-based types for email integration layer
Uses dataclasses instead of Pydantic for better performance in domain layer
"""
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional


# ========== Core Email Types ==========

@dataclass
class EmailAttachment:
    """Email attachment data carrier"""
    filename: str
    content_type: str
    size_bytes: int
    content: bytes
    content_id: Optional[str] = None
    is_inline: bool = False


@dataclass
class EmailMessage:
    """
    Standardized email message representation for all providers.
    Lightweight dataclass optimized for service layer usage.
    """
    message_id: str
    subject: str
    sender_email: str
    received_date: datetime
    folder_name: str

    # Optional fields
    sender_name: Optional[str] = None
    recipient_emails: list[str] = field(default_factory=list)
    body_text: Optional[str] = None
    body_html: Optional[str] = None
    body_preview: Optional[str] = None

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
    raw_headers: Optional[dict[str, str]] = None
    provider_specific_data: Optional[dict] = None


@dataclass
class EmailFolder:
    """Email folder/mailbox information"""
    name: str
    full_path: str
    message_count: int = 0
    unread_count: int = 0
    folder_type: Optional[str] = None  # inbox, sent, drafts, etc.
    parent_folder: Optional[str] = None


@dataclass
class EmailAccount:
    """Email account information from provider"""
    email_address: str
    display_name: str
    account_type: str  # Exchange, IMAP, etc.
    is_default: bool = False
    provider_specific_id: Optional[str] = None


# ========== Search and Query Types ==========

@dataclass
class EmailSearchCriteria:
    """Criteria for searching/filtering emails"""
    folder_name: str = "Inbox"

    # Text filters
    subject_contains: Optional[str] = None
    sender_email: Optional[str] = None
    sender_name: Optional[str] = None

    # Date filters
    date_from: Optional[datetime] = None
    date_to: Optional[datetime] = None

    # Boolean filters
    has_attachments: Optional[bool] = None
    has_pdf_attachments: Optional[bool] = None
    is_unread: Optional[bool] = None

    # Limit
    limit: int = 100


# ========== Connection and Testing Types ==========

@dataclass
class ConnectionTestResult:
    """Result of email provider connection test"""
    success: bool
    message: Optional[str] = None
    error: Optional[str] = None
    details: Optional[dict] = None


# ========== Provider Configuration Types ==========

@dataclass
class OutlookComConfig:
    """Configuration for Outlook COM integration (Windows)"""
    email_address: Optional[str] = None
    folder_name: str = "Inbox"


@dataclass
class GmailApiConfig:
    """Configuration for Gmail API integration"""
    credentials_path: str = "credentials.json"
    token_path: str = "token.json"
    email_address: Optional[str] = None
    scopes: list[str] = field(default_factory=lambda: [
        "https://www.googleapis.com/auth/gmail.readonly"
    ])


@dataclass
class ImapConfig:
    """Configuration for generic IMAP integration"""
    server: str
    port: int = 993
    username: str = ""
    password: str = ""
    use_ssl: bool = True
    email_address: Optional[str] = None


@dataclass
class OutlookGraphConfig:
    """Configuration for Microsoft Graph API integration"""
    client_id: str
    client_secret: str
    tenant_id: str
    email_address: Optional[str] = None
    scopes: list[str] = field(default_factory=lambda: [
        "https://graph.microsoft.com/Mail.Read"
    ])


@dataclass
class ExchangeConfig:
    """Configuration for Exchange Web Services integration"""
    server: str
    username: str
    password: str
    email_address: Optional[str] = None
    use_oauth: bool = False
