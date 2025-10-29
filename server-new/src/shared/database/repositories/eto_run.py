"""
ETO Run Repository
Repository for eto_runs table with CRUD operations
"""
import logging
from typing import Type, Optional, List
from datetime import datetime

from shared.database.repositories.base import BaseRepository
from shared.database.models import EtoRunModel
from shared.types.eto_runs import (
    EtoRun,
    EtoRunCreate,
    EtoRunUpdate,
    EtoRunStatus,
    EtoProcessingStep,
)

logger = logging.getLogger(__name__)


class EtoRunRepository(BaseRepository[EtoRunModel]):
    """
    Repository for ETO run CRUD operations.

    Handles:
    - Basic CRUD for eto_runs table
    - Conversion between ORM models and domain dataclasses
    - Query operations for worker (finding not_started runs)

    Note: Stage-specific data managed by separate repositories:
    - EtoRunTemplateMatchingRepository
    - EtoRunExtractionRepository
    - EtoRunPipelineExecutionRepository
    """

    @property
    def model_class(self) -> Type[EtoRunModel]:
        """Return the SQLAlchemy model class this repository manages"""
        return EtoRunModel

    # ========== Conversion Methods ==========

    def _model_to_domain(self, model: EtoRunModel) -> EtoRun:
        """
        Convert ORM model to EtoRun dataclass.

        Handles enum to string conversion:
        - model.status (EtoRunStatus enum) -> dataclass (string literal)
        - model.processing_step (EtoRunProcessingStep enum) -> dataclass (string literal)
        """
        return EtoRun(
            id=model.id,
            pdf_file_id=model.pdf_file_id,
            status=model.status.value,  # Enum to string
            processing_step=model.processing_step.value if model.processing_step else None,  # Enum to string
            error_type=model.error_type,
            error_message=model.error_message,
            error_details=model.error_details,
            started_at=model.started_at,
            completed_at=model.completed_at,
            created_at=model.created_at,
            updated_at=model.updated_at,
        )

    # ========== CRUD Operations ==========

    def create(self, data: EtoRunCreate) -> EtoRun:
        """
        Create new ETO run with status = "not_started".

        Args:
            data: EtoRunCreate with pdf_file_id

        Returns:
            Created EtoRun dataclass
        """
        with self._get_session() as session:
            # Create model with defaults
            model = self.model_class(
                pdf_file_id=data.pdf_file_id,
                # status defaults to NOT_STARTED via model default
                # processing_step defaults to None
                # timestamps auto-set by server_default
            )

            session.add(model)
            session.flush()  # Get ID without committing

            return self._model_to_domain(model)

    def get_by_id(self, run_id: int) -> Optional[EtoRun]:
        """
        Get ETO run by ID.

        Args:
            run_id: ETO run ID

        Returns:
            EtoRun dataclass or None if not found
        """
        with self._get_session() as session:
            model = session.get(self.model_class, run_id)

            if model is None:
                return None

            return self._model_to_domain(model)

    def update(self, run_id: int, data: EtoRunUpdate) -> Optional[EtoRun]:
        """
        Update ETO run. Only updates provided fields.

        Args:
            run_id: ETO run ID
            data: EtoRunUpdate with fields to update (all optional)

        Returns:
            Updated EtoRun dataclass or None if not found
        """
        with self._get_session() as session:
            model = session.get(self.model_class, run_id)

            if model is None:
                return None

            # Update only provided fields
            if data.status is not None:
                model.status = data.status  # SQLAlchemy will convert string to enum type: ignore    # type: ignore
            if data.processing_step is not None:
                model.processing_step = data.processing_step  # SQLAlchemy will convert string to enum # type: ignore
            if data.error_type is not None:
                model.error_type = data.error_type
            if data.error_message is not None:
                model.error_message = data.error_message
            if data.error_details is not None:
                model.error_details = data.error_details
            if data.started_at is not None:
                model.started_at = data.started_at
            if data.completed_at is not None:
                model.completed_at = data.completed_at

            session.flush()  # Persist changes

            return self._model_to_domain(model)

    # ========== Query Operations ==========

    def get_by_status(self, status: EtoRunStatus, limit: Optional[int] = None) -> List[EtoRun]:
        """
        Get ETO runs by status.
        Used by worker to find runs that need processing.

        Args:
            status: Status to filter by (e.g., "not_started")
            limit: Optional limit on number of results

        Returns:
            List of EtoRun dataclasses
        """
        with self._get_session() as session:
            query = session.query(self.model_class).filter_by(status=status)

            if limit:
                query = query.limit(limit)

            models = query.all()

            return [self._model_to_domain(model) for model in models]
