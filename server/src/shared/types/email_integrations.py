"""
Email Integration Domain Types
Dataclass types for email integration layer - used by integrations, service, and processing.
"""
from dataclasses import dataclass, field


@dataclass(frozen=True)
class EmailMessage:
    """
    Email message returned from integration.

    Lightweight structure for email ingestion - contains only what we need
    for processing and tracking. Does NOT include attachment content
    to keep polling efficient.
    """
    uid: int  # IMAP UID or equivalent (required for tracking)
    message_id: str  # Email Message-ID header
    subject: str
    sender_email: str
    sender_name: str | None
    received_date: str  # ISO format datetime string
    folder_name: str
    body_text: str | None = None
    body_html: str | None = None
    has_attachments: bool = False
    attachment_count: int = 0
    attachment_filenames: list[str] | None = None


@dataclass(frozen=True)
class EmailAttachment:
    """
    Email attachment with content.

    Used when downloading attachments after filter rules have been applied.
    """
    filename: str
    content_type: str
    data: bytes  # Raw attachment content


@dataclass(frozen=True)
class ValidationResult:
    """
    Result of credential validation.

    Returned by validate_credentials() - contains success status,
    message.
    """
    success: bool
    message: str
    folder_count: int | None = None


@dataclass(frozen=True)
class SendEmailResult:
    """
    Result of sending an email.

    Returned by send_email() - contains success status and message.
    """
    success: bool
    message: str
