"""
Strongly-typed pipeline domain models
These models define the structure of transformation pipelines following CRUD patterns
"""
from typing import List, Dict, Any, Optional, Literal
from pydantic import BaseModel, Field
from datetime import datetime
import json


# Supporting types for pipeline structure
class InstanceNodePin(BaseModel):
    """Runtime instance of a pin in a module instance"""
    node_id: str
    type: str  # Selected type: "str", "int", "float", "bool", "datetime", etc.
    name: str
    position_index: int
    group_label: str  # Which NodeGroup template this came from (e.g., "input_text", "text_data")


class ModuleInstance(BaseModel):
    """A module instance placed on the canvas"""
    module_instance_id: str
    module_ref: str  # e.g., "text_cleaner:1.0.0"
    module_kind: Literal["transform", "action", "logic"]
    config: Dict[str, Any]  # Module-specific configuration
    inputs: List[InstanceNodePin] = Field(default_factory=list)  # Flat list, grouped by group_label
    outputs: List[InstanceNodePin] = Field(default_factory=list)


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
    """Base fields for pipeline - includes visual and execution state (always required)"""
    name: str = Field(..., min_length=1, max_length=255, description="Pipeline name")
    description: Optional[str] = Field(None, max_length=1000, description="Pipeline description")
    pipeline_json: PipelineState = Field(..., description="Pipeline execution state")
    visual_json: VisualState = Field(..., description="Pipeline visual layout")

    class Config:
        from_attributes = True


class PipelineCreate(PipelineBase):
    """Model for creating new pipeline - pipelines are immutable, no updates allowed"""

    def model_dump_for_db(self) -> Dict[str, Any]:
        """Convert to database-ready dictionary with JSON serialization"""
        data = self.model_dump()
        # Convert complex objects to JSON strings for database storage
        data['pipeline_json'] = json.dumps(data['pipeline_json'])
        data['visual_json'] = json.dumps(data['visual_json'])
        return data

    class Config:
        from_attributes = True


class Pipeline(PipelineBase):
    """Full pipeline model retrieved from database - immutable once created"""
    id: str = Field(..., description="Pipeline ID")
    plan_checksum: Optional[str] = Field(None, description="Compiled plan checksum")
    compiled_at: Optional[datetime] = Field(None, description="When pipeline was compiled")
    created_at: datetime = Field(..., description="When pipeline was created")
    is_active: bool = Field(True, description="Whether pipeline is active")

    # Computed fields for convenience
    module_count: int = Field(0, description="Number of modules")
    connection_count: int = Field(0, description="Number of connections")
    entry_point_count: int = Field(0, description="Number of entry points")

    @classmethod
    def from_db_model(cls, db_model) -> "Pipeline":
        """
        Convert SQLAlchemy model to Pydantic model

        Args:
            db_model: PipelineDefinitionModel instance from database

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
            plan_checksum=db_model.plan_checksum,
            compiled_at=db_model.compiled_at,
            is_active=db_model.is_active,
            created_at=db_model.created_at,
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
    is_active: bool = True
    module_count: int = 0
    connection_count: int = 0
    entry_point_count: int = 0
    created_at: datetime

    @classmethod
    def from_full_pipeline(cls, pipeline: Pipeline) -> "PipelineSummary":
        """Create summary from full pipeline model"""
        return cls(
            id=pipeline.id,
            name=pipeline.name,
            description=pipeline.description,
            is_active=pipeline.is_active,
            module_count=pipeline.module_count,
            connection_count=pipeline.connection_count,
            entry_point_count=pipeline.entry_point_count,
            created_at=pipeline.created_at
        )

    class Config:
        from_attributes = True