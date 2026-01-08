"""
ETO Sub-Run Pipeline Execution Step Repository
Repository for eto_sub_run_pipeline_execution_steps table with CRUD operations
"""
import logging

from shared.database.repositories.base import BaseRepository
from shared.database.models import EtoSubRunPipelineExecutionStepModel
from shared.types.eto_sub_run_pipeline_execution_steps import (
    EtoSubRunPipelineExecutionStep,
    EtoSubRunPipelineExecutionStepCreate,
    EtoSubRunPipelineExecutionStepUpdate,
)

logger = logging.getLogger(__name__)


class EtoSubRunPipelineExecutionStepRepository(BaseRepository[EtoSubRunPipelineExecutionStepModel]):
    """
    Repository for pipeline execution step CRUD operations.

    Handles:
    - Basic CRUD for eto_sub_run_pipeline_execution_steps table
    - Conversion between ORM models and domain dataclasses
    - Query operations (get by pipeline_execution_id, ordered steps)
    """

    @property
    def model_class(self) -> type[EtoSubRunPipelineExecutionStepModel]:
        """Return the SQLAlchemy model class this repository manages"""
        return EtoSubRunPipelineExecutionStepModel

    # ========== Conversion Methods ==========

    def _model_to_domain(self, model: EtoSubRunPipelineExecutionStepModel) -> EtoSubRunPipelineExecutionStep:
        """
        Convert ORM model to EtoSubRunPipelineExecutionStep dataclass.
        No enum conversions needed for this table.
        """
        return EtoSubRunPipelineExecutionStep(
            id=model.id,
            pipeline_execution_id=model.pipeline_execution_id,
            module_instance_id=model.module_instance_id,
            step_number=model.step_number,
            inputs=model.inputs,
            outputs=model.outputs,
            error=model.error,
            created_at=model.created_at,
            updated_at=model.updated_at,
        )

    # ========== CRUD Operations ==========

    def create(self, data: EtoSubRunPipelineExecutionStepCreate) -> EtoSubRunPipelineExecutionStep:
        """
        Create new pipeline execution step record.

        Args:
            data: EtoSubRunPipelineExecutionStepCreate with step details

        Returns:
            Created EtoSubRunPipelineExecutionStep dataclass
        """
        with self._get_session() as session:
            # Create model
            model = self.model_class(
                pipeline_execution_id=data.pipeline_execution_id,
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

    def get_by_id(self, record_id: int) -> EtoSubRunPipelineExecutionStep | None:
        """
        Get pipeline execution step record by ID.

        Args:
            record_id: Step record ID

        Returns:
            EtoSubRunPipelineExecutionStep dataclass or None if not found
        """
        with self._get_session() as session:
            model = session.get(self.model_class, record_id)

            if model is None:
                return None

            return self._model_to_domain(model)

    def update(self, record_id: int, updates: EtoSubRunPipelineExecutionStepUpdate) -> EtoSubRunPipelineExecutionStep | None:
        """
        Update pipeline execution step record. Only updates provided fields.

        Uses Pydantic's model_fields_set to distinguish between:
        - Field not provided: not in model_fields_set (don't update)
        - Field set to None: in model_fields_set with None value (set NULL)
        - Field set to value: in model_fields_set with value (update)

        Args:
            record_id: Step record ID
            updates: EtoSubRunPipelineExecutionStepUpdate with fields to update

        Returns:
            Updated EtoSubRunPipelineExecutionStep dataclass or None if not found
        """
        with self._get_session() as session:
            model = session.get(self.model_class, record_id)

            if model is None:
                return None

            # Update only fields that were explicitly set
            for field_name in updates.model_fields_set:
                value = getattr(updates, field_name)
                setattr(model, field_name, value)

            session.flush()  # Persist changes

            return self._model_to_domain(model)

    # ========== Query Operations ==========

    def get_by_pipeline_execution_id(self, pipeline_execution_id: int, ordered: bool = True) -> list[EtoSubRunPipelineExecutionStep]:
        """
        Get all pipeline execution steps for a specific pipeline execution.

        Args:
            pipeline_execution_id: Pipeline execution ID (FK to eto_sub_run_pipeline_executions.id)
            ordered: If True, order by step_number (default: True)

        Returns:
            List of EtoSubRunPipelineExecutionStep dataclasses
        """
        with self._get_session() as session:
            query = session.query(self.model_class).filter_by(pipeline_execution_id=pipeline_execution_id)

            if ordered:
                query = query.order_by(self.model_class.step_number.asc())

            models = query.all()

            return [self._model_to_domain(model) for model in models]

    def get_by_module_instance_id(self, module_instance_id: str) -> list[EtoSubRunPipelineExecutionStep]:
        """
        Get all steps for a specific module instance.
        Useful for debugging specific module executions across runs.

        Args:
            module_instance_id: Module instance identifier

        Returns:
            List of EtoSubRunPipelineExecutionStep dataclasses
        """
        with self._get_session() as session:
            models = (
                session.query(self.model_class)
                .filter_by(module_instance_id=module_instance_id)
                .order_by(self.model_class.created_at.desc())
                .all()
            )

            return [self._model_to_domain(model) for model in models]
