"""
ETO Run Pipeline Execution Step Repository
Repository for eto_run_pipeline_execution_steps table with CRUD operations
"""
import json
import logging
from typing import Type, List, Optional, Dict, Any
from sqlalchemy import select

from shared.database.repositories.base import BaseRepository
from shared.database.models import EtoRunPipelineExecutionStepModel
from shared.types.pipeline_execution import (
    PipelineExecutionStep,
    PipelineExecutionStepCreate,
)

logger = logging.getLogger(__name__)


class EtoRunPipelineExecutionStepRepository(BaseRepository[EtoRunPipelineExecutionStepModel]):
    """
    Repository for Pipeline Execution Step CRUD operations.

    Supports dual-mode operation:
    - Standalone: Pass connection_manager, auto-commits
    - UoW: Pass session, caller controls transaction

    This table stores audit trail of module executions during pipeline runs.
    Each step records inputs, outputs, and any errors that occurred.
    """

    @property
    def model_class(self) -> Type[EtoRunPipelineExecutionStepModel]:
        """Return the SQLAlchemy model class this repository manages"""
        return EtoRunPipelineExecutionStepModel

    def _serialize_io(self, io_dict: Dict[str, Dict[str, Any]]) -> str:
        """
        Convert inputs/outputs dict to JSON string for database storage.

        Args:
            io_dict: Dict in format {node_name: {value, type}}

        Returns:
            JSON string representation
        """
        return json.dumps(io_dict)

    def _deserialize_io(self, json_str: Optional[str]) -> Dict[str, Dict[str, Any]]:
        """
        Convert JSON string to inputs/outputs dict.

        Args:
            json_str: JSON string from database (or None)

        Returns:
            Dict in format {node_name: {value, type}} or empty dict if None
        """
        if json_str is None:
            return {}

        return json.loads(json_str)

    def _model_to_domain(self, model: EtoRunPipelineExecutionStepModel) -> PipelineExecutionStep:
        """Convert ORM model to PipelineExecutionStep dataclass"""
        return PipelineExecutionStep(
            id=model.id,
            run_id=model.run_id,
            module_instance_id=model.module_instance_id,
            step_number=model.step_number,
            inputs=self._deserialize_io(model.inputs),
            outputs=self._deserialize_io(model.outputs),
            error=model.error,
            created_at=model.created_at,
            updated_at=model.updated_at,
        )

    def create(self, data: PipelineExecutionStepCreate) -> PipelineExecutionStep:
        """
        Create execution step audit record.

        Called during module execution to record inputs, outputs, and any errors.

        Args:
            data: Step creation data

        Returns:
            Created execution step with full details
        """
        with self._get_session() as session:
            # Create ORM model
            step_model = self.model_class(
                run_id=data.run_id,
                module_instance_id=data.module_instance_id,
                step_number=data.step_number,
                inputs=self._serialize_io(data.inputs),
                outputs=self._serialize_io(data.outputs),
                error=data.error,
            )

            session.add(step_model)
            session.commit()
            session.refresh(step_model)

            return self._model_to_domain(step_model)

    def get_steps_by_run_id(self, run_id: int) -> List[PipelineExecutionStep]:
        """
        Get all execution steps for a run, ordered by step_number.

        Retrieves the complete audit trail for a pipeline execution.

        Args:
            run_id: Execution run ID

        Returns:
            List of execution steps ordered by step_number (execution order)
        """
        with self._get_session() as session:
            stmt = select(self.model_class).where(
                self.model_class.run_id == run_id
            ).order_by(self.model_class.step_number, self.model_class.created_at)

            result = session.execute(stmt)
            models = result.scalars().all()

            return [self._model_to_domain(model) for model in models]

    def get_by_id(self, step_id: int) -> Optional[PipelineExecutionStep]:
        """
        Get execution step by ID.

        Args:
            step_id: Step ID

        Returns:
            Execution step with full details or None if not found
        """
        with self._get_session() as session:
            step = session.get(self.model_class, step_id)

            if step is None:
                return None

            return self._model_to_domain(step)

    def get_by_module_instance_id(
        self,
        run_id: int,
        module_instance_id: str
    ) -> Optional[PipelineExecutionStep]:
        """
        Get execution step for a specific module in a run.

        Useful for looking up a specific module's execution details.

        Args:
            run_id: Execution run ID
            module_instance_id: Module instance ID

        Returns:
            Execution step or None if not found
        """
        with self._get_session() as session:
            stmt = select(self.model_class).where(
                self.model_class.run_id == run_id,
                self.model_class.module_instance_id == module_instance_id
            )

            result = session.execute(stmt)
            step = result.scalars().first()

            if step is None:
                return None

            return self._model_to_domain(step)
