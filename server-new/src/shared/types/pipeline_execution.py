"""
Pipeline Execution Types
Domain types for pipeline execution runs and audit trail
"""
from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, Any, Optional

from shared.database.models import EtoStepStatus


@dataclass(frozen=True)
class PipelineExecutionRun:
    """
    Complete pipeline execution run from database.

    Represents a single execution of a compiled pipeline with entry point values.
    Tracks overall status and timing. Individual module executions are in
    PipelineExecutionStep records.
    """
    id: int
    eto_run_id: int
    status: EtoStepStatus
    executed_actions: Optional[str]
    started_at: Optional[datetime]
    completed_at: Optional[datetime]
    created_at: datetime
    updated_at: datetime


@dataclass(frozen=True)
class PipelineExecutionRunCreate:
    """
    Data needed to create new pipeline execution run.

    Created at the start of pipeline execution with status=PROCESSING.
    Updated to SUCCESS/FAILURE when execution completes.
    """
    eto_run_id: int
    status: EtoStepStatus = EtoStepStatus.PROCESSING
    executed_actions: Optional[str] = None
    started_at: Optional[datetime] = None


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
    inputs: Dict[str, Dict[str, Any]]  # {node_name: {value, type}}
    outputs: Dict[str, Dict[str, Any]]  # {node_name: {value, type}}
    error: Optional[str]
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
    inputs: Dict[str, Dict[str, Any]] = field(default_factory=dict)
    outputs: Dict[str, Dict[str, Any]] = field(default_factory=dict)
    error: Optional[str] = None


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
    inputs: Dict[str, Dict[str, Any]]  # {node_name: {value, type}}
    outputs: Dict[str, Dict[str, Any]]  # {node_name: {value, type}}
    error: Optional[str] = None


@dataclass(frozen=True)
class ActionExecutionData:
    """
    Data about an action module that would execute.

    During simulation, action modules collect their data but don't actually
    execute. This holds the data that would be passed to the action handler
    if it were to execute in production.

    Format for executed_actions field:
        {"module_id": {"input_field": "value", ...}, ...}
    """
    module_instance_id: str
    action_module_id: str  # e.g., "email_sender"
    inputs: Dict[str, Any]  # {node_name: value} - ready for handler
    config: Dict[str, Any]  # Module configuration


@dataclass(frozen=True)
class PipelineExecutionResult:
    """
    Result of pipeline execution (simulation mode).

    Contains all execution steps and collected action data without
    any database persistence.

    Used by simulate endpoint to show users what would happen if
    the pipeline were executed in production.
    """
    status: str  # "success" or "failed"
    steps: list  # List[PipelineExecutionStepResult]
    executed_actions: Dict[str, Dict[str, Any]]  # {module_id: {field: value}}
    error: Optional[str] = None
