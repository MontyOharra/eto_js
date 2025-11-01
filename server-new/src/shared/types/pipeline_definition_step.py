"""
Pipeline Definition Step Types
Domain types for pipeline_definition_steps table
"""
from dataclasses import dataclass
from typing import Any

from .pipelines import NodeInstance


@dataclass(frozen=True)
class PipelineDefinitionStep:
    """
    Complete pipeline step record from database.

    Represents a single execution step in a compiled pipeline plan.
    Steps are ordered by step_number (topological layers) and contain
    all the metadata needed to execute a module instance.

    Multiple compiled plans can have similar steps, but each step belongs
    to exactly one compiled plan via pipeline_compiled_plan_id.
    """
    id: int
    pipeline_compiled_plan_id: int
    module_instance_id: str
    module_ref: str  # e.g., "text_cleaner:1.0.0"
    module_config: dict[str, Any]  # Module-specific configuration
    input_field_mappings: dict[str, str]  # Maps input pin IDs to source node IDs
    node_metadata: dict[str, list[NodeInstance]]  # Maps "inputs"/"outputs" to pin metadata
    step_number: int  # Execution order (topological layer)


@dataclass(frozen=True)
class PipelineDefinitionStepCreate:
    """
    Data needed to create new pipeline step.

    Created during pipeline compilation after:
    1. Validation succeeds
    2. Graph pruning completes
    3. Checksum calculation completes
    4. Topological sorting determines execution order
    5. Compiler generates step metadata

    The repository layer handles JSON serialization of dict fields.
    """
    pipeline_compiled_plan_id: int
    module_instance_id: str
    module_ref: str
    module_config: dict[str, Any]
    input_field_mappings: dict[str, str]
    node_metadata: dict[str, list[NodeInstance]]
    step_number: int
