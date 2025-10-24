"""
Pipeline Definition Step Types
Domain types for pipeline_definition_steps table
"""
from dataclasses import dataclass
from typing import Dict, Any, List

from .pipelines import NodeInstance


@dataclass(frozen=True)
class PipelineDefinitionStepFull:
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
    module_config: Dict[str, Any]  # Module-specific configuration
    input_field_mappings: Dict[str, str]  # Maps input pin IDs to source node IDs
    node_metadata: Dict[str, List[NodeInstance]]  # Maps "inputs"/"outputs" to pin metadata
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
    module_config: Dict[str, Any]
    input_field_mappings: Dict[str, str]
    node_metadata: Dict[str, List[NodeInstance]]
    step_number: int
