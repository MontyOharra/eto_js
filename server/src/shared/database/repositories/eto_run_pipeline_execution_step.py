"""
ETO Run Pipeline Execution Step Repository
Repository for eto_run_pipeline_execution_steps table with CRUD operations
"""
import logging
from typing import Type, Optional, List

from shared.database.repositories.base import BaseRepository
from shared.database.models import EtoRunPipelineExecutionStepModel
from shared.types.eto_run_pipeline_execution_steps import (
    EtoRunPipelineExecutionStep,
    EtoRunPipelineExecutionStepCreate,
    EtoRunPipelineExecutionStepUpdate,
)

logger = logging.getLogger(__name__)


class EtoRunPipelineExecutionStepRepository(BaseRepository[EtoRunPipelineExecutionStepModel]):
    """
    Repository for pipeline execution step CRUD operations.

    Handles:
    - Basic CRUD for eto_run_pipeline_execution_steps table
    - Conversion between ORM models and domain dataclasses
    - Query operations (get by run_id, ordered steps)
    """

    @property
    def model_class(self) -> Type[EtoRunPipelineExecutionStepModel]:
        """Return the SQLAlchemy model class this repository manages"""
        return EtoRunPipelineExecutionStepModel

    # ========== Conversion Methods ==========

    def _model_to_domain(self, model: EtoRunPipelineExecutionStepModel) -> EtoRunPipelineExecutionStep:
        """
        Convert ORM model to EtoRunPipelineExecutionStep dataclass.
        No enum conversions needed for this table.
        """
        return EtoRunPipelineExecutionStep(
            id=model.id,
            run_id=model.run_id,
            module_instance_id=model.module_instance_id,
            step_number=model.step_number,
            inputs=model.inputs,
            outputs=model.outputs,
            error=model.error,
            created_at=model.created_at,
            updated_at=model.updated_at,
        )

    # ========== CRUD Operations ==========

    def create(self, data: EtoRunPipelineExecutionStepCreate) -> EtoRunPipelineExecutionStep:
        """
        Create new pipeline execution step record.

        Args:
            data: EtoRunPipelineExecutionStepCreate with step details

        Returns:
            Created EtoRunPipelineExecutionStep dataclass
        """
        with self._get_session() as session:
            # Create model
            model = self.model_class(
                run_id=data.run_id,
                module_instance_id=data.module_instance_id,
                step_number=data.step_number,
                inputs=data.inputs,
                outputs=data.outputs,
                error=data.error,
                # timestamps auto-set by server_default
            )

            session.add(model)
            session.flush()  # Get ID without committing

            return self._model_to_domain(model)

    def get_by_id(self, record_id: int) -> Optional[EtoRunPipelineExecutionStep]:
        """
        Get pipeline execution step record by ID.

        Args:
            record_id: Step record ID

        Returns:
            EtoRunPipelineExecutionStep dataclass or None if not found
        """
        with self._get_session() as session:
            model = session.get(self.model_class, record_id)

            if model is None:
                return None

            return self._model_to_domain(model)

    def update(self, record_id: int, data: EtoRunPipelineExecutionStepUpdate) -> Optional[EtoRunPipelineExecutionStep]:
        """
        Update pipeline execution step record. Only updates provided fields.

        Args:
            record_id: Step record ID
            data: EtoRunPipelineExecutionStepUpdate with fields to update (all optional)

        Returns:
            Updated EtoRunPipelineExecutionStep dataclass or None if not found
        """
        with self._get_session() as session:
            model = session.get(self.model_class, record_id)

            if model is None:
                return None

            # Update only provided fields
            if data.inputs is not None:
                model.inputs = data.inputs
            if data.outputs is not None:
                model.outputs = data.outputs
            if data.error is not None:
                model.error = data.error

            session.flush()  # Persist changes

            return self._model_to_domain(model)

    # ========== Query Operations ==========

    def get_by_run_id(self, run_id: int, ordered: bool = True) -> List[EtoRunPipelineExecutionStep]:
        """
        Get all pipeline execution steps for a specific pipeline execution run.

        Args:
            run_id: Pipeline execution run ID (FK to eto_run_pipeline_executions.id)
            ordered: If True, order by step_number (default: True)

        Returns:
            List of EtoRunPipelineExecutionStep dataclasses
        """
        with self._get_session() as session:
            query = session.query(self.model_class).filter_by(run_id=run_id)

            if ordered:
                query = query.order_by(self.model_class.step_number.asc())

            models = query.all()

            return [self._model_to_domain(model) for model in models]

    def get_by_module_instance_id(self, module_instance_id: str) -> List[EtoRunPipelineExecutionStep]:
        """
        Get all steps for a specific module instance.
        Useful for debugging specific module executions across runs.

        Args:
            module_instance_id: Module instance identifier

        Returns:
            List of EtoRunPipelineExecutionStep dataclasses
        """
        with self._get_session() as session:
            models = (
                session.query(self.model_class)
                .filter_by(module_instance_id=module_instance_id)
                .order_by(self.model_class.created_at.desc())
                .all()
            )

            return [self._model_to_domain(model) for model in models]
