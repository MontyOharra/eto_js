"""
Pipeline Definition Repository
Repository for pipeline_definitions table with CRUD operations
"""
import json
import logging
from typing import Type, List, Optional
from sqlalchemy import select, desc, asc

from shared.database.repositories.base import BaseRepository
from shared.database.models import PipelineDefinitionModel
from shared.types.pipeline_definition import (
    PipelineDefinitionFull,
    PipelineDefinitionSummary,
    PipelineDefinitionCreate,
)
from shared.types.pipelines import PipelineState, VisualState

logger = logging.getLogger(__name__)


class PipelineDefinitionRepository(BaseRepository[PipelineDefinitionModel]):
    """
    Repository for Pipeline Definition CRUD operations.

    Supports dual-mode operation:
    - Standalone: Pass connection_manager, auto-commits
    - UoW: Pass session, caller controls transaction
    """

    @property
    def model_class(self) -> Type[PipelineDefinitionModel]:
        """Return the SQLAlchemy model class this repository manages"""
        return PipelineDefinitionModel

    def _serialize_pipeline_state(self, pipeline_state: PipelineState) -> str:
        """Convert PipelineState dataclass to JSON string"""
        from dataclasses import asdict
        return json.dumps(asdict(pipeline_state))

    def _serialize_visual_state(self, visual_state: VisualState) -> str:
        """Convert VisualState (flat dict) to JSON string"""
        from dataclasses import asdict
        # visual_state is a dict of {node_id: Position}
        # Convert Position dataclasses to dicts
        return json.dumps({k: asdict(v) for k, v in visual_state.items()})

    def _deserialize_pipeline_state(self, json_str: str) -> PipelineState:
        """Convert JSON string to PipelineState dataclass"""
        from shared.types.pipelines import EntryPoint, ModuleInstance, NodeInstance, NodeConnection
        data = json.loads(json_str)

        # Reconstruct nested dataclasses
        entry_points = [EntryPoint(**ep) for ep in data.get("entry_points", [])]

        modules = []
        for mod in data.get("modules", []):
            inputs = [NodeInstance(**ni) for ni in mod.get("inputs", [])]
            outputs = [NodeInstance(**ni) for ni in mod.get("outputs", [])]
            modules.append(ModuleInstance(
                module_instance_id=mod["module_instance_id"],
                module_ref=mod["module_ref"],
                config=mod["config"],
                inputs=inputs,
                outputs=outputs
            ))

        connections = [NodeConnection(**conn) for conn in data.get("connections", [])]

        return PipelineState(
            entry_points=entry_points,
            modules=modules,
            connections=connections
        )

    def _deserialize_visual_state(self, json_str: str) -> VisualState:
        """Convert JSON string to VisualState (flat dict structure)"""
        from shared.types.pipelines import Position
        data = json.loads(json_str)

        # Handle both old nested structure and new flat structure
        if "modules" in data or "entry_points" in data:
            # Old nested structure - flatten it
            result = {}
            result.update({k: Position(**v) for k, v in data.get("modules", {}).items()})
            result.update({k: Position(**v) for k, v in data.get("entry_points", {}).items()})
            return result
        else:
            # New flat structure
            return {k: Position(**v) for k, v in data.items()}

    def _model_to_full(self, model: PipelineDefinitionModel) -> PipelineDefinitionFull:
        """Convert ORM model to PipelineDefinitionFull dataclass"""
        return PipelineDefinitionFull(
            id=model.id,
            pipeline_state=self._deserialize_pipeline_state(model.pipeline_state),
            visual_state=self._deserialize_visual_state(model.visual_state),
            compiled_plan_id=model.compiled_plan_id,
            created_at=model.created_at,
            updated_at=model.updated_at
        )

    def _model_to_summary(self, model: PipelineDefinitionModel) -> PipelineDefinitionSummary:
        """Convert ORM model to PipelineDefinitionSummary dataclass"""
        return PipelineDefinitionSummary(
            id=model.id,
            compiled_plan_id=model.compiled_plan_id,
            created_at=model.created_at,
            updated_at=model.updated_at
        )

    def create(self, create_data: PipelineDefinitionCreate) -> PipelineDefinitionFull:
        """
        Create new pipeline definition.

        Args:
            create_data: Pipeline definition creation data

        Returns:
            Created pipeline definition with full details
        """
        with self._get_session() as session:
            # Serialize states to JSON
            pipeline_state_json = self._serialize_pipeline_state(create_data.pipeline_state)
            visual_state_json = self._serialize_visual_state(create_data.visual_state)

            # Create ORM model
            pipeline_def = self.model_class(
                pipeline_state=pipeline_state_json,
                visual_state=visual_state_json,
                compiled_plan_id=None  # Compilation happens separately in service layer
            )

            session.add(pipeline_def)
            session.commit()
            session.refresh(pipeline_def)

            return self._model_to_full(pipeline_def)

    def get_by_id(self, pipeline_id: int) -> Optional[PipelineDefinitionFull]:
        """
        Get pipeline definition by ID.

        Args:
            pipeline_id: Pipeline definition ID

        Returns:
            Pipeline definition with full details or None if not found
        """
        with self._get_session() as session:
            pipeline_def = session.get(self.model_class, pipeline_id)

            if pipeline_def is None:
                return None

            return self._model_to_full(pipeline_def)

    def list_pipelines(
        self,
        sort_by: str = "created_at",
        sort_order: str = "desc"
    ) -> List[PipelineDefinitionSummary]:
        """
        List all pipeline definitions with lightweight summaries.

        Args:
            sort_by: Field to sort by (created_at, updated_at, id)
            sort_order: Sort order (asc or desc)

        Returns:
            List of pipeline definition summaries
        """
        with self._get_session() as session:
            # Build query
            stmt = select(self.model_class)

            # Apply sorting
            sort_column = getattr(self.model_class, sort_by, self.model_class.created_at)
            if sort_order == "desc":
                stmt = stmt.order_by(desc(sort_column))
            else:
                stmt = stmt.order_by(asc(sort_column))

            result = session.execute(stmt)
            models = result.scalars().all()

            return [self._model_to_summary(model) for model in models]

    def update_compiled_plan_id(self, pipeline_id: int, compiled_plan_id: int) -> None:
        """
        Update the compiled_plan_id for a pipeline definition.

        This is the only mutable field - used by the service layer after compilation.

        Args:
            pipeline_id: Pipeline definition ID
            compiled_plan_id: Compiled plan ID to link to
        """
        with self._get_session() as session:
            pipeline_def = session.get(self.model_class, pipeline_id)
            if pipeline_def is None:
                raise ValueError(f"Pipeline definition {pipeline_id} not found")

            pipeline_def.compiled_plan_id = compiled_plan_id
            session.commit()
