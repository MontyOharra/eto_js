"""
Email domain types
Dataclasses for email records stored in database.

Deduplication is per-account (not per-config) so emails moved between
folders on the same account are not re-processed.
"""
from dataclasses import dataclass
from datetime import datetime
from typing import Optional


@dataclass(frozen=True)
class Email:
    """
    Full email record (database record).
    Represents an email that has been received and processed.
    Used by services and repositories for complete email data.
    """
    id: int
    account_id: int  # FK to email_accounts (for deduplication)
    ingestion_config_id: Optional[int]  # FK to email_ingestion_configs (which config first ingested)
    message_id: str
    sender_email: str
    subject: str
    received_date: datetime
    folder_name: str
    has_pdf_attachments: bool
    attachment_count: int
    pdf_count: int
    processed_at: Optional[datetime]
    created_at: datetime


@dataclass(frozen=True)
class EmailCreate:
    """
    Data for creating a new email record.
    Used when storing processed emails for deduplication tracking.
    """
    account_id: int  # FK to email_accounts (required for deduplication)
    ingestion_config_id: int  # FK to email_ingestion_configs (which config ingested)
    message_id: str
    sender_email: str
    sender_name: Optional[str]
    subject: str
    received_date: datetime
    folder_name: str
    has_pdf_attachments: bool = False
    attachment_count: int = 0
    pdf_count: int = 0
