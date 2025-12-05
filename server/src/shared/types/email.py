"""
Email domain types
Dataclasses for email records stored in database.

References email_ingestion_configs for the listener that ingested the email.
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
    ingestion_config_id: Optional[int]  # FK to email_ingestion_configs
    message_id: str
    sender_email: str
    subject: str
    received_date: datetime
    folder_name: str
    processed_at: datetime
    created_at: datetime


@dataclass(frozen=True)
class EmailCreate:
    """
    Data for creating a new email record.
    Used by EmailIngestionService._process_email when storing emails.
    """
    ingestion_config_id: int  # FK to email_ingestion_configs
    message_id: str
    sender_email: str
    subject: str
    received_date: datetime
    folder_name: str
