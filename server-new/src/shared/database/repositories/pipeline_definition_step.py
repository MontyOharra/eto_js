"""
Pipeline Definition Step Repository
Repository for pipeline_definition_steps table with CRUD operations
"""
import json
import logging
from typing import Type, List, Dict, Optional, Any
from sqlalchemy import select

from shared.database.repositories.base import BaseRepository
from shared.database.models import PipelineDefinitionStepModel
from shared.types.pipeline_definition_step import (
    PipelineDefinitionStepFull,
    PipelineDefinitionStepCreate,
)
from shared.types.pipelines import NodeInstance

logger = logging.getLogger(__name__)


class PipelineDefinitionStepRepository(BaseRepository[PipelineDefinitionStepModel]):
    """
    Repository for Pipeline Definition Step CRUD operations.

    Supports dual-mode operation:
    - Standalone: Pass connection_manager, auto-commits
    - UoW: Pass session, caller controls transaction

    This table is append-only (no updates or deletes) - steps are immutable
    once created as part of a compiled plan.
    """

    @property
    def model_class(self) -> Type[PipelineDefinitionStepModel]:
        """Return the SQLAlchemy model class this repository manages"""
        return PipelineDefinitionStepModel

    def _serialize_node_metadata(self, node_metadata: Dict[str, List[NodeInstance]]) -> str:
        """
        Convert node metadata (inputs/outputs) to JSON string.

        Args:
            node_metadata: Dict with "inputs" and "outputs" keys mapping to List[NodeInstance]

        Returns:
            JSON string representation
        """
        from dataclasses import asdict

        # Convert NodeInstance dataclasses to dicts
        serializable = {}
        for key, node_list in node_metadata.items():
            serializable[key] = [asdict(node) for node in node_list]

        return json.dumps(serializable)

    def _deserialize_node_metadata(self, json_str: str) -> Dict[str, List[NodeInstance]]:
        """
        Convert JSON string to node metadata dict.

        Args:
            json_str: JSON string from database

        Returns:
            Dict with "inputs" and "outputs" keys mapping to List[NodeInstance]
        """
        data = json.loads(json_str)

        result = {}
        for key, node_list in data.items():
            result[key] = [NodeInstance(**node_dict) for node_dict in node_list]

        return result

    def _model_to_full(self, model: PipelineDefinitionStepModel) -> PipelineDefinitionStepFull:
        """Convert ORM model to PipelineDefinitionStepFull dataclass"""
        return PipelineDefinitionStepFull(
            id=model.id,
            pipeline_compiled_plan_id=model.pipeline_compiled_plan_id,
            module_instance_id=model.module_instance_id,
            module_ref=model.module_ref,
            module_config=json.loads(model.module_config),
            input_field_mappings=json.loads(model.input_field_mappings),
            node_metadata=self._deserialize_node_metadata(model.node_metadata),
            step_number=model.step_number
        )

    def create_steps(
        self,
        steps: List[PipelineDefinitionStepCreate]
    ) -> List[PipelineDefinitionStepFull]:
        """
        Bulk create pipeline definition steps.

        This is the primary method for creating steps - they're always created
        in bulk as part of a compiled plan.

        Args:
            steps: List of step creation data (all for same compiled plan)

        Returns:
            List of created steps with full details
        """
        with self._get_session() as session:
            # Create ORM models
            step_models = []
            for step_data in steps:
                step_model = self.model_class(
                    pipeline_compiled_plan_id=step_data.pipeline_compiled_plan_id,
                    module_instance_id=step_data.module_instance_id,
                    module_ref=step_data.module_ref,
                    module_config=json.dumps(step_data.module_config),
                    input_field_mappings=json.dumps(step_data.input_field_mappings),
                    node_metadata=self._serialize_node_metadata(step_data.node_metadata),
                    step_number=step_data.step_number
                )
                step_models.append(step_model)

            # Bulk insert
            session.add_all(step_models)
            session.commit()

            # Refresh to get IDs
            for model in step_models:
                session.refresh(model)

            return [self._model_to_full(model) for model in step_models]

    def get_steps_by_plan_id(
        self,
        compiled_plan_id: int
    ) -> List[PipelineDefinitionStepFull]:
        """
        Get all steps for a compiled plan, ordered by step_number.

        This retrieves the execution plan in the correct topological order.

        Args:
            compiled_plan_id: Compiled plan ID

        Returns:
            List of steps ordered by step_number (execution order)
        """
        with self._get_session() as session:
            stmt = select(self.model_class).where(
                self.model_class.pipeline_compiled_plan_id == compiled_plan_id
            ).order_by(self.model_class.step_number)

            result = session.execute(stmt)
            models = result.scalars().all()

            return [self._model_to_full(model) for model in models]

    def get_by_id(self, step_id: int) -> Optional[PipelineDefinitionStepFull]:
        """
        Get step by ID.

        Args:
            step_id: Step ID

        Returns:
            Step with full details or None if not found
        """
        with self._get_session() as session:
            step = session.get(self.model_class, step_id)

            if step is None:
                return None

            return self._model_to_full(step)