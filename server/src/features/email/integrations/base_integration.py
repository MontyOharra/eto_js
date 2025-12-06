"""
Base Email Integration
Abstract base class for email provider integrations.
"""
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
import logging

logger = logging.getLogger(__name__)


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
    message, and any discovered capabilities.
    """
    success: bool
    message: str
    capabilities: list[str] = field(default_factory=list)
    folder_count: int | None = None


class BaseEmailIntegration(ABC):
    """
    Abstract base class for email integrations.

    Each provider (IMAP, Gmail API, etc.) implements this interface.
    The integration manages its own connection semantics internally:

    - For IMAP: Maintains persistent connection, handles reconnection
    - For REST APIs: Stateless, each method call is independent

    The service layer treats all integrations uniformly through this interface.
    """

    def __init__(self):
        """Initialize integration."""
        self.logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")

    # ========== Lifecycle Methods ==========

    @abstractmethod
    def startup(self) -> None:
        """
        Initialize the integration for persistent use.

        Called when the first ingestion config for this account is activated.

        For IMAP: Establishes connection, starts keepalive thread.
        For REST APIs: May validate tokens, or no-op if stateless.
        """
        pass

    @abstractmethod
    def shutdown(self) -> None:
        """
        Cleanup and close the integration.

        Called when the last ingestion config for this account is deactivated,
        or on server shutdown.

        For IMAP: Stops keepalive, closes connection.
        For REST APIs: No-op if stateless.
        """
        pass

    @abstractmethod
    def validate_credentials(self) -> ValidationResult:
        """
        Validate credentials without establishing persistent connection.

        Used during account creation to verify credentials work.
        Should connect, verify, and disconnect (transient).

        Returns:
            ValidationResult with success status, message, and capabilities
        """
        pass

    # ========== Folder Operations ==========

    @abstractmethod
    def list_folders(self) -> list[str]:
        """
        List all available folders/mailboxes.

        Returns:
            List of folder names/paths (e.g., ["INBOX", "INBOX.Sent", "INBOX.Drafts"])
        """
        pass

    # ========== Email Operations ==========

    @abstractmethod
    def get_emails_since_uid(
        self,
        folder_name: str,
        since_uid: int,
        limit: int = 100,
    ) -> list[EmailMessage]:
        """
        Get emails with UID greater than since_uid.

        This is the primary method for incremental email ingestion.
        Returns emails ordered by UID ascending (oldest first).

        Args:
            folder_name: Folder to retrieve emails from (e.g., "INBOX")
            since_uid: Only get emails with UID > this value.
                      Use 0 to get emails from the beginning.
            limit: Maximum number of emails to retrieve

        Returns:
            List of EmailMessage dataclasses with uid field populated,
            ordered by UID ascending (oldest first)
        """
        pass

    @abstractmethod
    def get_highest_uid(self, folder_name: str) -> int | None:
        """
        Get the highest UID in the folder.

        Used to initialize last_processed_uid for new configs
        (so we don't process historical emails).

        Args:
            folder_name: Folder to check

        Returns:
            Highest UID in folder, or None if folder is empty
        """
        pass

    @abstractmethod
    def get_attachments(
        self,
        folder_name: str,
        uid: int,
        file_extensions: list[str] | None = None,
    ) -> list[EmailAttachment]:
        """
        Download attachments for a specific email by UID.

        Called after filter rules have been applied, to fetch only
        attachments from emails that passed filtering.

        Args:
            folder_name: Folder containing the email
            uid: UID of the email
            file_extensions: Optional list of extensions to filter by (e.g., [".pdf"]).
                            Case-insensitive. If None, returns all attachments.

        Returns:
            List of EmailAttachment dataclasses with filename, content_type, and data
        """
        pass
