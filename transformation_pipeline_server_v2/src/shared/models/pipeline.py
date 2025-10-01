"""
Strongly-typed pipeline domain models
These models define the structure of transformation pipelines following CRUD patterns
"""
from typing import List, Dict, Any, Optional, Literal
from pydantic import BaseModel, Field
from datetime import datetime
import json


# Supporting types for pipeline structure
class NodePin(BaseModel):
    """Represents an input or output pin on a module"""
    node_id: str
    direction: Literal["in", "out"]
    type: str  # "str", "int", "float", "bool", "datetime", etc.
    name: str
    position_index: int


class ModuleInstance(BaseModel):
    """A module instance placed on the canvas"""
    module_instance_id: str
    module_ref: str  # e.g., "text_cleaner:1.0.0"
    module_kind: Literal["transform", "action", "logic"]
    config: Dict[str, Any]  # Module-specific configuration
    inputs: List[NodePin]
    outputs: List[NodePin]


class NodeConnection(BaseModel):
    """Connection between two nodes"""
    from_node_id: str
    to_node_id: str


class EntryPoint(BaseModel):
    """Entry point for pipeline input"""
    node_id: str
    name: str


class PipelineState(BaseModel):
    """The actual pipeline structure (execution data)"""
    entry_points: List[EntryPoint] = Field(default_factory=list)
    modules: List[ModuleInstance] = Field(default_factory=list)
    connections: List[NodeConnection] = Field(default_factory=list)


class ModulePosition(BaseModel):
    """Position of a module on the canvas"""
    x: float
    y: float


class VisualState(BaseModel):
    """Visual positioning data for the UI"""
    modules: Dict[str, ModulePosition] = Field(default_factory=dict)
    entryPoints: Dict[str, ModulePosition] = Field(default_factory=dict)


# CRUD Models for Pipeline Operations

class PipelineBase(BaseModel):
    """Base fields for pipeline"""
    name: str = Field(..., min_length=1, max_length=255, description="Pipeline name")
    description: Optional[str] = Field(None, max_length=1000, description="Pipeline description")

    class Config:
        from_attributes = True


class PipelineCreate(PipelineBase):
    """Model for creating new pipeline"""
    pipeline_json: PipelineState = Field(..., description="Pipeline definition")
    visual_json: VisualState = Field(..., description="Visual positioning data")
    created_by_user: str = Field(..., description="User ID who created the pipeline")

    def model_dump_for_db(self) -> Dict[str, Any]:
        """Convert to database-ready dictionary with JSON serialization"""
        data = self.model_dump()
        # Convert complex objects to JSON strings for database storage
        data['pipeline_json'] = json.dumps(data['pipeline_json'])
        data['visual_json'] = json.dumps(data['visual_json'])
        # Compute derived fields
        pipeline_state = self.pipeline_json
        data['start_modules'] = json.dumps(self._get_start_modules(pipeline_state))
        data['end_modules'] = json.dumps(self._get_end_modules(pipeline_state))
        return data

    def _get_start_modules(self, pipeline_state: PipelineState) -> List[str]:
        """Get modules that have no inputs (start of pipeline)"""
        start_modules = []
        for module in pipeline_state.modules:
            if not module.inputs or len(module.inputs) == 0:
                start_modules.append(module.module_instance_id)
        return start_modules

    def _get_end_modules(self, pipeline_state: PipelineState) -> List[str]:
        """Get modules that have no outputs or are action modules (end of pipeline)"""
        end_modules = []
        for module in pipeline_state.modules:
            if not module.outputs or len(module.outputs) == 0 or module.module_kind == "action":
                end_modules.append(module.module_instance_id)
        return end_modules

    class Config:
        from_attributes = True


class PipelineUpdate(BaseModel):
    """Model for updating existing pipeline"""
    name: Optional[str] = Field(None, min_length=1, max_length=255, description="Pipeline name")
    description: Optional[str] = Field(None, max_length=1000, description="Pipeline description")
    pipeline_json: Optional[PipelineState] = Field(None, description="Pipeline definition")
    visual_json: Optional[VisualState] = Field(None, description="Visual positioning data")
    status: Optional[Literal["draft", "active", "archived"]] = Field(None, description="Pipeline status")

    def model_dump_for_db(self, exclude_unset: bool = True) -> Dict[str, Any]:
        """Convert to database-ready dictionary with JSON serialization"""
        data = self.model_dump(exclude_unset=exclude_unset)
        # Convert complex objects to JSON strings if present
        if 'pipeline_json' in data and data['pipeline_json'] is not None:
            pipeline_state = PipelineState(**data['pipeline_json'])
            data['pipeline_json'] = json.dumps(data['pipeline_json'])
            # Update derived fields when pipeline changes
            data['start_modules'] = json.dumps(self._get_start_modules(pipeline_state))
            data['end_modules'] = json.dumps(self._get_end_modules(pipeline_state))
        if 'visual_json' in data and data['visual_json'] is not None:
            data['visual_json'] = json.dumps(data['visual_json'])
        return data

    def _get_start_modules(self, pipeline_state: PipelineState) -> List[str]:
        """Get modules that have no inputs (start of pipeline)"""
        start_modules = []
        for module in pipeline_state.modules:
            if not module.inputs or len(module.inputs) == 0:
                start_modules.append(module.module_instance_id)
        return start_modules

    def _get_end_modules(self, pipeline_state: PipelineState) -> List[str]:
        """Get modules that have no outputs or are action modules (end of pipeline)"""
        end_modules = []
        for module in pipeline_state.modules:
            if not module.outputs or len(module.outputs) == 0 or module.module_kind == "action":
                end_modules.append(module.module_instance_id)
        return end_modules

    class Config:
        from_attributes = True


class Pipeline(PipelineBase):
    """Full pipeline model retrieved from database"""
    id: str = Field(..., description="Pipeline ID")
    pipeline_json: PipelineState = Field(..., description="Pipeline definition")
    visual_json: VisualState = Field(..., description="Visual positioning data")
    created_by_user: str = Field(..., description="User ID who created the pipeline")
    status: Literal["draft", "active", "archived"] = Field("draft", description="Pipeline status")
    is_active: bool = Field(True, description="Whether pipeline is active")
    created_at: datetime
    updated_at: datetime

    # Computed fields for convenience
    module_count: int = Field(0, description="Number of modules")
    connection_count: int = Field(0, description="Number of connections")
    entry_point_count: int = Field(0, description="Number of entry points")

    @classmethod
    def from_db_model(cls, db_model) -> "Pipeline":
        """
        Convert SQLAlchemy model to Pydantic model

        Args:
            db_model: TransformationPipelineModel instance from database

        Returns:
            Pipeline Pydantic model
        """
        # Parse JSON fields back to Python objects
        pipeline_json_data = json.loads(db_model.pipeline_json) if isinstance(db_model.pipeline_json, str) else db_model.pipeline_json
        visual_json_data = json.loads(db_model.visual_json) if isinstance(db_model.visual_json, str) else db_model.visual_json

        # Create PipelineState and VisualState objects
        pipeline_state = PipelineState(**pipeline_json_data)
        visual_state = VisualState(**visual_json_data)

        return cls(
            id=db_model.id,
            name=db_model.name,
            description=db_model.description,
            pipeline_json=pipeline_state,
            visual_json=visual_state,
            created_by_user=db_model.created_by_user,
            status=db_model.status,
            is_active=db_model.is_active,
            created_at=db_model.created_at,
            updated_at=db_model.updated_at,
            # Compute counts
            module_count=len(pipeline_state.modules),
            connection_count=len(pipeline_state.connections),
            entry_point_count=len(pipeline_state.entry_points)
        )

    class Config:
        from_attributes = True


class PipelineSummary(BaseModel):
    """Lightweight pipeline summary for list views"""
    id: str
    name: str
    description: Optional[str] = None
    created_by_user: str
    status: Literal["draft", "active", "archived"] = "draft"
    module_count: int = 0
    connection_count: int = 0
    entry_point_count: int = 0
    created_at: datetime
    updated_at: datetime

    @classmethod
    def from_full_pipeline(cls, pipeline: Pipeline) -> "PipelineSummary":
        """Create summary from full pipeline model"""
        return cls(
            id=pipeline.id,
            name=pipeline.name,
            description=pipeline.description,
            created_by_user=pipeline.created_by_user,
            status=pipeline.status,
            module_count=pipeline.module_count,
            connection_count=pipeline.connection_count,
            entry_point_count=pipeline.entry_point_count,
            created_at=pipeline.created_at,
            updated_at=pipeline.updated_at
        )

    class Config:
        from_attributes = True