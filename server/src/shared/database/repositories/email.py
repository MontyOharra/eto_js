"""
Email Repository
Repository for emails table with create and query operations
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
            ingestion_config_id=model.ingestion_config_id,
            message_id=model.message_id,
            sender_email=model.sender_email or "",  # Ensure not None
            subject=model.subject or "",  # Ensure not None
            received_date=model.received_date or datetime.now(timezone.utc),  # Ensure not None
            folder_name=model.folder_name or "",  # Ensure not None
            processed_at=model.processed_at or datetime.now(timezone.utc),  # Ensure not None
            created_at=model.created_at,
        )

    # ========== Public Repository Methods ==========

    def get_by_message_id(self, message_id: str) -> Email | None:
        """
        Get email record by message_id (for duplicate detection).

        Args:
            message_id: Email message ID from email provider

        Returns:
            Email dataclass or None if not found
        """
        if not message_id:
            return None

        with self._get_session() as session:
            model = session.query(self.model_class).filter(
                self.model_class.message_id == message_id
            ).first()

            if model is None:
                return None

            return self._model_to_dataclass(model)

    def create(self, email_data: EmailCreate) -> Email:
        """
        Create new email record.

        Args:
            email_data: EmailCreate dataclass with email data

        Returns:
            Created Email dataclass
        """
        with self._get_session() as session:
            # Create ORM model
            now = datetime.now(timezone.utc)

            model = self.model_class(
                ingestion_config_id=email_data.ingestion_config_id,
                message_id=email_data.message_id,
                sender_email=email_data.sender_email,
                subject=email_data.subject,
                received_date=email_data.received_date,
                folder_name=email_data.folder_name,
                processed_at=now,
                # Additional fields not in EmailCreate use defaults
                has_pdf_attachments=False,
                attachment_count=0,
                pdf_count=0,
            )

            session.add(model)
            session.flush()  # Get ID assigned

            logger.info(
                f"Created email record {model.id} for ingestion config {email_data.ingestion_config_id}: "
                f"{email_data.message_id}"
            )

            return self._model_to_dataclass(model)
