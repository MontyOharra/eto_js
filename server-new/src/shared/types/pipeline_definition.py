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
    and visual layout (visual_state). Multiple definitions can share the same
    compiled plan via compiled_plan_id.
    """
    id: int
    pipeline_state: PipelineState
    visual_state: VisualState
    compiled_plan_id: int | None
    created_at: datetime
    updated_at: datetime


@dataclass(frozen=True)
class PipelineDefinitionSummary:
    """
    Lightweight summary for list views.

    No computed fields - kept minimal since this will be removed later.
    """
    id: int
    compiled_plan_id: int | None
    created_at: datetime
    updated_at: datetime


@dataclass(frozen=True)
class PipelineDefinitionCreate:
    """
    Data needed to create new pipeline definition.

    The service layer will handle:
    - Validation of pipeline_state
    - Pruning dead branches
    - Checksum calculation
    - Compilation (or reuse of existing compiled plan)
    """
    pipeline_state: PipelineState
    visual_state: VisualState
