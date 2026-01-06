"""
Email Ingestion Config Types

Pydantic models for email ingestion listener configuration.
References email_accounts for credentials - this file only handles
ingestion-specific settings like folder, filters, polling, etc.
"""

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict


# =========================
# Literal Type Aliases
# =========================

FilterRuleField = Literal["sender_email", "subject", "has_attachments", "received_date"]
FilterRuleOperation = Literal["contains", "equals", "starts_with", "ends_with", "before", "after", "is"]


# =========================
# Filter Rules
# =========================

class FilterRule(BaseModel):
    """Rule for filtering which emails to process"""
    model_config = ConfigDict(frozen=True)

    field: FilterRuleField
    operation: FilterRuleOperation
    value: str
    case_sensitive: bool


# =========================
# Email Ingestion Config (full record)
# =========================

class EmailIngestionConfig(BaseModel):
    """
    Full email ingestion configuration from database.
    References an email_account for credentials.
    """
    model_config = ConfigDict(frozen=True)

    id: int
    name: str
    description: str | None
    account_id: int  # FK to email_accounts
    folder_name: str
    filter_rules: list[FilterRule]
    poll_interval_seconds: int
    use_idle: bool
    is_active: bool
    activated_at: datetime | None
    last_check_time: datetime | None
    last_processed_uid: int | None
    last_error_message: str | None
    last_error_at: datetime | None
    created_at: datetime
    updated_at: datetime


class EmailIngestionConfigSummary(BaseModel):
    """
    Lightweight ingestion config summary for list operations.
    """
    model_config = ConfigDict(frozen=True)

    id: int
    name: str
    account_id: int
    folder_name: str
    is_active: bool
    last_check_time: datetime | None


class EmailIngestionConfigWithAccount(BaseModel):
    """
    Ingestion config with related account info for display.
    Used when listing configs with account names.
    """
    model_config = ConfigDict(frozen=True)

    id: int
    name: str
    description: str | None
    account_id: int
    account_name: str
    account_email: str
    folder_name: str
    is_active: bool
    last_check_time: datetime | None
    last_error_message: str | None


# =========================
# Create/Update DTOs
# =========================

class EmailIngestionConfigCreate(BaseModel):
    """Data for creating a new ingestion config"""
    model_config = ConfigDict(frozen=True)

    name: str
    account_id: int
    folder_name: str
    description: str | None = None
    filter_rules: list[FilterRule] = []
    poll_interval_seconds: int = 60
    use_idle: bool = True


class EmailIngestionConfigUpdate(BaseModel):
    """
    Data for updating an ingestion config.

    Uses Pydantic's model_fields_set to distinguish between:
    - Field not provided: not in model_fields_set (don't update)
    - Field set to None: in model_fields_set with None value (set NULL)
    - Field set to value: in model_fields_set with value (update)
    """
    name: str | None = None
    description: str | None = None
    folder_name: str | None = None
    filter_rules: list[FilterRule] | None = None
    poll_interval_seconds: int | None = None
    use_idle: bool | None = None
    is_active: bool | None = None
    activated_at: datetime | None = None
    last_check_time: datetime | None = None
    last_processed_uid: int | None = None
    last_error_message: str | None = None
    last_error_at: datetime | None = None
