"""
Email Ingestion Domain Types
Domain objects for email ingestion and configuration management
"""
from dataclasses import dataclass, field
from typing import Optional, Dict, Any, List
from datetime import datetime
from ...shared.types.common import ProcessingStatus, OptionalString


@dataclass
class EmailFilterRule:
    """Individual email filter rule"""
    field: str  # 'subject', 'sender_email', 'has_attachments'
    operation: str  # 'contains', 'equals', 'starts_with', 'ends_with'
    value: str
    case_sensitive: bool = False


@dataclass
class EmailIngestionConfig:
    """Email ingestion configuration domain object"""
    # Required fields (no defaults)
    id: Optional[int]
    name: str
    description: Optional[str]
    email_address: Optional[str]  # None = default account
    folder_name: str
    filter_rules: List[EmailFilterRule]
    created_by: str
    created_at: datetime
    updated_at: datetime
    
    # Optional fields (with defaults)
    poll_interval_seconds: int = 5
    max_backlog_hours: int = 24
    error_retry_attempts: int = 3
    is_active: bool = True
    is_running: bool = False
    last_used_at: Optional[datetime] = None
    emails_processed: int = 0
    pdfs_found: int = 0
    last_error_message: Optional[str] = None
    last_error_at: Optional[datetime] = None


@dataclass
class EmailConfigSummary:
    """Summary information for email configurations"""
    id: int
    name: str
    folder_name: str
    is_active: bool
    is_running: bool
    emails_processed: int
    pdfs_found: int
    last_used_at: Optional[datetime]
    created_at: datetime
    updated_at: datetime


@dataclass
class EmailConfigStats:
    """Statistics for email configuration performance"""
    config_id: int
    config_name: str
    total_emails_processed: int
    total_pdfs_found: int
    success_rate: float
    avg_processing_time_ms: int
    last_24h_emails: int
    last_24h_pdfs: int
    last_error: Optional[str]
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
class EmailConnectionConfig:
    """Email connection configuration data structure"""
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
    configuration_loaded: bool = False
    last_error: Optional[str] = None
    stats: IngestionStats = field(default_factory=IngestionStats)


# === Email Record Types ===

@dataclass
class Email:
    """Email record domain object"""
    id: int
    message_id: str
    subject: Optional[str]
    sender_email: Optional[str]
    sender_name: Optional[str]
    received_date: datetime
    folder_name: Optional[str]
    has_pdf_attachments: bool
    attachment_count: int
    created_at: datetime