"""
Base Repository
Abstract base class providing common CRUD operations for all repositories
Supports dual-mode operation: standalone (via connection_manager) or transactional (via session)
"""
import logging
from abc import ABC, abstractmethod
from typing import Optional, Any, Type, TypeVar, Generic, Protocol
from contextlib import contextmanager
from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError

from shared.database.connection import DatabaseConnectionManager

logger = logging.getLogger(__name__)



class HasId(Protocol):
    """Protocol for models that have an id attribute"""
    id: Any


ModelType = TypeVar('ModelType', bound=HasId)


class BaseRepository(ABC, Generic[ModelType]):
    """
    Abstract base repository providing common CRUD operations.

    Supports dual-mode operation:
    - Standalone mode: Uses connection_manager to create sessions per operation
    - Transaction mode: Uses provided session (from Unit of Work)

    All concrete repositories should inherit from this class and implement model_class.
    """

    def __init__(
        self,
        session: Optional[Session] = None,
        connection_manager: Optional[DatabaseConnectionManager] = None
    ):
        """
        Initialize repository.

        Args:
            session: If provided, use this session (we're in a UoW transaction)
            connection_manager: If no session, use this to create sessions per operation

        Note: Either session OR connection_manager must be provided (not both)

        Raises:
            ValueError: If neither or both parameters are provided
        """
        if session is None and connection_manager is None:
            raise ValueError("Must provide either session or connection_manager")

        if session is not None and connection_manager is not None:
            raise ValueError("Provide either session OR connection_manager, not both")

        self.session = session
        self.connection_manager = connection_manager
        self._owns_session = session is None

        mode = "transaction" if session else "standalone"
        logger.debug(f"Initialized {self.__class__.__name__} in {mode} mode")

    @property
    @abstractmethod
    def model_class(self) -> Type[ModelType]:
        """Return the SQLAlchemy model class this repository manages"""
        pass

    @contextmanager
    def _get_session(self):
        """
        Get session for an operation (internal helper).

        If we have a session (in UoW), use it without committing.
        Otherwise create a new session for this operation and commit after.

        This allows repository methods to have a single implementation
        that works both standalone and in transactions.

        Yields:
            Session: Session to use for database operations
        """
        if self.session:
            # We're in a UoW transaction - use the UoW's session
            # Don't commit - UoW will handle that
            yield self.session
        else:
            # Standalone operation - create our own session
            assert self.connection_manager is not None
            with self.connection_manager.session() as session:
                yield session
                # Session auto-commits on context exit