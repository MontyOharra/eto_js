"""
Email Repository
Repository for emails table with create and query operations.

Supports deduplication by checking if a message_id already exists for an account.
"""
import logging
from datetime import datetime, timezone
from typing import Type

from shared.database.repositories.base import BaseRepository
from shared.database.models import EmailModel
from shared.types.email import Email, EmailCreate

logger = logging.getLogger(__name__)


class EmailRepository(BaseRepository[EmailModel]):
    """
    Repository for email record operations.

    Supports dual-mode operation:
    - Standalone: Pass connection_manager, auto-commits
    - UoW: Pass session, caller controls transaction

    Key method for deduplication: exists_for_account(account_id, message_id)
    """

    @property
    def model_class(self) -> Type[EmailModel]:
        """Return the SQLAlchemy model class this repository manages"""
        return EmailModel

    # ========== Helper Methods ==========

    def _model_to_dataclass(self, model: EmailModel) -> Email:
        """Convert ORM model to Email dataclass"""
        return Email(
            id=model.id,
            account_id=model.account_id,
            ingestion_config_id=model.ingestion_config_id,
            message_id=model.message_id,
            sender_email=model.sender_email or "",
            subject=model.subject or "",
            received_date=model.received_date or datetime.now(timezone.utc),
            folder_name=model.folder_name or "",
            has_pdf_attachments=model.has_pdf_attachments,
            attachment_count=model.attachment_count,
            pdf_count=model.pdf_count,
            processed_at=model.processed_at,
            created_at=model.created_at,
        )

    # ========== Deduplication Methods ==========

    def exists_for_account(self, account_id: int, message_id: str) -> bool:
        """
        Check if an email with this message_id already exists for the account.

        This is the primary deduplication check - prevents re-processing
        emails that have been moved between folders on the same account.

        Args:
            account_id: Email account ID
            message_id: Email Message-ID header

        Returns:
            True if email already exists, False otherwise
        """
        if not message_id:
            return False

        with self._get_session() as session:
            exists = session.query(self.model_class).filter(
                self.model_class.account_id == account_id,
                self.model_class.message_id == message_id,
            ).first() is not None

            return exists

    def get_existing_message_ids(self, account_id: int, message_ids: list[str]) -> set[str]:
        """
        Batch check which message_ids already exist for an account.

        More efficient than calling exists_for_account() in a loop.

        Args:
            account_id: Email account ID
            message_ids: List of Message-ID headers to check

        Returns:
            Set of message_ids that already exist
        """
        if not message_ids:
            return set()

        with self._get_session() as session:
            existing = session.query(self.model_class.message_id).filter(
                self.model_class.account_id == account_id,
                self.model_class.message_id.in_(message_ids),
            ).all()

            return {row[0] for row in existing}

    # ========== Query Methods ==========

    def get_by_id(self, email_id: int) -> Email | None:
        """
        Get email record by ID.

        Args:
            email_id: Email record ID

        Returns:
            Email dataclass or None if not found
        """
        with self._get_session() as session:
            model = session.query(self.model_class).filter(
                self.model_class.id == email_id
            ).first()

            if model is None:
                return None

            return self._model_to_dataclass(model)

    def get_by_account_and_message_id(self, account_id: int, message_id: str) -> Email | None:
        """
        Get email record by account and message_id.

        Args:
            account_id: Email account ID
            message_id: Email Message-ID header

        Returns:
            Email dataclass or None if not found
        """
        if not message_id:
            return None

        with self._get_session() as session:
            model = session.query(self.model_class).filter(
                self.model_class.account_id == account_id,
                self.model_class.message_id == message_id,
            ).first()

            if model is None:
                return None

            return self._model_to_dataclass(model)

    # ========== Create Methods ==========

    def create(self, email_data: EmailCreate) -> Email:
        """
        Create new email record.

        Args:
            email_data: EmailCreate dataclass with email data

        Returns:
            Created Email dataclass
        """
        with self._get_session() as session:
            now = datetime.now(timezone.utc)

            model = self.model_class(
                account_id=email_data.account_id,
                ingestion_config_id=email_data.ingestion_config_id,
                message_id=email_data.message_id,
                sender_email=email_data.sender_email,
                sender_name=email_data.sender_name,
                subject=email_data.subject,
                received_date=email_data.received_date,
                folder_name=email_data.folder_name,
                has_pdf_attachments=email_data.has_pdf_attachments,
                attachment_count=email_data.attachment_count,
                pdf_count=email_data.pdf_count,
                processed_at=now,
            )

            session.add(model)
            session.flush()  # Get ID assigned

            logger.info(
                f"Created email record {model.id} for account {email_data.account_id}: "
                f"{email_data.message_id[:50]}..."
            )

            return self._model_to_dataclass(model)
