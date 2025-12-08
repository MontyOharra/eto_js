"""
Pipeline Execution Types
Domain types for pipeline execution runs and audit trail
"""
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any


@dataclass(frozen=True)
class PipelinExecutionStepIOData:
    name: str
    value: str
    type: str

@dataclass(frozen=True)
class PipelineExecutionStep:
    """
    Complete execution step audit record from database.

    Records one module's execution during a pipeline run.
    Inputs and outputs stored as {node_name: {value, type}} for human readability.
    """
    id: int
    run_id: int
    module_instance_id: str
    step_number: int
    inputs: dict[str, PipelinExecutionStepIOData]  # {node_name: {value, type}}
    outputs: dict[str, PipelinExecutionStepIOData]  # {node_name: {value, type}}
    error: str | None
    created_at: datetime
    updated_at: datetime


@dataclass(frozen=True)
class PipelineExecutionStepCreate:
    """
    Data needed to create execution step audit record.

    Persisted during module execution to create audit trail.
    Inputs and outputs use node names (not node IDs) for readability.

    Example:
        inputs = {
            "hawb": {"value": "ABC123", "type": "str"},
            "weight": {"value": 150.5, "type": "float"}
        }
        outputs = {
            "cleaned_hawb": {"value": "abc123", "type": "str"}
        }
    """
    run_id: int
    module_instance_id: str
    step_number: int
    inputs: dict[str, dict[str, Any]] = field(default_factory=dict)
    outputs: dict[str, dict[str, Any]] = field(default_factory=dict)
    error: str | None = None


# ==================== Simulation Types ====================


@dataclass(frozen=True)
class PipelineExecutionStepResult:
    """
    Result of single module execution (simulation mode).

    Similar to PipelineExecutionStep but without DB IDs.
    Used for in-memory execution results during simulation.
    """
    module_instance_id: str
    step_number: int
    inputs: dict[str, dict[str, Any]]  # {node_id: {name, value, type}}
    outputs: dict[str, dict[str, Any]]  # {node_id: {name, value, type}}
    error: str | None = None


@dataclass(frozen=True)
class PipelineExecutionResult:
    """
    Result of pipeline execution (simulation mode).

    Contains all execution steps and collected output channel values
    without any database persistence.

    Used by simulate endpoint to show users what would happen if
    the pipeline were executed in production.
    """
    status: str
    steps: list[PipelineExecutionStepResult]
    output_channel_values: dict[str, Any]  # {channel_type: value} e.g., {"hawb": "ABC123", "pickup_address": "123 Main St"}
    error: str | None
    # Legacy fields for backward compatibility (deprecated)
    output_module_id: str | None = None
    output_module_inputs: dict[str, Any] = field(default_factory=dict)