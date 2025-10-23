"""
Unit of Work Pattern
Manages database transactions and provides repository access within a transaction context
"""
import logging
from typing import TYPE_CHECKING, Optional
from sqlalchemy.orm import Session

# Import repository classes (will be created)
# Using TYPE_CHECKING to avoid circular imports
if TYPE_CHECKING:
    from shared.database.repositories.email_config import EmailConfigRepository
    from shared.database.repositories.email import EmailRepository
    # Add other repositories as they're created

logger = logging.getLogger(__name__)


class UnitOfWork:
    """
    Unit of Work manages a database transaction and provides repository access.

    All repositories within this UoW share the same session, ensuring
    that operations are part of a single atomic transaction.

    Usage:
        with connection_manager.unit_of_work() as uow:
            config = uow.email_configs.create(config_data)
            email = uow.emails.create(email_data)
            # Both commit together automatically

    Repositories are lazy-loaded - only instantiated when accessed.
    """

    def __init__(self, session: Session):
        """
        Initialize Unit of Work with a session.

        Args:
            session: Session instance for this transaction
        """
        self.session = session

        # Lazy-loaded repository instances
        # These are created on first access via properties
        self._email_config_repository: Optional['EmailConfigRepository'] = None
        self._email_repository: Optional['EmailRepository'] = None
        # Add other repositories as needed

        logger.debug("UnitOfWork initialized")

    @property
    def email_configs(self) -> 'EmailConfigRepository':
        """
        Access to email config repository within this transaction.

        Returns:
            EmailConfigRepository instance using this UoW's session
        """
        if not self._email_config_repository:
            from shared.database.repositories.email_config import EmailConfigRepository
            self._email_config_repository = EmailConfigRepository(session=self.session)
            logger.debug("EmailConfigRepository loaded in UoW")
        return self._email_config_repository

    @property
    def emails(self) -> 'EmailRepository':
        """
        Access to email repository within this transaction.

        Returns:
            EmailRepository instance using this UoW's session
        """
        if not self._email_repository:
            from shared.database.repositories.email import EmailRepository
            self._email_repository = EmailRepository(session=self.session)
            logger.debug("EmailRepository loaded in UoW")
        return self._email_repository

    # ========== Transaction Control ==========
    # Usually not needed - context manager handles commit/rollback
    # These are provided for manual control if needed

    def commit(self):
        """
        Manually commit the transaction.

        Note: Usually not needed - the context manager commits automatically.
        """
        self.session.commit()
        logger.debug("UoW transaction committed manually")

    def rollback(self):
        """
        Manually rollback the transaction.

        Note: Usually not needed - the context manager rolls back on exception.
        """
        self.session.rollback()
        logger.debug("UoW transaction rolled back manually")
