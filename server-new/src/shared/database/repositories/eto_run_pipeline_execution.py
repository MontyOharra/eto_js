"""
ETO Run Pipeline Execution Repository
Repository for eto_run_pipeline_executions table with CRUD operations
"""
import logging
from typing import Type, Optional, List

from shared.database.repositories.base import BaseRepository
from shared.database.models import EtoRunPipelineExecutionModel
from shared.types.eto_run_pipeline_executions import (
    EtoRunPipelineExecution,
    EtoRunPipelineExecutionCreate,
    EtoRunPipelineExecutionUpdate,
)

logger = logging.getLogger(__name__)


class EtoRunPipelineExecutionRepository(BaseRepository[EtoRunPipelineExecutionModel]):
    """
    Repository for pipeline execution CRUD operations.

    Handles:
    - Basic CRUD for eto_run_pipeline_executions table
    - Conversion between ORM models and domain dataclasses
    - Query operations for finding executions by eto_run_id
    """

    @property
    def model_class(self) -> Type[EtoRunPipelineExecutionModel]:
        """Return the SQLAlchemy model class this repository manages"""
        return EtoRunPipelineExecutionModel

    # ========== Conversion Methods ==========

    def _model_to_domain(self, model: EtoRunPipelineExecutionModel) -> EtoRunPipelineExecution:
        """
        Convert ORM model to EtoRunPipelineExecution dataclass.

        Status field is plain string (no enum conversion needed).
        """
        return EtoRunPipelineExecution(
            id=model.id,
            eto_run_id=model.eto_run_id,
            status=model.status,
            executed_actions=model.executed_actions,
            started_at=model.started_at,
            completed_at=model.completed_at,
            created_at=model.created_at,
            updated_at=model.updated_at,
        )

    # ========== CRUD Operations ==========

    def create(self, data: EtoRunPipelineExecutionCreate) -> EtoRunPipelineExecution:
        """
        Create new pipeline execution record with status = "processing".

        Args:
            data: EtoRunPipelineExecutionCreate with eto_run_id

        Returns:
            Created EtoRunPipelineExecution dataclass
        """
        with self._get_session() as session:
            # Create model with defaults
            model = self.model_class(
                eto_run_id=data.eto_run_id,
                started_at=data.started_at,
                # status defaults to PROCESSING via model default
                # timestamps auto-set by server_default
            )

            session.add(model)
            session.flush()  # Get ID without committing

            return self._model_to_domain(model)

    def get_by_id(self, execution_id: int) -> Optional[EtoRunPipelineExecution]:
        """
        Get pipeline execution by ID.

        Args:
            execution_id: Pipeline execution ID

        Returns:
            EtoRunPipelineExecution dataclass or None if not found
        """
        with self._get_session() as session:
            model = session.get(self.model_class, execution_id)

            if model is None:
                return None

            return self._model_to_domain(model)

    def update(self, execution_id: int, data: EtoRunPipelineExecutionUpdate) -> Optional[EtoRunPipelineExecution]:
        """
        Update pipeline execution. Only updates provided fields.

        Args:
            execution_id: Pipeline execution ID
            data: EtoRunPipelineExecutionUpdate with fields to update (all optional)

        Returns:
            Updated EtoRunPipelineExecution dataclass or None if not found
        """
        with self._get_session() as session:
            model = session.get(self.model_class, execution_id)

            if model is None:
                return None

            # Update only provided fields
            if data.status is not None:
                model.status = data.status
            if data.executed_actions is not None:
                model.executed_actions = data.executed_actions
            if data.completed_at is not None:
                model.completed_at = data.completed_at

            session.flush()  # Persist changes

            return self._model_to_domain(model)

    # ========== Query Operations ==========

    def get_by_eto_run_id(self, eto_run_id: int) -> Optional[EtoRunPipelineExecution]:
        """
        Get pipeline execution by ETO run ID.
        Expects only one pipeline execution per ETO run.

        Args:
            eto_run_id: ETO run ID

        Returns:
            EtoRunPipelineExecution dataclass or None if not found
        """
        with self._get_session() as session:
            model = session.query(self.model_class).filter_by(eto_run_id=eto_run_id).first()

            if model is None:
                return None

            return self._model_to_domain(model)

    def get_by_status(self, status: str, limit: Optional[int] = None) -> List[EtoRunPipelineExecution]:
        """
        Get pipeline executions by status.

        Args:
            status: Status to filter by (e.g., "processing", "success", "failure")
            limit: Optional limit on number of results

        Returns:
            List of EtoRunPipelineExecution dataclasses
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
