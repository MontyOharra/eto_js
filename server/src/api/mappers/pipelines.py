"""
Pipeline API Mappers

Utility functions for converting dict data to domain types.
Used by pdf_templates service for dict-to-Pydantic conversion.

NOTE: Most pipeline API endpoints no longer need these mappers since
the schemas now directly use shared types. These remain for legacy
dict-handling in pdf_templates.
"""
from shared.types.pipelines import (
    NodeInstance,
    EntryPoint,
    ModuleInstance,
    NodeConnection,
    OutputChannelInstance,
    PipelineState,
    VisualState,
    Position,
)


def convert_pipeline_state_to_domain(pipeline_state: PipelineState | dict) -> PipelineState:
    """
    Convert dict or PipelineState to domain PipelineState.

    If already a PipelineState, returns as-is.
    If a dict, validates and converts to PipelineState.
    """
    if isinstance(pipeline_state, PipelineState):
        return pipeline_state

    # Use Pydantic's model_validate for dict conversion
    return PipelineState.model_validate(pipeline_state)


def convert_visual_state_to_domain(visual_state: VisualState | dict) -> VisualState:
    """
    Convert dict to VisualState (dict[str, Position]).

    Handles both raw dicts with {x, y} values and Position objects.
    """
    if not isinstance(visual_state, dict):
        return visual_state

    result: VisualState = {}
    for key, pos in visual_state.items():
        if isinstance(pos, Position):
            result[key] = pos
        elif isinstance(pos, dict):
            result[key] = Position(x=pos['x'], y=pos['y'])
        else:
            # Already a Position-like object with x, y attributes
            result[key] = Position(x=pos.x, y=pos.y)

    return result
