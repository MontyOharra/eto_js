"""
Email Ingestion Domain Types
Domain objects for email ingestion and config management
"""
from dataclasses import dataclass, field
from typing import Optional, Dict, Any, List
from datetime import datetime

@dataclass
class EmailFilterRule:
    """Individual email filter rule"""
    field: str  # 'subject', 'sender_email', 'has_attachments'
    operation: str  # 'contains', 'equals', 'starts_with', 'ends_with'
    value: str
    case_sensitive: bool = False

@dataclass
class EmailIngestionConfig:
    """Email ingestion config domain object"""
    # Required fields (no defaults)
    id: int
    name: str
    description: Optional[str]
    email_address: Optional[str]  # None = default account
    folder_name: str
    filter_rules: List[EmailFilterRule]
    created_at: datetime
    updated_at: datetime
    
    # Optional fields (with defaults)
    poll_interval_seconds: int
    max_backlog_hours: int
    error_retry_attempts: int
    is_active: bool
    is_running: bool
    last_used_at: Optional[datetime]
    emails_processed: int
    pdfs_found: int
    last_error_message: Optional[str]
    last_error_at: Optional[datetime]

# === Email Processing Types ===

@dataclass
class EmailIngestionCursor:
    """Email ingestion cursor domain object"""
    id: int
    email_address: str
    folder_name: str
    last_processed_message_id: Optional[str]
    last_processed_received_date: Optional[datetime]
    last_check_time: datetime
    total_emails_processed: int
    total_pdfs_found: int
    created_at: datetime
    updated_at: datetime


@dataclass
class EmailIngestionCursorStatistics:
    """Cursor statistics response object"""
    email_address: str
    folder_name: str
    total_emails_processed: int
    total_pdfs_found: int
    last_processed_date: Optional[datetime]
    last_check_time: datetime
    last_message_id: Optional[str]


@dataclass
class EmailIngestionConnectionConfig:
    """Email connection config data structure"""
    email_address: str
    folder_name: str
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'EmailIngestionConnectionConfig':
        """Create from dictionary data"""
        return cls(
            email_address=data['email_address'],  # Required field
            folder_name=data.get('folder_name', 'Inbox')
        )


@dataclass
class EmailServiceConnectionStatus:
    """Connection status information"""
    is_connected: bool
    last_error: Optional[str] = None


@dataclass
class EmailConfigSummary:
    """Summary of current email config"""
    id: Optional[int]
    name: Optional[str]
    email_address: Optional[str]
    folder_name: Optional[str]


@dataclass
class EmailData:
    """Standardized email data structure"""
    message_id: str
    subject: str
    sender_email: str
    sender_name: Optional[str]
    received_time: datetime
    has_attachments: bool
    attachment_count: int
    attachment_filenames: List[str]
    has_pdf_attachments: bool
    body_preview: Optional[str]
    pdf_attachments_data: List[Dict[str, Any]] = field(default_factory=list)
    _outlook_mail_object: Optional[Any] = None  # For deferred PDF extraction


@dataclass
class EmailIngestionStats:
    """Email ingestion statistics"""
    emails_processed: int = 0
    pdfs_found: int = 0
    processing_errors: int = 0
    last_processed_at: Optional[datetime] = None
    uptime_seconds: int = 0
    reconnections: int = 0


@dataclass
class EmailServiceHealth:
    """Service health status"""
    is_running: bool = False
    is_connected: bool = False
    config_loaded: bool = False
    last_error: Optional[str] = None
    stats: EmailIngestionStats = field(default_factory=EmailIngestionStats)


@dataclass
class Email:
    """Email domain object (with ID and timestamps)"""
    id: int
    message_id: str
    subject: str
    sender_email: str
    sender_name: Optional[str]
    received_date: datetime
    folder_name: str
    has_pdf_attachments: bool
    attachment_count: int
    created_at: datetime