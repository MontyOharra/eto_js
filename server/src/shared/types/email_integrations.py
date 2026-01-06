"""
Email Integration Domain Types
Pydantic models for email integration layer - used by integrations, service, and processing.
"""
from pydantic import BaseModel, ConfigDict


class EmailMessage(BaseModel):
    """
    Email message returned from integration.

    Lightweight structure for email ingestion - contains only what we need
    for processing and tracking. Does NOT include attachment content
    to keep polling efficient.
    """
    model_config = ConfigDict(frozen=True)

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


class EmailAttachment(BaseModel):
    """
    Email attachment with content.

    Used when downloading attachments after filter rules have been applied.
    """
    model_config = ConfigDict(frozen=True)

    filename: str
    content_type: str
    data: bytes  # Raw attachment content


class ValidationResult(BaseModel):
    """
    Result of credential validation.

    Returned by validate_credentials() - contains success status,
    message.
    """
    model_config = ConfigDict(frozen=True)

    success: bool
    message: str
    folder_count: int | None = None


class SendEmailResult(BaseModel):
    """
    Result of sending an email.

    Returned by send_email() - contains success status and message.
    """
    model_config = ConfigDict(frozen=True)

    success: bool
    message: str
