from dataclasses import dataclass, field
from datetime import datetime
from typing import Literal


@dataclass(frozen=True)
class FilterRule:
    field: Literal["sender_email", "subject", "has_attachments", "attachment_types"]
    operation: Literal["contains", "equals", "starts_with", "ends_with"]
    value: str
    case_sensitive: bool


@dataclass(frozen=True)
class EmailConfig:
    """
    Full email configuration (database record).
    Used by services and repositories for complete config data.
    """
    id: int
    name: str
    description: str | None
    email_address: str
    folder_name: str
    filter_rules: list[FilterRule]
    poll_interval_seconds: int
    is_active: bool
    activated_at: datetime | None
    last_check_time: datetime | None
    last_error_message: str | None
    last_error_at: datetime | None
    created_at: datetime
    updated_at: datetime


@dataclass(frozen=True)
class EmailConfigSummary:
    """
    Lightweight email configuration summary (for list operations).
    Used by list_configs_summary service method.
    """
    id: int
    name: str
    is_active: bool
    last_check_time: datetime | None


@dataclass(frozen=True)
class EmailConfigCreate:
    """
    Data for creating a new email configuration.
    Used by create_config service method.
    """
    name: str
    email_address: str
    folder_name: str
    description: str | None = None
    filter_rules: list[FilterRule] = field(default_factory=list)
    poll_interval_seconds: int = 5


@dataclass(frozen=True)
class EmailConfigUpdate:
    """
    Data for updating an email configuration.
    All fields are optional - only provided fields are updated.
    Used by update_config service method.
    """
    description: str | None = None
    filter_rules: list[FilterRule] | None = None
    poll_interval_seconds: int | None = None
    is_active: bool | None = None
    activated_at: datetime | None = None
    last_check_time: datetime | None = None
    last_error_message: str | None = None
    last_error_at: datetime | None = None