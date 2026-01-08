"""
ETO Sub-Run Pipeline Execution Step Domain Types
Pydantic models representing eto_sub_run_pipeline_execution_steps table and related operations
"""
from datetime import datetime

from pydantic import BaseModel, ConfigDict


class EtoSubRunPipelineExecutionStepCreate(BaseModel):
    """
    Data required to create a new pipeline execution step record.
    Used to create audit records for each step in the pipeline.
    """
    model_config = ConfigDict(frozen=True)

    pipeline_execution_id: int  # FK to eto_sub_run_pipeline_executions.id
    module_instance_id: str
    step_number: int
    inputs: str | None = None  # JSON string
    outputs: str | None = None  # JSON string
    error: str | None = None  # JSON string


class EtoSubRunPipelineExecutionStepUpdate(BaseModel):
    """
    Data for updating a pipeline execution step record.
    Typically used to set outputs after step execution, or error on failure.

    Uses Pydantic's model_fields_set to distinguish between:
    - Field not provided: not in model_fields_set (don't update)
    - Field set to None: in model_fields_set with None value (set NULL)
    - Field set to value: in model_fields_set with value (update)
    """
    inputs: str | None = None  # JSON string
    outputs: str | None = None  # JSON string
    error: str | None = None  # JSON string


class EtoSubRunPipelineExecutionStep(BaseModel):
    """
    Complete pipeline execution step record as stored in the database.
    Represents the eto_sub_run_pipeline_execution_steps table exactly.
    """
    model_config = ConfigDict(frozen=True)

    id: int
    pipeline_execution_id: int  # FK to eto_sub_run_pipeline_executions.id
    module_instance_id: str
    step_number: int
    inputs: str | None  # JSON string
    outputs: str | None  # JSON string
    error: str | None  # JSON string
    created_at: datetime
    updated_at: datetime
