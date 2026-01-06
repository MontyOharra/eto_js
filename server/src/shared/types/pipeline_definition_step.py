"""
Pipeline Definition Step Types
Domain types for pipeline_definition_steps table
"""
from typing import Any

from pydantic import BaseModel, ConfigDict

from .pipelines import NodeInstance


class PipelineDefinitionStep(BaseModel):
    """
    Complete pipeline step record from database.

    Represents a single execution step in a compiled pipeline.
    Steps are ordered by step_number (topological layers) and contain
    all the metadata needed to execute a module instance.

    Each step belongs to exactly one pipeline definition via pipeline_definition_id.
    """
    model_config = ConfigDict(frozen=True)

    id: int
    pipeline_definition_id: int
    module_instance_id: str
    module_ref: str | None  # e.g., "text_cleaner:1.0.0", None for output channel steps
    module_config: dict[str, Any]  # Module-specific configuration; contains channel_type for output channels
    input_field_mappings: dict[str, str]  # Maps input pin IDs to source node IDs
    node_metadata: dict[str, list[NodeInstance]]  # Maps "inputs"/"outputs" to pin metadata
    step_number: int  # Execution order (topological layer)


class PipelineDefinitionStepCreate(BaseModel):
    """
    Data needed to create new pipeline step.

    Created during pipeline compilation after:
    1. Validation succeeds
    2. Graph pruning completes
    3. Topological sorting determines execution order
    4. Compiler generates step metadata

    The repository layer handles JSON serialization of dict fields.
    """
    model_config = ConfigDict(frozen=True)

    pipeline_definition_id: int
    module_instance_id: str
    module_ref: str | None  # None for output channel steps
    module_config: dict[str, Any]  # Contains channel_type for output channel steps
    input_field_mappings: dict[str, str]
    node_metadata: dict[str, list[NodeInstance]]
    step_number: int
