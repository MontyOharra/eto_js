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
class EmailIngestionConfigCreate:
    """Domain object for creating email configs (no ID)"""
    name: str
    description: Optional[str]
    email_address: Optional[str]  # None = default account
    folder_name: str
    filter_rules: List[EmailFilterRule]
    created_by: str
    # Optional fields (with defaults)
    poll_interval_seconds: int = 5
    max_backlog_hours: int = 24
    error_retry_attempts: int = 3


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
    created_by: str
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
class EmailIngestionCursorCreate:
    """Domain object for creating email cursors (no ID)"""
    email_address: str
    folder_name: str
    last_processed_message_id: Optional[str] = None
    last_processed_received_date: Optional[datetime] = None
    last_check_time: Optional[datetime] = None
    total_emails_processed: int = 0
    total_pdfs_found: int = 0


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
class CursorStatistics:
    """Cursor statistics response object"""
    email_address: str
    folder_name: str
    total_emails_processed: int
    total_pdfs_found: int
    last_processed_date: Optional[datetime]
    last_check_time: datetime
    last_message_id: Optional[str]


@dataclass
class EmailConnectionConfig:
    """Email connection config data structure"""
    email_address: str
    folder_name: str
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'EmailConnectionConfig':
        """Create from dictionary data"""
        return cls(
            email_address=data['email_address'],  # Required field
            folder_name=data.get('folder_name', 'Inbox')
        )


@dataclass
class ConnectionStatus:
    """Connection status information"""
    is_connected: bool
    email_address: Optional[str]
    folder_name: Optional[str]
    inbox_count: int
    last_error: Optional[str]
    connection_time: Optional[datetime]


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


@dataclass
class IngestionStats:
    """Email ingestion statistics"""
    emails_processed: int = 0
    pdfs_found: int = 0
    processing_errors: int = 0
    last_processed_at: Optional[datetime] = None
    uptime_seconds: int = 0
    reconnections: int = 0


@dataclass
class ServiceHealth:
    """Service health status"""
    is_running: bool = False
    is_connected: bool = False
    config_loaded: bool = False
    last_error: Optional[str] = None
    stats: IngestionStats = field(default_factory=IngestionStats)


