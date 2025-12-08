"""
ETO Sub-Run Pipeline Execution Repository
Repository for eto_sub_run_pipeline_executions table with CRUD operations
"""
import logging
from typing import Type, Optional, List

from shared.database.repositories.base import BaseRepository
from shared.database.models import EtoSubRunPipelineExecutionModel
from shared.types.eto_sub_run_pipeline_executions import (
    EtoSubRunPipelineExecution,
    EtoSubRunPipelineExecutionCreate,
    EtoSubRunPipelineExecutionUpdate,
)

logger = logging.getLogger(__name__)


class EtoSubRunPipelineExecutionRepository(BaseRepository[EtoSubRunPipelineExecutionModel]):
    """
    Repository for sub-run pipeline execution CRUD operations.

    Handles:
    - Basic CRUD for eto_sub_run_pipeline_executions table
    - Conversion between ORM models and domain dataclasses
    - Query operations for finding executions by sub_run_id

    Manages pipeline execution stage for individual sub-runs.
    """

    @property
    def model_class(self) -> Type[EtoSubRunPipelineExecutionModel]:
        """Return the SQLAlchemy model class this repository manages"""
        return EtoSubRunPipelineExecutionModel

    # ========== Conversion Methods ==========

    def _model_to_domain(self, model: EtoSubRunPipelineExecutionModel) -> EtoSubRunPipelineExecution:
        """
        Convert ORM model to EtoSubRunPipelineExecution dataclass.

        Status field is plain string (no enum conversion needed).
        """
        return EtoSubRunPipelineExecution(
            id=model.id,
            sub_run_id=model.sub_run_id,
            status=model.status,
            error_message=model.error_message,
            transformed_data=model.transformed_data,
            started_at=model.started_at,
            completed_at=model.completed_at,
            created_at=model.created_at,
            updated_at=model.updated_at,
        )

    # ========== CRUD Operations ==========

    def create(self, data: EtoSubRunPipelineExecutionCreate) -> EtoSubRunPipelineExecution:
        """
        Create new pipeline execution record with status = "processing".

        Args:
            data: EtoSubRunPipelineExecutionCreate with sub_run_id

        Returns:
            Created EtoSubRunPipelineExecution dataclass
        """
        with self._get_session() as session:
            # Create model with defaults
            model = self.model_class(
                sub_run_id=data.sub_run_id,
                started_at=data.started_at,
                # status defaults to PROCESSING via model default
                # timestamps auto-set by server_default
            )

            session.add(model)
            session.flush()  # Get ID without committing

            return self._model_to_domain(model)

    def get_by_id(self, execution_id: int) -> Optional[EtoSubRunPipelineExecution]:
        """
        Get pipeline execution by ID.

        Args:
            execution_id: Pipeline execution ID

        Returns:
            EtoSubRunPipelineExecution dataclass or None if not found
        """
        with self._get_session() as session:
            model = session.get(self.model_class, execution_id)

            if model is None:
                return None

            return self._model_to_domain(model)

    def update(self, execution_id: int, updates: EtoSubRunPipelineExecutionUpdate) -> Optional[EtoSubRunPipelineExecution]:
        """
        Update pipeline execution. Only updates provided fields.

        Uses dict keys to distinguish between:
        - Field not provided (key absent) - field will not be updated
        - Field explicitly set to None (key present, value None) - field will be cleared in database
        - Field set to value (key present) - field will be updated to that value

        Args:
            execution_id: Pipeline execution ID
            updates: Dict of fields to update (TypedDict with all fields optional)

        Returns:
            Updated EtoSubRunPipelineExecution dataclass or None if not found

        Raises:
            ValueError: If invalid field name provided
        """
        with self._get_session() as session:
            model = session.get(self.model_class, execution_id)

            if model is None:
                return None

            # Update only provided fields (iterate over dict keys)
            for field, value in updates.items():
                if not hasattr(model, field):
                    raise ValueError(f"Invalid field for pipeline execution update: {field}")
                setattr(model, field, value)

            session.flush()  # Persist changes

            return self._model_to_domain(model)

    # ========== Query Operations ==========

    def get_by_sub_run_id(self, sub_run_id: int) -> Optional[EtoSubRunPipelineExecution]:
        """
        Get pipeline execution by sub-run ID.
        Each sub-run should have at most one pipeline execution record.

        Args:
            sub_run_id: Sub-run ID

        Returns:
            EtoSubRunPipelineExecution dataclass or None if not found
        """
        with self._get_session() as session:
            model = session.query(self.model_class).filter_by(sub_run_id=sub_run_id).first()

            if model is None:
                return None

            return self._model_to_domain(model)

    def get_by_status(self, status: str, limit: Optional[int] = None) -> List[EtoSubRunPipelineExecution]:
        """
        Get pipeline executions by status.
        Useful for monitoring/debugging pipeline processing.

        Args:
            status: Status to filter by (e.g., "processing", "success", "failure")
            limit: Optional limit on number of results

        Returns:
            List of EtoSubRunPipelineExecution dataclasses
        """
        with self._get_session() as session:
            query = session.query(self.model_class).filter_by(status=status)

            if limit:
                query = query.limit(limit)

            models = query.all()

            return [self._model_to_domain(model) for model in models]

    def delete(self, execution_id: int) -> bool:
        """
        Delete pipeline execution record by ID.
        Note: Cascade delete should handle related step records.

        Args:
            execution_id: Pipeline execution record ID

        Returns:
            True if deleted, False if not found
        """
        with self._get_session() as session:
            model = session.get(self.model_class, execution_id)

            if model is None:
                return False

            session.delete(model)
            session.flush()  # Persist deletion

            logger.debug(f"Deleted pipeline execution record {execution_id}")
            return True
