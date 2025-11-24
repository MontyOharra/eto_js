"""
ETO Sub-Run Pipeline Execution Step Domain Types
Dataclasses representing eto_sub_run_pipeline_execution_steps table and related operations
"""
from dataclasses import dataclass
from datetime import datetime
from typing import Optional


# =========================
# Pipeline Execution Step Types
# =========================

@dataclass
class EtoSubRunPipelineExecutionStepCreate:
    """
    Data required to create a new pipeline execution step record.
    Used to create audit records for each step in the pipeline.
    """
    pipeline_execution_id: int  # FK to eto_sub_run_pipeline_executions.id
    module_instance_id: str
    step_number: int
    inputs: Optional[str] = None  # JSON string
    outputs: Optional[str] = None  # JSON string
    error: Optional[str] = None  # JSON string


@dataclass
class EtoSubRunPipelineExecutionStepUpdate:
    """
    Data for updating a pipeline execution step record.
    All fields are optional - only provided fields will be updated.
    Typically used to set outputs after step execution, or error on failure.
    """
    inputs: Optional[str] = None  # JSON string
    outputs: Optional[str] = None  # JSON string
    error: Optional[str] = None  # JSON string


@dataclass
class EtoSubRunPipelineExecutionStep:
    """
    Complete pipeline execution step record as stored in the database.
    Represents the eto_sub_run_pipeline_execution_steps table exactly.
    """
    id: int
    pipeline_execution_id: int  # FK to eto_sub_run_pipeline_executions.id
    module_instance_id: str
    step_number: int
    inputs: Optional[str]  # JSON string
    outputs: Optional[str]  # JSON string
    error: Optional[str]  # JSON string
    created_at: datetime
    updated_at: datetime
