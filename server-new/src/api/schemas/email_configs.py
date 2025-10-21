"""
Email Configurations API Schemas
Pydantic models for email configuration endpoints
"""
from typing import Optional, List, Literal
from pydantic import BaseModel, Field


# GET /email-configs - List Response
class EmailConfigSummaryItem(BaseModel):
    id: int
    name: str
    is_active: bool
    last_check_time: Optional[str] = None  # ISO 8601


class ListEmailConfigsResponse(BaseModel):
    __root__: List[EmailConfigSummaryItem]


# GET /email-configs/{id} - Detail Response
class FilterRule(BaseModel):
    field: Literal["sender_email", "subject", "has_attachments", "attachment_types"]
    operation: Literal["contains", "equals", "starts_with", "ends_with"]
    value: str
    case_sensitive: bool


class EmailConfigDetail(BaseModel):
    id: int
    name: str
    description: Optional[str] = None
    email_address: str
    folder_name: str
    filter_rules: List[FilterRule]
    poll_interval_seconds: int
    max_backlog_hours: int
    error_retry_attempts: int
    is_active: bool
    activated_at: Optional[str] = None  # ISO 8601
    is_running: bool
    last_check_time: Optional[str] = None  # ISO 8601
    last_error_message: Optional[str] = None
    last_error_at: Optional[str] = None  # ISO 8601


# POST /email-configs - Create Request
class FilterRuleCreate(BaseModel):
    field: Literal["sender_email", "subject", "has_attachments", "attachment_types"]
    operation: Literal["contains", "equals", "starts_with", "ends_with"]
    value: str
    case_sensitive: Optional[bool] = False


class CreateEmailConfigRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = Field(None, max_length=1000)
    email_address: str
    folder_name: str = Field(..., min_length=1)
    filter_rules: Optional[List[FilterRuleCreate]] = []
    poll_interval_seconds: Optional[int] = Field(5, ge=5)
    max_backlog_hours: Optional[int] = Field(24, ge=1)
    error_retry_attempts: Optional[int] = Field(3, ge=1, le=10)


class CreateEmailConfigResponse(BaseModel):
    id: int
    name: str
    description: Optional[str] = None
    email_address: str
    folder_name: str
    filter_rules: List[FilterRule]
    poll_interval_seconds: int
    max_backlog_hours: int
    error_retry_attempts: int
    is_active: bool
    activated_at: Optional[str] = None
    is_running: bool
    last_check_time: Optional[str] = None
    last_error_message: Optional[str] = None
    last_error_at: Optional[str] = None


# PUT /email-configs/{id} - Update Request
class FilterRuleUpdate(BaseModel):
    field: Literal["sender_email", "subject", "has_attachments", "attachment_types"]
    operation: Literal["contains", "equals", "starts_with", "ends_with"]
    value: str
    case_sensitive: Optional[bool] = False


class UpdateEmailConfigRequest(BaseModel):
    description: Optional[str] = Field(None, max_length=1000)
    filter_rules: Optional[List[FilterRuleUpdate]] = None
    poll_interval_seconds: Optional[int] = Field(None, ge=5)
    max_backlog_hours: Optional[int] = Field(None, ge=1)
    error_retry_attempts: Optional[int] = Field(None, ge=1, le=10)


class UpdateEmailConfigResponse(BaseModel):
    id: int
    name: str
    description: Optional[str] = None
    email_address: str
    folder_name: str
    filter_rules: List[FilterRule]
    poll_interval_seconds: int
    max_backlog_hours: int
    error_retry_attempts: int
    is_active: bool
    activated_at: Optional[str] = None
    is_running: bool
    last_check_time: Optional[str] = None
    last_error_message: Optional[str] = None
    last_error_at: Optional[str] = None


# POST /email-configs/{id}/activate - Activate Response
class ActivateEmailConfigResponse(BaseModel):
    id: int
    is_active: bool  # true
    activated_at: str  # ISO 8601
    name: str
    description: Optional[str] = None
    email_address: str
    folder_name: str
    filter_rules: List[FilterRule]
    poll_interval_seconds: int
    max_backlog_hours: int
    error_retry_attempts: int
    is_running: bool
    last_check_time: Optional[str] = None
    last_error_message: Optional[str] = None
    last_error_at: Optional[str] = None


# POST /email-configs/{id}/deactivate - Deactivate Response
class DeactivateEmailConfigResponse(BaseModel):
    id: int
    is_active: bool  # false
    name: str
    description: Optional[str] = None
    email_address: str
    folder_name: str
    filter_rules: List[FilterRule]
    poll_interval_seconds: int
    max_backlog_hours: int
    error_retry_attempts: int
    is_running: bool
    last_check_time: Optional[str] = None
    last_error_message: Optional[str] = None
    last_error_at: Optional[str] = None


# GET /email-configs/discovery/accounts - Discovery Response
class EmailAccountItem(BaseModel):
    email_address: str
    display_name: Optional[str] = None


class DiscoverEmailAccountsResponse(BaseModel):
    __root__: List[EmailAccountItem]


# GET /email-configs/discovery/folders - Discovery Response
class EmailFolderItem(BaseModel):
    folder_name: str
    folder_path: str


class DiscoverEmailFoldersResponse(BaseModel):
    __root__: List[EmailFolderItem]


# POST /email-configs/validate - Validate Request/Response
class ValidateEmailConfigRequest(BaseModel):
    email_address: str
    folder_name: str


class ValidateEmailConfigResponse(BaseModel):
    email_address: str
    folder_name: str
    message: str
