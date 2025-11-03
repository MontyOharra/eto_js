"""
Email Configurations API Schemas
Pydantic models for email configuration endpoints
"""
from typing import Optional, List, Literal
from pydantic import BaseModel, Field, ConfigDict

# Base Models

class FilterRule(BaseModel):
    field: Literal["sender_email", "subject", "has_attachments", "attachment_types"]
    operation: Literal["contains", "equals", "starts_with", "ends_with"]
    value: str
    case_sensitive: bool

class EmailConfigSummary(BaseModel):
    id: int
    name: str
    is_active: bool
    last_check_time: Optional[str] = None  # ISO 8601

class EmailConfig(BaseModel):
    id: int
    name: str
    description: Optional[str] = None
    email_address: str
    folder_name: str
    filter_rules: List[FilterRule]
    poll_interval_seconds: int
    is_active: bool
    activated_at: Optional[str] = None
    last_check_time: Optional[str] = None
    last_error_message: Optional[str] = None
    last_error_at: Optional[str] = None

class EmailAccount(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    
    email_address: str
    display_name: Optional[str] = None


class EmailFolder(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    
    folder_name: str
    folder_path: str


class ListEmailConfigsResponse(BaseModel):
    configs: List[EmailConfigSummary]


class CreateEmailConfigRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = Field(None, max_length=1000)
    email_address: str
    folder_name: str = Field(..., min_length=1)
    filter_rules: List[FilterRule] = []
    poll_interval_seconds: int = Field(5, ge=5)


class UpdateEmailConfigRequest(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = Field(None, max_length=1000)
    filter_rules: Optional[List[FilterRule]] = None
    poll_interval_seconds: Optional[int] = Field(None, ge=5)


class DiscoverEmailAccountsResponse(BaseModel):
    accounts: List[EmailAccount]


class DiscoverEmailFoldersResponse(BaseModel):
    folders: List[EmailFolder]


class ValidateEmailConfigRequest(BaseModel):
    email_address: str
    folder_name: str

class ValidateEmailConfigResponse(BaseModel):
    email_address: str
    folder_name: str
    message: str
