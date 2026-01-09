"""
Pipeline Execution Types
Domain types for pipeline execution results (in-memory, no persistence)

Note: Actual persistence of execution steps is handled by ETO sub-runs.
See eto_sub_run_pipeline_execution_steps.py for persisted execution types.
"""
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict


# Pipeline execution status (in-memory result, not persisted)
PipelineExecutionStatus = Literal["success", "failed", "partial"]


class PipelineExecutionStepResult(BaseModel):
    """
    Result of single module execution.

    Used for in-memory execution results during pipeline runs.
    """
    model_config = ConfigDict(frozen=True)

    module_instance_id: str
    step_number: int
    inputs: dict[str, dict[str, Any]]  # {node_id: {name, value, type}}
    outputs: dict[str, dict[str, Any]]  # {node_id: {name, value, type}}
    error: str | None = None


class PipelineExecutionResult(BaseModel):
    """
    Result of pipeline execution.

    Contains all execution steps and collected output channel values.
    This is an in-memory result - persistence is handled by ETO sub-runs.
    """
    model_config = ConfigDict(frozen=True)

    status: PipelineExecutionStatus
    steps: list[PipelineExecutionStepResult]
    output_channel_values: dict[str, Any]  # {channel_type: value} e.g., {"hawb": "ABC123"}
    error: str | None
