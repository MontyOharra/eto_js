"""
Base Email Integration
Abstract base class for email provider integrations.
"""
from abc import ABC, abstractmethod
from dataclasses import dataclass
import logging

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class EmailMessage:
    """
    Email message returned from integration.

    Lightweight structure for email ingestion - contains only what we need
    for processing and tracking.
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


class BaseEmailIntegration(ABC):
    """
    Abstract base class for email integrations.

    Each provider (IMAP, Gmail API, etc.) implements this interface.
    Designed for persistent connections - connect once, perform many operations,
    disconnect when done.

    For IMAP: connect() opens a socket, disconnect() closes it.
    For REST APIs: connect() validates credentials, disconnect() is a no-op.
    """

    def __init__(self):
        """Initialize integration."""
        self.logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")

    @abstractmethod
    def connect(self) -> bool:
        """
        Establish connection to email provider.

        For socket-based protocols (IMAP): Opens connection and authenticates.
        For REST APIs: Validates that credentials/tokens are working.

        Returns:
            True if connection/validation successful, False otherwise.
        """
        pass

    @abstractmethod
    def disconnect(self) -> None:
        """
        Close connection and cleanup resources.

        For socket-based protocols (IMAP): Closes the socket.
        For REST APIs: No-op (stateless).
        """
        pass

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
