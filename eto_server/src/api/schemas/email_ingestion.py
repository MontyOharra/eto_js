"""
Email Ingestion API Schemas
Request/response models for email ingestion endpoints
"""
from pydantic import BaseModel, Field, field_validator
from typing import Optional, List
from datetime import datetime
from api.schemas.common import APIResponse, ValidationResponse


class EmailFilterSchema(BaseModel):
    """Email filter rule schema"""
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


class EmailConfigConnectionSchema(BaseModel):
    """Email connection configuration schema"""
    email_address: str = Field(..., description="Email address to monitor", min_length=1)
    folder_name: str = Field(..., description="Email folder name")


class EmailConfigMonitoringSchema(BaseModel):
    """Email monitoring configuration schema"""
    poll_interval_seconds: int = Field(5, ge=5, description="Polling interval in seconds")
    max_backlog_hours: int = Field(24, ge=1, description="Maximum backlog hours")
    error_retry_attempts: int = Field(3, ge=1, le=10, description="Error retry attempts")


class EmailConfigCreateRequest(BaseModel):
    """Request schema for creating email configuration"""
    name: str = Field(..., min_length=1, max_length=255, description="Configuration name")
    description: Optional[str] = Field(None, max_length=1000, description="Configuration description")
    connection: EmailConfigConnectionSchema
    filter_rules: Optional[List[EmailFilterSchema]] = Field(None, description="Email filter rules")
    monitoring: EmailConfigMonitoringSchema
    created_by: str = Field(..., description="User who created the configuration")


class EmailConfigUpdateRequest(BaseModel):
    """Request schema for updating email configuration"""
    description: Optional[str] = Field(None, max_length=1000, description="Configuration description")
    connection: Optional[EmailConfigConnectionSchema] = None
    filter_rules: Optional[List[EmailFilterSchema]] = Field(None, min_length=1, description="Email filter rules")
    monitoring: Optional[EmailConfigMonitoringSchema] = None


class EmailConfigSummaryResponse(BaseModel):
    """Email configuration summary response"""
    id: int
    name: str
    folder_name: str
    is_active: bool
    is_running: bool
    emails_processed: int
    pdfs_found: int
    last_used_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime


class EmailConfigDetailResponse(BaseModel):
    """Detailed email configuration response"""
    id: int
    name: str
    description: Optional[str] = None
    connection: EmailConfigConnectionSchema
    filter_rules: List[EmailFilterSchema]
    monitoring: EmailConfigMonitoringSchema
    is_active: bool
    is_running: bool
    emails_processed: int
    pdfs_found: int
    last_error_message: Optional[str] = None
    last_error_at: Optional[datetime] = None
    created_by: str
    created_at: datetime
    updated_at: datetime
    last_used_at: Optional[datetime] = None


class EmailConfigStatsResponse(BaseModel):
    """Email configuration statistics response"""
    config_id: int
    config_name: str
    total_emails_processed: int
    total_pdfs_found: int
    success_rate: float = Field(ge=0.0, le=1.0, description="Success rate (0.0 to 1.0)")
    avg_processing_time_ms: int = Field(ge=0, description="Average processing time in milliseconds")
    last_24h_emails: int = Field(ge=0, description="Emails processed in last 24 hours")
    last_24h_pdfs: int = Field(ge=0, description="PDFs found in last 24 hours")
    last_error: Optional[str] = None
    last_error_at: Optional[datetime] = None


class EmailConfigTemplateResponse(BaseModel):
    """Configuration template response"""
    connection: EmailConfigConnectionSchema
    filter_rules: List[EmailFilterSchema]
    monitoring: EmailConfigMonitoringSchema


class EmailConfigValidateRequest(BaseModel):
    """Request schema for configuration validation"""
    connection: EmailConfigConnectionSchema
    filter_rules: List[EmailFilterSchema]
    monitoring: EmailConfigMonitoringSchema


class EmailConfigActivateRequest(BaseModel):
    """Request schema for activating configuration"""
    config_id: int = Field(..., description="Configuration ID to activate")


class EmailConfigActivateResponse(BaseModel):
    """Response schema for configuration activation"""
    success: bool = True
    config_id: int
    config_name: str
    message: str
    previous_active_config: Optional[str] = Field(None, description="Previously active configuration name")