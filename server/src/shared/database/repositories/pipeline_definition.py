"""
Pipeline Definition Repository
Repository for pipeline_definitions table with CRUD operations
"""
import json
import logging

from sqlalchemy import select, desc, asc

from shared.database.repositories.base import BaseRepository
from shared.database.models import PipelineDefinitionModel
from shared.types.pipeline_definition import (
    PipelineDefinition,
    PipelineDefinitionSummary,
    PipelineDefinitionCreate,
)
from shared.types.pipelines import (
    PipelineState,
    VisualState,
    EntryPoint,
    ModuleInstance,
    NodeInstance,
    NodeConnection,
    OutputChannelInstance,
    Position,
)

logger = logging.getLogger(__name__)


class PipelineDefinitionRepository(BaseRepository[PipelineDefinitionModel]):
    """
    Repository for Pipeline Definition CRUD operations.

    Supports dual-mode operation:
    - Standalone: Pass connection_manager, auto-commits
    - UoW: Pass session, caller controls transaction
    """

    @property
    def model_class(self) -> type[PipelineDefinitionModel]:
        """Return the SQLAlchemy model class this repository manages."""
        return PipelineDefinitionModel

    def _serialize_pipeline_state(self, pipeline_state: PipelineState) -> str:
        """Convert PipelineState to JSON string."""
        return json.dumps(pipeline_state.model_dump())

    def _serialize_visual_state(self, visual_state: VisualState) -> str:
        """Convert VisualState (dict of Position) to JSON string."""
        return json.dumps({k: v.model_dump() for k, v in visual_state.items()})

    def _deserialize_pipeline_state(self, json_str: str) -> PipelineState:
        """Convert JSON string to PipelineState."""
        data = json.loads(json_str)

        entry_points = [
            EntryPoint(
                entry_point_id=ep["entry_point_id"],
                name=ep["name"],
                outputs=[NodeInstance(**ni) for ni in ep.get("outputs", [])],
            )
            for ep in data.get("entry_points", [])
        ]

        modules = [
            ModuleInstance(
                module_instance_id=mod["module_instance_id"],
                module_id=mod["module_id"],
                config=mod["config"],
                inputs=[NodeInstance(**ni) for ni in mod.get("inputs", [])],
                outputs=[NodeInstance(**ni) for ni in mod.get("outputs", [])],
            )
            for mod in data.get("modules", [])
        ]

        connections = [NodeConnection(**conn) for conn in data.get("connections", [])]

        output_channels = [
            OutputChannelInstance(
                output_channel_instance_id=oc["output_channel_instance_id"],
                channel_type=oc["channel_type"],
                inputs=[NodeInstance(**ni) for ni in oc.get("inputs", [])],
            )
            for oc in data.get("output_channels", [])
        ]

        return PipelineState(
            entry_points=entry_points,
            modules=modules,
            connections=connections,
            output_channels=output_channels,
        )

    def _deserialize_visual_state(self, json_str: str) -> VisualState:
        """Convert JSON string to VisualState (flat dict structure)."""
        data = json.loads(json_str)

        # Handle both old nested structure and new flat structure
        if "modules" in data or "entry_points" in data:
            # Old nested structure - flatten it
            result: VisualState = {}
            result.update({k: Position(**v) for k, v in data.get("modules", {}).items()})
            result.update({k: Position(**v) for k, v in data.get("entry_points", {}).items()})
            return result
        else:
            # New flat structure
            return {k: Position(**v) for k, v in data.items()}

    def _model_to_domain(self, model: PipelineDefinitionModel) -> PipelineDefinition:
        """Convert ORM model to PipelineDefinition domain type."""
        return PipelineDefinition(
            id=model.id,
            pipeline_state=self._deserialize_pipeline_state(model.pipeline_state),
            visual_state=self._deserialize_visual_state(model.visual_state),
            created_at=model.created_at,
            updated_at=model.updated_at,
        )

    def _model_to_summary(self, model: PipelineDefinitionModel) -> PipelineDefinitionSummary:
        """Convert ORM model to PipelineDefinitionSummary domain type."""
        return PipelineDefinitionSummary(
            id=model.id,
            created_at=model.created_at,
            updated_at=model.updated_at,
        )

    def create(self, create_data: PipelineDefinitionCreate) -> PipelineDefinition:
        """
        Create new pipeline definition.

        Args:
            create_data: Pipeline definition creation data

        Returns:
            Created pipeline definition with full details
        """
        with self._get_session() as session:
            pipeline_state_json = self._serialize_pipeline_state(create_data.pipeline_state)
            visual_state_json = self._serialize_visual_state(create_data.visual_state)

            pipeline_def = self.model_class(
                pipeline_state=pipeline_state_json,
                visual_state=visual_state_json,
            )

            session.add(pipeline_def)
            session.commit()
            session.refresh(pipeline_def)

            return self._model_to_domain(pipeline_def)

    def get_by_id(self, pipeline_id: int) -> PipelineDefinition | None:
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

            return self._model_to_domain(pipeline_def)

    def list_pipelines(
        self,
        sort_by: str = "created_at",
        sort_order: str = "desc",
    ) -> list[PipelineDefinitionSummary]:
        """
        List all pipeline definitions with lightweight summaries.

        Args:
            sort_by: Field to sort by (created_at, updated_at, id)
            sort_order: Sort order (asc or desc)

        Returns:
            List of pipeline definition summaries
        """
        with self._get_session() as session:
            stmt = select(self.model_class)

            sort_column = getattr(self.model_class, sort_by, self.model_class.created_at)
            if sort_order == "desc":
                stmt = stmt.order_by(desc(sort_column))
            else:
                stmt = stmt.order_by(asc(sort_column))

            result = session.execute(stmt)
            models = result.scalars().all()

            return [self._model_to_summary(model) for model in models]
