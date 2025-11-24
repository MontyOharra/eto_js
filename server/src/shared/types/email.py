"""
Email domain types
Dataclasses for email records stored in database
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
    config_id: Optional[int]
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
    config_id: int
    message_id: str
    sender_email: str
    subject: str
    received_date: datetime
    folder_name: str
