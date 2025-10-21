"""
Strongly-typed pipeline domain models
These models define the structure of transformation pipelines following CRUD patterns
"""
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field
from datetime import datetime
import json

from shared.database.models import PipelineDefinitionModel

from ..pipelines import PipelineState, VisualState

# CRUD Models for Pipeline Operations

class PipelineDefinitionBase(BaseModel):
    """Base fields for pipeline - includes visual and execution state (always required)"""
    name: str = Field(..., min_length=1, max_length=255, description="Pipeline name")
    description: Optional[str] = Field(None, max_length=1000, description="Pipeline description")
    pipeline_state: PipelineState = Field(..., description="Pipeline execution state")
    visual_state: VisualState = Field(..., description="Pipeline visual layout")

    class Config:
        from_attributes = True


class PipelineDefinition(PipelineDefinitionBase):
    """Full pipeline model retrieved from database - immutable once created"""
    id: int = Field(..., description="Pipeline ID")
    plan_checksum: Optional[str] = Field(None, description="Compiled plan checksum")
    compiled_at: Optional[datetime] = Field(None, description="When pipeline was compiled")
    created_at: datetime = Field(..., description="When pipeline was created")
    is_active: bool = Field(True, description="Whether pipeline is active")

    # Computed fields for convenience
    module_count: int = Field(0, description="Number of modules")
    connection_count: int = Field(0, description="Number of connections")
    entry_point_count: int = Field(0, description="Number of entry points")

    @classmethod
    def from_db_model(cls, db_model : PipelineDefinitionModel) -> "PipelineDefinition":
        """
        Convert SQLAlchemy model to Pydantic model

        Args:
            db_model: PipelineDefinitionModel instance from database

        Returns:
            Pipeline Pydantic model
        """
        # Parse JSON fields back to Python objects
        pipeline_state = PipelineState(**json.loads(db_model.pipeline_state))
        visual_state = VisualState(**json.loads(db_model.visual_state))

        return cls(
            id=db_model.id,
            name=db_model.name,
            description=db_model.description,
            pipeline_state=pipeline_state,
            visual_state=visual_state,
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


class PipelineDefinitionCreate(PipelineDefinitionBase):
    """Model for creating new pipeline - pipelines are immutable, no updates allowed"""

    def model_dump_for_db(self) -> Dict[str, Any]:
        """Convert to database-ready dictionary with JSON serialization"""
        data = self.model_dump()
        # Convert complex objects to JSON strings for database storage
        data['pipeline_state'] = json.dumps(data['pipeline_state'])
        data['visual_state'] = json.dumps(data['visual_state'])
        return data

    class Config:
        from_attributes = True


class PipelineDefinitionSummary(BaseModel):
    """Lightweight pipeline summary for list views"""
    id: int
    name: str
    description: Optional[str] = None
    is_active: bool = True
    module_count: int = 0
    connection_count: int = 0
    entry_point_count: int = 0
    created_at: datetime

    @classmethod
    def from_full_pipeline_definition(cls, pipeline_definition: PipelineDefinition) -> "PipelineDefinitionSummary":
        """Create summary from full pipeline model"""
        return cls(
            id=pipeline_definition.id,
            name=pipeline_definition.name,
            description=pipeline_definition.description,
            is_active=pipeline_definition.is_active,
            module_count=pipeline_definition.module_count,
            connection_count=pipeline_definition.connection_count,
            entry_point_count=pipeline_definition.entry_point_count,
            created_at=pipeline_definition.created_at
        )

    class Config:
        from_attributes = True