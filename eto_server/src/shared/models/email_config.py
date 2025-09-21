"""
Email Config Domain Models
Core domain models for email ingestion configuration management
"""

from pydantic import BaseModel, Field, field_validator
from typing import Optional, List
from datetime import datetime


class EmailFilterRule(BaseModel):
    """Individual email filter rule"""
    field: str = Field(..., description="Field to filter on")
    operation: str = Field(..., description="Filter operation")
    value: str = Field(..., description="Filter value")
    case_sensitive: bool = Field(False, description="Case sensitive matching")

    @field_validator('field')
    @classmethod
    def validate_field(cls, v):
        allowed_fields = ['sender_email', 'subject', 'has_attachments', 'received_date']
        if v not in allowed_fields:
            raise ValueError(f"Field must be one of: {allowed_fields}")
        return v

    @field_validator('operation')
    @classmethod
    def validate_operation(cls, v):
        allowed_operations = ['contains', 'equals', 'starts_with', 'ends_with', 'before', 'after']
        if v not in allowed_operations:
            raise ValueError(f"Operation must be one of: {allowed_operations}")
        return v

    class Config:
        from_attributes = True


class EmailConfigMonitoringSettings(BaseModel):
    """Email monitoring configuration settings"""
    poll_interval_seconds: int = Field(5, ge=5, description="Polling interval in seconds")
    max_backlog_hours: int = Field(24, ge=1, description="Maximum backlog hours")
    error_retry_attempts: int = Field(3, ge=1, le=10, description="Error retry attempts")

    class Config:
        from_attributes = True


class EmailConfigBase(BaseModel):
    """Core fields required for any email config"""
    name: str = Field(..., min_length=1, max_length=255, description="Configuration name")
    description: Optional[str] = Field(None, max_length=1000, description="Configuration description")
    email_address: str = Field(..., description="Email address to monitor")
    folder_name: str = Field(..., description="Email folder name")
    filter_rules: List[EmailFilterRule] = Field(default_factory=list, description="Email filter rules")
    monitoring: EmailConfigMonitoringSettings = Field(default_factory=EmailConfigMonitoringSettings.model_construct, description="Monitoring settings")

    class Config:
        from_attributes = True


class EmailConfig(EmailConfigBase):
    """Complete email configuration with DB-generated fields"""
    id: int = Field(..., description="Configuration ID (DB-generated)")
    is_active: bool = Field(False, description="Whether config is active")
    is_running: bool = Field(False, description="Whether config is currently running")
    emails_processed: int = Field(0, ge=0, description="Total emails processed")
    pdfs_found: int = Field(0, ge=0, description="Total PDFs found")
    last_error_message: Optional[str] = Field(None, description="Last error message")
    last_error_at: Optional[datetime] = Field(None, description="Last error timestamp")
    created_by: str = Field(..., description="User who created the configuration")
    created_at: datetime = Field(..., description="Creation timestamp")
    updated_at: datetime = Field(..., description="Last update timestamp")
    last_used_at: Optional[datetime] = Field(None, description="Last usage timestamp")

    class Config:
        from_attributes = True


class EmailConfigSummary(BaseModel):
    """Summary view of email configuration for list endpoints"""
    id: int = Field(..., description="Configuration ID")
    name: str = Field(..., description="Configuration name")
    email_address: str = Field(..., description="Email address being monitored")
    folder_name: str = Field(..., description="Email folder name")
    is_active: bool = Field(..., description="Whether config is active")
    is_running: bool = Field(..., description="Whether config is currently running")
    emails_processed: int = Field(0, ge=0, description="Total emails processed")
    pdfs_found: int = Field(0, ge=0, description="Total PDFs found")
    filter_rule_count: int = Field(0, ge=0, description="Number of filter rules")
    last_used_at: Optional[datetime] = Field(None, description="Last usage timestamp")
    created_at: datetime = Field(..., description="Creation timestamp")

    class Config:
        from_attributes = True


class EmailConfigStats(BaseModel):
    """Statistics for email configuration"""
    config_id: int = Field(..., description="Configuration ID")
    config_name: str = Field(..., description="Configuration name")
    total_emails_processed: int = Field(0, ge=0, description="Total emails processed")
    total_pdfs_found: int = Field(0, ge=0, description="Total PDFs found")
    success_rate: float = Field(0.0, ge=0.0, le=1.0, description="Success rate (0.0 to 1.0)")
    avg_processing_time_ms: int = Field(0, ge=0, description="Average processing time in milliseconds")
    last_24h_emails: int = Field(0, ge=0, description="Emails processed in last 24 hours")
    last_24h_pdfs: int = Field(0, ge=0, description="PDFs found in last 24 hours")
    last_error: Optional[str] = Field(None, description="Last error message")
    last_error_at: Optional[datetime] = Field(None, description="Last error timestamp")

    class Config:
        from_attributes = True