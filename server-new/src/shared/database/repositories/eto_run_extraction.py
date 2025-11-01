"""
ETO Run Extraction Repository
Repository for eto_run_extractions table with CRUD operations
"""
import logging
from typing import Type, Optional, List

from shared.database.repositories.base import BaseRepository
from shared.database.models import EtoRunExtractionModel
from shared.types.eto_run_extractions import (
    EtoRunExtraction,
    EtoRunExtractionCreate,
    EtoRunExtractionUpdate,
    EtoStepStatus,
)

logger = logging.getLogger(__name__)


class EtoRunExtractionRepository(BaseRepository[EtoRunExtractionModel]):
    """
    Repository for ETO extraction run CRUD operations.

    Handles:
    - Basic CRUD for eto_run_extractions table
    - Conversion between ORM models and domain dataclasses
    - Query operations for finding extractions by run ID and status

    Manages Stage 2 (Data Extraction) of ETO processing workflow.
    """

    @property
    def model_class(self) -> Type[EtoRunExtractionModel]:
        """Return the SQLAlchemy model class this repository manages"""
        return EtoRunExtractionModel

    # ========== Conversion Methods ==========

    def _model_to_domain(self, model: EtoRunExtractionModel) -> EtoRunExtraction:
        """
        Convert ORM model to EtoRunExtraction dataclass.

        Status field is plain string (no enum conversion needed).
        """
        return EtoRunExtraction(
            id=model.id,
            eto_run_id=model.eto_run_id,
            status=model.status,
            extracted_data=model.extracted_data,
            started_at=model.started_at,
            completed_at=model.completed_at,
            created_at=model.created_at,
            updated_at=model.updated_at,
        )

    # ========== CRUD Operations ==========

    def create(self, data: EtoRunExtractionCreate) -> EtoRunExtraction:
        """
        Create new extraction run with status = "processing".

        Args:
            data: EtoRunExtractionCreate with eto_run_id

        Returns:
            Created EtoRunExtraction dataclass
        """
        with self._get_session() as session:
            # Create model with defaults
            model = self.model_class(
                eto_run_id=data.eto_run_id,
                # status defaults to PROCESSING via model default
                # extracted_data starts as None
                # timestamps auto-set by server_default
            )

            session.add(model)
            session.flush()  # Get ID without committing

            return self._model_to_domain(model)

    def get_by_id(self, extraction_id: int) -> Optional[EtoRunExtraction]:
        """
        Get extraction run by ID.

        Args:
            extraction_id: Extraction run ID

        Returns:
            EtoRunExtraction dataclass or None if not found
        """
        with self._get_session() as session:
            model = session.get(self.model_class, extraction_id)

            if model is None:
                return None

            return self._model_to_domain(model)

    def update(self, extraction_id: int, data: EtoRunExtractionUpdate) -> Optional[EtoRunExtraction]:
        """
        Update extraction run. Only updates provided fields.

        Args:
            extraction_id: Extraction run ID
            data: EtoRunExtractionUpdate with fields to update (all optional)

        Returns:
            Updated EtoRunExtraction dataclass or None if not found
        """
        with self._get_session() as session:
            model = session.get(self.model_class, extraction_id)

            if model is None:
                return None

            # Update only provided fields
            if data.status is not None:
                model.status = data.status
            if data.extracted_data is not None:
                model.extracted_data = data.extracted_data
            if data.started_at is not None:
                model.started_at = data.started_at
            if data.completed_at is not None:
                model.completed_at = data.completed_at

            session.flush()  # Persist changes

            return self._model_to_domain(model)

    # ========== Query Operations ==========

    def get_by_eto_run_id(self, eto_run_id: int) -> Optional[EtoRunExtraction]:
        """
        Get extraction run by ETO run ID.
        Each ETO run should have at most one extraction record.

        Args:
            eto_run_id: ETO run ID

        Returns:
            EtoRunExtraction dataclass or None if not found
        """
        with self._get_session() as session:
            model = session.query(self.model_class).filter_by(eto_run_id=eto_run_id).first()

            if model is None:
                return None

            return self._model_to_domain(model)

    def get_by_status(self, status: EtoStepStatus, limit: Optional[int] = None) -> List[EtoRunExtraction]:
        """
        Get extraction runs by status.
        Useful for monitoring/debugging extraction processing.

        Args:
            status: Status to filter by (e.g., "processing", "success", "failure")
            limit: Optional limit on number of results

        Returns:
            List of EtoRunExtraction dataclasses
        """
        with self._get_session() as session:
            query = session.query(self.model_class).filter_by(status=status)

            if limit:
                query = query.limit(limit)

            models = query.all()

            return [self._model_to_domain(model) for model in models]

    def delete(self, extraction_id: int) -> bool:
        """
        Delete extraction record by ID.

        Args:
            extraction_id: Extraction record ID

        Returns:
            True if deleted, False if not found
        """
        with self._get_session() as session:
            model = session.get(self.model_class, extraction_id)

            if model is None:
                return False

            session.delete(model)
            session.flush()  # Persist deletion

            logger.debug(f"Deleted extraction record {extraction_id}")
            return True
