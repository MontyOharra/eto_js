"""
Email Config Domain Models
Core domain models for email ingestion configuration management
"""

from pydantic import BaseModel, Field, field_validator
from typing import Optional, List
from datetime import datetime
import json


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


class EmailConfigBase(BaseModel):
    """Core fields required for any email config"""
    name: str = Field(..., min_length=1, max_length=255, description="Configuration name")
    description: Optional[str] = Field(None, max_length=1000, description="Configuration description")
    email_address: str = Field(..., description="Email address to monitor")
    folder_name: str = Field(..., description="Email folder name")
    filter_rules: List[EmailFilterRule] = Field(default_factory=list, description="Email filter rules")
    poll_interval_seconds: int = Field(5, ge=5, description="Polling interval in seconds")
    max_backlog_hours: int = Field(24, ge=1, description="Maximum backlog hours")
    error_retry_attempts: int = Field(3, ge=1, le=10, description="Error retry attempts")

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
    created_at: datetime = Field(..., description="Creation timestamp")
    updated_at: datetime = Field(..., description="Last update timestamp")
    last_used_at: Optional[datetime] = Field(None, description="Last usage timestamp")

    class Config:
        from_attributes = True
        
    @classmethod
    def from_db_model(cls, db_model) -> 'EmailConfig':
        """Create from database model with JSON deserialization"""
        # Parse filter_rules JSON
        filter_rules = []
        if db_model.filter_rules:
            try:
                rules_data = json.loads(db_model.filter_rules)
                filter_rules = [EmailFilterRule(**rule) for rule in rules_data]
            except (json.JSONDecodeError, TypeError):
                filter_rules = []

        return cls(
            id=db_model.id,
            name=db_model.name,
            description=db_model.description,
            email_address=db_model.email_address,
            folder_name=db_model.folder_name,
            filter_rules=filter_rules,
            poll_interval_seconds=db_model.poll_interval_seconds,
            max_backlog_hours=db_model.max_backlog_hours,
            error_retry_attempts=db_model.error_retry_attempts,
            is_active=db_model.is_active,
            is_running=db_model.is_running,
            emails_processed=db_model.emails_processed,
            pdfs_found=db_model.pdfs_found,
            last_error_message=db_model.last_error_message,
            last_error_at=db_model.last_error_at,
            created_at=db_model.created_at,
            updated_at=db_model.updated_at,
            last_used_at=db_model.last_used_at
        )


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
        

class EmailConfigCreate(EmailConfigBase):
    """Request model for creating new email configurations"""
    
    def model_dump_for_db(self) -> dict:
        """Convert to database format with JSON serialization"""
        data = self.model_dump()
        # Serialize filter_rules to JSON for database storage
        if 'filter_rules' in data:
            data['filter_rules'] = json.dumps([rule.model_dump() if hasattr(rule, 'model_dump') else dict(rule) for rule in data['filter_rules']])
        return data
    
    class Config:
        from_attributes = True


class EmailConfigUpdate(BaseModel):
    """Request model for updating existing email configurations"""
    description: Optional[str] = Field(None, max_length=1000, description="Configuration description")
    filter_rules: Optional[List[EmailFilterRule]] = Field(None, description="Email filter rules")
    poll_interval_seconds: Optional[int] = Field(None, ge=5, description="Polling interval in seconds")
    max_backlog_hours: Optional[int] = Field(None, ge=1, description="Maximum backlog hours")
    error_retry_attempts: Optional[int] = Field(None, ge=1, le=10, description="Error retry attempts")

    def model_dump_for_db(self) -> dict:
        """Convert to database format, handling optionals and JSON serialization"""
        data = self.model_dump(exclude_unset=True)
        if 'filter_rules' in data and data['filter_rules'] is not None:
            data['filter_rules'] = json.dumps([rule.model_dump() for rule in data['filter_rules']])
        return data

    class Config:
        from_attributes = True

