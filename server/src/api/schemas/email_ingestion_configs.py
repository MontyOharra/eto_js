"""
Email Ingestion Config API Schemas

Pydantic models for email ingestion config API requests and responses.
"""

from typing import Literal, Optional
from pydantic import BaseModel, Field


# ========== Filter Rules ==========

class FilterRuleSchema(BaseModel):
    """Rule for filtering which emails to process"""
    field: Literal["sender_email", "subject", "has_attachments", "received_date"]
    operation: Literal["contains", "equals", "starts_with", "ends_with", "before", "after", "is"]
    value: str
    case_sensitive: bool = False


# ========== Validation ==========

class ValidateIngestionConfigRequest(BaseModel):
    """Request to validate an ingestion config before creation"""
    account_id: int = Field(..., description="Account ID to use")
    folder_name: str = Field(..., description="Folder to monitor")


class ValidateIngestionConfigResponse(BaseModel):
    """Response from ingestion config validation"""
    valid: bool = Field(..., description="Whether the config is valid")
    message: str = Field(..., description="Validation message")


# ========== CRUD ==========

class CreateIngestionConfigRequest(BaseModel):
    """Request to create a new ingestion config"""
    name: str = Field(..., description="Display name for the config")
    account_id: int = Field(..., description="Account ID to use")
    folder_name: str = Field(..., description="Folder to monitor")
    description: Optional[str] = Field(None, description="Optional description")
    filter_rules: list[FilterRuleSchema] = Field(default_factory=list, description="Email filter rules")
    poll_interval_seconds: int = Field(60, description="Polling interval in seconds")
    use_idle: bool = Field(True, description="Use IMAP IDLE if available")


class UpdateIngestionConfigRequest(BaseModel):
    """Request to update an ingestion config"""
    name: Optional[str] = Field(None, description="Display name")
    description: Optional[str] = Field(None, description="Description")
    folder_name: Optional[str] = Field(None, description="Folder to monitor")
    filter_rules: Optional[list[FilterRuleSchema]] = Field(None, description="Email filter rules")
    poll_interval_seconds: Optional[int] = Field(None, description="Polling interval")
    use_idle: Optional[bool] = Field(None, description="Use IMAP IDLE")


# ========== Responses ==========

class IngestionConfigSummaryResponse(BaseModel):
    """Summary of an ingestion config"""
    id: int
    name: str
    account_id: int
    folder_name: str
    is_active: bool
    last_check_time: Optional[str]


class IngestionConfigWithAccountResponse(BaseModel):
    """Ingestion config with account info"""
    id: int
    name: str
    description: Optional[str]
    account_id: int
    account_name: str
    account_email: str
    folder_name: str
    is_active: bool
    last_check_time: Optional[str]
    last_error_message: Optional[str]


class IngestionConfigResponse(BaseModel):
    """Full ingestion config response"""
    id: int
    name: str
    description: Optional[str]
    account_id: int
    folder_name: str
    filter_rules: list[FilterRuleSchema]
    poll_interval_seconds: int
    use_idle: bool
    is_active: bool
    activated_at: Optional[str]
    last_check_time: Optional[str]
    last_processed_uid: Optional[int]
    last_error_message: Optional[str]
    last_error_at: Optional[str]
    created_at: str
    updated_at: str


class IngestionConfigListResponse(BaseModel):
    """List of ingestion configs with account info"""
    configs: list[IngestionConfigWithAccountResponse]
    total: int
