"""
Shared types for email services
Common data structures used across email processing services
"""
from dataclasses import dataclass
from typing import Optional, List, Dict, Any
from datetime import datetime


@dataclass
class EmailConnectionConfig:
    """Email connection configuration data structure"""
    email_address: Optional[str]
    folder_name: str
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'EmailConnectionConfig':
        """Create from dictionary data"""
        return cls(
            email_address=data.get('email_address'),
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
    subject: str
    sender_email: str
    sender_name: Optional[str]
    received_time: datetime
    has_attachments: bool
    attachment_count: int
    attachment_filenames: List[str]
    has_pdf_attachments: bool
    body_preview: Optional[str]


@dataclass
class ConnectionSettings:
    """Connection settings data structure"""
    email_address: Optional[str]
    folder_name: str
    polling_interval: int = 60
    max_hours_back: int = 24


@dataclass
class FilterRule:
    """Individual filter rule data structure"""
    type: str  # 'sender', 'subject', 'attachment', 'date'
    pattern: str
    operation: str = 'contains'  # 'contains', 'equals', 'regex', 'before', 'after'


@dataclass
class FilterConfig:
    """Complete filter configuration data structure"""
    name: str
    rules: List[FilterRule]
    require_attachments: bool = True
    pdf_only: bool = True
    enabled: bool = True


@dataclass
class MonitoringSettings:
    """Monitoring and recovery settings"""
    auto_reconnect: bool = True
    max_reconnect_attempts: int = 5
    connection_timeout: int = 30
    health_check_interval: int = 300


@dataclass
class ConfigurationData:
    """Complete configuration data structure"""
    connection: ConnectionSettings
    filters: FilterConfig
    monitoring: MonitoringSettings
    created_at: datetime
    updated_at: datetime