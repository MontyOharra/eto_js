"""
Pipeline Definition Types
Domain types for pipeline_definitions table
"""
from datetime import datetime

from pydantic import BaseModel, ConfigDict

from .pipelines import PipelineState, VisualState


class PipelineDefinition(BaseModel):
    """
    Complete pipeline definition from database.

    Represents the user-facing pipeline with both execution logic (pipeline_state)
    and visual layout (visual_state). Each definition owns its compiled steps
    directly via the pipeline_definition_steps table.
    """
    model_config = ConfigDict(frozen=True)

    id: int
    pipeline_state: PipelineState
    visual_state: VisualState
    created_at: datetime
    updated_at: datetime


class PipelineDefinitionSummary(BaseModel):
    """
    Lightweight summary for list views.
    """
    model_config = ConfigDict(frozen=True)

    id: int
    created_at: datetime
    updated_at: datetime


class PipelineDefinitionCreate(BaseModel):
    """
    Data needed to create new pipeline definition.

    The service layer will handle:
    - Validation of pipeline_state
    - Pruning dead branches
    - Compilation to execution steps
    """
    model_config = ConfigDict(frozen=True)

    pipeline_state: PipelineState
    visual_state: VisualState
