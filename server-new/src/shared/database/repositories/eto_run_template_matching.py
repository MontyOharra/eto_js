"""
ETO Run Template Matching Repository
Repository for eto_run_template_matchings table with CRUD operations
"""
import logging
from typing import Type, Optional, List

from shared.database.repositories.base import BaseRepository
from shared.database.models import EtoRunTemplateMatchingModel
from shared.types.eto_run_template_matchings import (
    EtoRunTemplateMatching,
    EtoRunTemplateMatchingCreate,
    EtoRunTemplateMatchingUpdate,
    EtoStepStatus,
)

logger = logging.getLogger(__name__)


class EtoRunTemplateMatchingRepository(BaseRepository[EtoRunTemplateMatchingModel]):
    """
    Repository for template matching stage CRUD operations.

    Handles:
    - Basic CRUD for eto_run_template_matchings table
    - Conversion between ORM models and domain dataclasses
    - Query operations (get by eto_run_id, status)
    """

    @property
    def model_class(self) -> Type[EtoRunTemplateMatchingModel]:
        """Return the SQLAlchemy model class this repository manages"""
        return EtoRunTemplateMatchingModel

    # ========== Conversion Methods ==========

    def _model_to_domain(self, model: EtoRunTemplateMatchingModel) -> EtoRunTemplateMatching:
        """
        Convert ORM model to EtoRunTemplateMatching dataclass.

        Handles enum to string conversion:
        - model.status (EtoStepStatus enum or str) -> dataclass (string literal)

        Note: With native_enum=False, SQLAlchemy may return string values instead of Enum instances
        """
        return EtoRunTemplateMatching(
            id=model.id,
            eto_run_id=model.eto_run_id,
            status=model.status,
            matched_template_version_id=model.matched_template_version_id,
            started_at=model.started_at,
            completed_at=model.completed_at,
            created_at=model.created_at,
            updated_at=model.updated_at,
        )

    # ========== CRUD Operations ==========

    def create(self, data: EtoRunTemplateMatchingCreate) -> EtoRunTemplateMatching:
        """
        Create new template matching record with status = "processing".

        Args:
            data: EtoRunTemplateMatchingCreate with eto_run_id

        Returns:
            Created EtoRunTemplateMatching dataclass
        """
        with self._get_session() as session:
            # Create model with defaults
            model = self.model_class(
                eto_run_id=data.eto_run_id,
                # status defaults to PROCESSING via model default
                # timestamps auto-set by server_default
            )

            session.add(model)
            session.flush()  # Get ID without committing

            return self._model_to_domain(model)

    def get_by_id(self, record_id: int) -> Optional[EtoRunTemplateMatching]:
        """
        Get template matching record by ID.

        Args:
            record_id: Template matching record ID

        Returns:
            EtoRunTemplateMatching dataclass or None if not found
        """
        with self._get_session() as session:
            model = session.get(self.model_class, record_id)

            if model is None:
                return None

            return self._model_to_domain(model)

    def update(self, record_id: int, data: EtoRunTemplateMatchingUpdate) -> Optional[EtoRunTemplateMatching]:
        """
        Update template matching record. Only updates provided fields.

        Args:
            record_id: Template matching record ID
            data: EtoRunTemplateMatchingUpdate with fields to update (all optional)

        Returns:
            Updated EtoRunTemplateMatching dataclass or None if not found
        """
        with self._get_session() as session:
            model = session.get(self.model_class, record_id)

            if model is None:
                return None

            # Update only provided fields
            if data.status is not None:
                model.status = data.status  # SQLAlchemy will convert string to enum # type: ignore
            if data.matched_template_version_id is not None:
                model.matched_template_version_id = data.matched_template_version_id
            if data.started_at is not None:
                model.started_at = data.started_at
            if data.completed_at is not None:
                model.completed_at = data.completed_at

            session.flush()  # Persist changes

            return self._model_to_domain(model)

    # ========== Query Operations ==========

    def get_by_eto_run_id(self, eto_run_id: int) -> Optional[EtoRunTemplateMatching]:
        """
        Get template matching record by ETO run ID.
        Returns the most recent record if multiple exist (should only be one).

        Args:
            eto_run_id: ETO run ID

        Returns:
            EtoRunTemplateMatching dataclass or None if not found
        """
        with self._get_session() as session:
            model = (
                session.query(self.model_class)
                .filter_by(eto_run_id=eto_run_id)
                .order_by(self.model_class.created_at.desc())
                .first()
            )

            if model is None:
                return None

            return self._model_to_domain(model)

    def get_by_status(self, status: EtoStepStatus, limit: Optional[int] = None) -> List[EtoRunTemplateMatching]:
        """
        Get template matching records by status.

        Args:
            status: Status to filter by (e.g., "processing", "success", "failure")
            limit: Optional limit on number of results

        Returns:
            List of EtoRunTemplateMatching dataclasses
        """
        with self._get_session() as session:
            query = session.query(self.model_class).filter_by(status=status)

            if limit:
                query = query.limit(limit)

            models = query.all()

            return [self._model_to_domain(model) for model in models]

    def get_by_run_ids(self, run_ids: List[int]) -> dict[int, EtoRunTemplateMatching]:
        """
        Batch fetch template matching records by ETO run IDs.
        Returns dict keyed by eto_run_id.

        Args:
            run_ids: List of ETO run IDs

        Returns:
            Dict mapping eto_run_id to EtoRunTemplateMatching
            (returns most recent if multiple records exist per run)
        """
        if not run_ids:
            return {}

        with self._get_session() as session:
            # Query all matching records
            models = (
                session.query(self.model_class)
                .filter(self.model_class.eto_run_id.in_(run_ids))
                .order_by(self.model_class.eto_run_id, self.model_class.created_at.desc())
                .all()
            )

            # Build dict, keeping only the most recent per run_id
            result = {}
            for model in models:
                if model.eto_run_id not in result:
                    result[model.eto_run_id] = self._model_to_domain(model)

            return result

    def delete(self, record_id: int) -> bool:
        """
        Delete template matching record by ID.

        Args:
            record_id: Template matching record ID

        Returns:
            True if deleted, False if not found
        """
        with self._get_session() as session:
            model = session.get(self.model_class, record_id)

            if model is None:
                return False

            session.delete(model)
            session.flush()  # Persist deletion

            logger.debug(f"Deleted template matching record {record_id}")
            return True
