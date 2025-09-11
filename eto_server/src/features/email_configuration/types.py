"""
Email Configuration Domain Types
Domain objects for email configuration management
"""
from dataclasses import dataclass
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
    id: Optional[int]
    name: str
    description: Optional[str]
    
    # Connection settings
    email_address: Optional[str]  # None = default account
    folder_name: str
    
    # Filter configuration
    filter_rules: List[EmailFilterRule]
    
    # Monitoring settings
    poll_interval_seconds: int = 5
    max_backlog_hours: int = 24
    error_retry_attempts: int = 3
    
    # Status and control
    is_active: bool = True
    is_running: bool = False
    
    # Audit fields
    created_by: str
    created_at: datetime
    updated_at: datetime
    last_used_at: Optional[datetime] = None
    
    # Statistics
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