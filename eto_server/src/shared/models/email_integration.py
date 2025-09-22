"""
Email Integration Domain Models
Pydantic models for standardized email integration across all providers
"""
from typing import List, Dict, Any, Optional, Literal
from datetime import datetime
from pydantic import BaseModel, Field
from enum import Enum


class EmailProvider(str, Enum):
    """Supported email provider types"""
    OUTLOOK_COM = "outlook_com"  # Local Outlook COM
    OUTLOOK_GRAPH = "outlook_graph"  # Microsoft Graph API
    GMAIL_API = "gmail_api"  # Gmail API
    IMAP_GENERIC = "imap_generic"  # Generic IMAP
    EXCHANGE = "exchange"  # Exchange Web Services


# ========== Core Email Models ==========

class EmailMessage(BaseModel):
    """Standardized email message format for all providers"""
    message_id: str = Field(..., description="Unique message identifier")
    subject: str = Field(..., description="Email subject line")
    sender_email: str = Field(..., description="Sender email address")
    sender_name: Optional[str] = Field(default=None, description="Sender display name")
    recipient_emails: List[str] = Field(default_factory=list, description="List of recipient emails")
    received_date: datetime = Field(..., description="When email was received (UTC)")
    folder_name: str = Field(..., description="Folder containing the email")
    body_text: Optional[str] = Field(default=None, description="Plain text body")
    body_html: Optional[str] = Field(default=None, description="HTML body")
    body_preview: Optional[str] = Field(default=None, max_length=500, description="Body preview")
    has_attachments: bool = Field(default=False, description="Whether email has attachments")
    attachment_count: int = Field(default=0, ge=0, description="Number of attachments")
    attachment_filenames: List[str] = Field(default_factory=list, description="List of attachment filenames")
    size_bytes: int = Field(default=0, ge=0, description="Total email size")
    is_read: bool = Field(default=False, description="Read status")
    importance: str = Field(default="normal", description="Email importance level")
    raw_headers: Optional[Dict[str, str]] = Field(default=None, description="Raw email headers")
    provider_specific_data: Optional[Dict[str, Any]] = Field(default=None, description="Provider-specific metadata")
    
    class Config:
        from_attributes = True
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


class EmailAttachment(BaseModel):
    """Standardized attachment format"""
    filename: str = Field(..., description="Attachment filename")
    content_type: str = Field(..., description="MIME content type")
    size_bytes: int = Field(..., ge=0, description="Attachment size in bytes")
    content: bytes = Field(..., description="Actual file content")
    content_id: Optional[str] = Field(default=None, description="Content ID for inline attachments")
    is_inline: bool = Field(default=False, description="Whether attachment is inline")
    
    class Config:
        from_attributes = True


class EmailFolder(BaseModel):
    """Standardized folder representation"""
    name: str = Field(..., description="Folder name")
    full_path: str = Field(..., description="Full folder path")
    message_count: int = Field(default=0, ge=0, description="Total messages in folder")
    unread_count: int = Field(default=0, ge=0, description="Unread message count")
    folder_type: Optional[str] = Field(default=None, description="Folder type (inbox, sent, etc.)")
    parent_folder: Optional[str] = Field(default=None, description="Parent folder path")
    
    class Config:
        from_attributes = True


class EmailAccount(BaseModel):
    """Email account information"""
    email_address: str = Field(..., description="Email address")
    display_name: str = Field(..., description="Account display name")
    account_type: str = Field(..., description="Account type (Exchange, IMAP, etc.)")
    is_default: bool = Field(default=False, description="Whether this is the default account")
    provider_specific_id: Optional[str] = Field(default=None, description="Provider-specific account ID")
    
    class Config:
        from_attributes = True


# ========== Search and Filter Models ==========

class EmailSearchCriteria(BaseModel):
    """Search criteria for email queries"""
    subject_contains: Optional[str] = Field(default=None, description="Subject contains text")
    sender_email: Optional[str] = Field(default=None, description="Sender email address")
    sender_name: Optional[str] = Field(default=None, description="Sender display name")
    date_from: Optional[datetime] = Field(default=None, description="Emails after this date")
    date_to: Optional[datetime] = Field(default=None, description="Emails before this date")
    has_attachments: Optional[bool] = Field(default=None, description="Filter by attachment presence")
    has_pdf_attachments: Optional[bool] = Field(default=None, description="Filter by PDF attachment presence")
    is_unread: Optional[bool] = Field(default=None, description="Filter by read status")
    folder_name: str = Field(default="Inbox", description="Folder to search in")
    limit: int = Field(default=100, ge=1, le=1000, description="Maximum results to return")
    
    class Config:
        from_attributes = True


# ========== Configuration Models ==========

class EmailIntegrationConfig(BaseModel):
    """Base configuration for email integrations"""
    provider_type: EmailProvider = Field(..., description="Email provider type")
    account_identifier: Optional[str] = Field(default=None, description="Account email or identifier")
    
    class Config:
        from_attributes = True
        use_enum_values = True


class OutlookComConfig(EmailIntegrationConfig):
    """Configuration specific to Outlook COM integration"""
    provider_type: Literal[EmailProvider.OUTLOOK_COM] = Field(default=EmailProvider.OUTLOOK_COM)
    default_folder: str = Field(default="Inbox", description="Default folder to monitor")
    
    class Config:
        from_attributes = True


class GmailApiConfig(EmailIntegrationConfig):
    """Configuration specific to Gmail API integration"""
    provider_type: Literal[EmailProvider.GMAIL_API] = Field(default=EmailProvider.GMAIL_API)
    credentials_path: str = Field(..., description="Path to OAuth credentials")
    token_path: str = Field(..., description="Path to store token")
    scopes: List[str] = Field(
        default_factory=lambda: ["https://www.googleapis.com/auth/gmail.readonly"],
        description="Gmail API scopes"
    )
    
    class Config:
        from_attributes = True


class ImapConfig(EmailIntegrationConfig):
    """Configuration for generic IMAP integration"""
    provider_type: Literal[EmailProvider.IMAP_GENERIC] = Field(default=EmailProvider.IMAP_GENERIC)
    server: str = Field(..., description="IMAP server address")
    port: int = Field(default=993, ge=1, le=65535, description="IMAP port")
    username: str = Field(..., description="IMAP username")
    password: str = Field(..., description="IMAP password")
    use_ssl: bool = Field(default=True, description="Use SSL/TLS")
    
    class Config:
        from_attributes = True


# ========== Response Models ==========

class ConnectionTestResult(BaseModel):
    """Result of connection test"""
    success: bool = Field(..., description="Whether connection test succeeded")
    message: str = Field(..., description="Test result message")
    error: Optional[str] = Field(default=None, description="Error message if failed")
    details: Optional[Dict[str, Any]] = Field(default=None, description="Additional test details")
    
    class Config:
        from_attributes = True


class ProviderInfo(BaseModel):
    """Email provider information"""
    provider_type: str = Field(..., description="Provider type")
    is_connected: bool = Field(..., description="Connection status")
    supports_multiple_accounts: bool = Field(..., description="Whether provider supports multiple accounts")
    config_summary: Dict[str, Any] = Field(..., description="Configuration summary (sensitive data excluded)")
    
    class Config:
        from_attributes = True