"""
Base Email Integration
Abstract base class for all email provider integrations using dataclass types
"""
from abc import ABC, abstractmethod
from typing import Optional
from datetime import datetime
import logging

from shared.types.email_integrations import (
    EmailMessage,
    EmailAttachment,
    EmailFolder,
    EmailAccount,
    EmailSearchCriteria,
    ConnectionTestResult,
)

logger = logging.getLogger(__name__)


class BaseEmailIntegration(ABC):
    """
    Abstract base class for all email integrations.
    Each provider (Outlook COM, Gmail API, etc.) implements this interface.

    Uses lightweight dataclass types for optimal performance in domain layer.
    """

    def __init__(self, **config):
        """
        Initialize integration with provider-specific configuration

        Args:
            **config: Configuration parameters (provider-specific)
        """
        self.config = config
        self.is_connected = False
        self.logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")

    # ========== Connection Management ==========

    @abstractmethod
    def connect(self) -> bool:
        """
        Establish connection to email provider

        Args:
            account_identifier: Optional account identifier (email address, account ID, etc.)
                               Used when provider supports multiple accounts

        Returns:
            True if connection successful

        Raises:
            ConnectionError: If unable to connect
        """
        pass

    @abstractmethod
    def disconnect(self) -> None:
        """
        Close connection to email provider and cleanup resources
        """
        pass

    @abstractmethod
    def test_connection(self) -> ConnectionTestResult:
        """
        Test if current connection is valid and active

        Returns:
            ConnectionTestResult dataclass with success status and details
        """
        pass

    # ========== Folder Operations ==========

    @abstractmethod
    def discover_folders(self) -> list[EmailFolder]:
        """
        Get list of all available folders in the email account

        Args:
            account_identifier: Optional account to get folders for

        Returns:
            List of EmailFolder dataclasses representing folder hierarchy
        """
        pass

    @abstractmethod
    def select_folder(self, folder_name: str) -> bool:
        """
        Select/focus a specific folder for operations

        Args:
            folder_name: Name or path of folder to select

        Returns:
            True if folder selected successfully
        """
        pass

    # ========== Email Retrieval ==========

    @abstractmethod
    def get_recent_emails(
        self,
        folder_name: str = "Inbox",
        since_datetime: Optional[datetime] = None,
        limit: int = 100,
        include_read: bool = True
    ) -> list[EmailMessage]:
        """
        Get recent emails from specified folder

        Args:
            folder_name: Folder to retrieve emails from
            since_datetime: Only get emails received after this time
            limit: Maximum number of emails to retrieve
            include_read: Whether to include already read emails

        Returns:
            List of EmailMessage dataclasses in standardized format
        """
        pass

    @abstractmethod
    def get_email_by_id(
        self,
        message_id: str,
        folder_name: str = "Inbox"
    ) -> Optional[EmailMessage]:
        """
        Get specific email by its message ID

        Args:
            message_id: Unique message identifier
            folder_name: Folder containing the email

        Returns:
            EmailMessage dataclass if found, None otherwise
        """
        pass

    def search_emails(self, criteria: EmailSearchCriteria) -> list[EmailMessage]:
        """
        Search emails based on criteria

        Args:
            criteria: EmailSearchCriteria dataclass with search parameters

        Returns:
            List of matching EmailMessage dataclasses

        Note:
            Default implementation uses get_recent_emails and filters.
            Providers can override for native search capabilities.
        """
        # Default implementation using filtering
        emails = self.get_recent_emails(
            folder_name=criteria.folder_name,
            since_datetime=criteria.date_from,
            limit=criteria.limit
        )

        # Apply filters
        filtered = []
        for email in emails:
            # Check all criteria
            if criteria.subject_contains and criteria.subject_contains.lower() not in email.subject.lower():
                continue
            if criteria.sender_email and email.sender_email.lower() != criteria.sender_email.lower():
                continue
            if criteria.date_to and email.received_date > criteria.date_to:
                continue
            if criteria.has_attachments is not None and email.has_attachments != criteria.has_attachments:
                continue
            if criteria.is_unread is not None and email.is_read == criteria.is_unread:
                continue

            filtered.append(email)

        return filtered[:criteria.limit]

    # ========== Attachment Operations ==========

    @abstractmethod
    def get_attachments(
        self,
        message_id: str,
        folder_name: str = "Inbox"
    ) -> list[EmailAttachment]:
        """
        Get all attachments from a specific email

        Args:
            message_id: Email message ID
            folder_name: Folder containing the email

        Returns:
            List of EmailAttachment dataclasses with content
        """
        pass

    def get_pdf_attachments(
        self,
        message_id: str,
        folder_name: str = "Inbox"
    ) -> list[EmailAttachment]:
        """
        Get only PDF attachments from email

        Args:
            message_id: Email message ID
            folder_name: Folder containing the email

        Returns:
            List of PDF EmailAttachment dataclasses
        """
        attachments = self.get_attachments(message_id, folder_name)
        return [
            a for a in attachments
            if a.content_type == "application/pdf" or a.filename.lower().endswith(".pdf")
        ]

    # ========== Email State Management ==========

    @abstractmethod
    def mark_as_read(self, message_id: str, folder_name: str = "Inbox") -> bool:
        """
        Mark email as read

        Args:
            message_id: Email message ID
            folder_name: Folder containing the email

        Returns:
            True if successfully marked as read
        """
        pass

    def mark_as_processed(self, message_id: str, folder_name: str = "Inbox") -> bool:
        """
        Mark email as processed (provider-specific implementation)
        Default: marks as read

        Args:
            message_id: Email message ID
            folder_name: Folder containing the email

        Returns:
            True if successfully marked
        """
        return self.mark_as_read(message_id, folder_name)

    # ========== Batch Operations ==========

    def get_emails_with_attachments(
        self,
        folder_name: str = "Inbox",
        since_datetime: Optional[datetime] = None,
        limit: int = 100
    ) -> list[tuple[EmailMessage, list[EmailAttachment]]]:
        """
        Get emails along with their attachments in one operation

        Args:
            folder_name: Folder to retrieve from
            since_datetime: Only get emails after this time
            limit: Maximum number of emails

        Returns:
            List of tuples (EmailMessage, List[EmailAttachment])
        """
        emails = self.get_recent_emails(folder_name, since_datetime, limit)
        result = []

        for email in emails:
            if email.has_attachments:
                try:
                    attachments = self.get_attachments(email.message_id, folder_name)
                    result.append((email, attachments))
                except Exception as e:
                    self.logger.warning(f"Failed to get attachments for {email.message_id}: {e}")
                    result.append((email, []))
            else:
                result.append((email, []))

        return result
