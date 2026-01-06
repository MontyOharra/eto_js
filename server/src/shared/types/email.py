"""
Email domain types
Pydantic models for email records stored in database.

Deduplication is per-account (not per-config) so emails moved between
folders on the same account are not re-processed.
"""
from datetime import datetime

from pydantic import BaseModel, ConfigDict


class Email(BaseModel):
    """
    Full email record (database record).
    Represents an email that has been received and processed.
    Used by services and repositories for complete email data.
    """
    model_config = ConfigDict(frozen=True)

    id: int
    account_id: int  # FK to email_accounts (for deduplication)
    ingestion_config_id: int | None  # FK to email_ingestion_configs (which config first ingested)
    message_id: str
    sender_email: str
    subject: str
    received_date: datetime
    folder_name: str
    has_pdf_attachments: bool
    attachment_count: int
    pdf_count: int
    processed_at: datetime | None
    created_at: datetime


class EmailCreate(BaseModel):
    """
    Data for creating a new email record.
    Used when storing processed emails for deduplication tracking.
    """
    model_config = ConfigDict(frozen=True)

    account_id: int  # FK to email_accounts (required for deduplication)
    ingestion_config_id: int  # FK to email_ingestion_configs (which config ingested)
    message_id: str
    sender_email: str
    sender_name: str | None
    subject: str
    received_date: datetime
    folder_name: str
    has_pdf_attachments: bool
    attachment_count: int
    pdf_count: int
