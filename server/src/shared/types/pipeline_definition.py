"""
Pipeline Definition Types
Domain types for pipeline_definitions table
"""
from dataclasses import dataclass
from datetime import datetime

from .pipelines import PipelineState, VisualState


@dataclass(frozen=True)
class PipelineDefinition:
    """
    Complete pipeline definition from database.

    Represents the user-facing pipeline with both execution logic (pipeline_state)
    and visual layout (visual_state). Each definition owns its compiled steps
    directly via the pipeline_definition_steps table.
    """
    id: int
    pipeline_state: PipelineState
    visual_state: VisualState
    created_at: datetime
    updated_at: datetime


@dataclass(frozen=True)
class PipelineDefinitionSummary:
    """
    Lightweight summary for list views.
    """
    id: int
    created_at: datetime
    updated_at: datetime


@dataclass(frozen=True)
class PipelineDefinitionCreate:
    """
    Data needed to create new pipeline definition.

    The service layer will handle:
    - Validation of pipeline_state
    - Pruning dead branches
    - Compilation to execution steps
    """
    pipeline_state: PipelineState
    visual_state: VisualState
