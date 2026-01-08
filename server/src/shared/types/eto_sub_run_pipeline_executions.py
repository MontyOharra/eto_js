"""
ETO Sub-Run Pipeline Execution Domain Types
Pydantic models representing eto_sub_run_pipeline_executions table and related operations
"""
from datetime import datetime

from pydantic import BaseModel, ConfigDict


# =========================
# ETO Sub-Run Pipeline Execution Types
# =========================

class EtoSubRunPipelineExecutionCreate(BaseModel):
    """
    Data required to create a new pipeline execution record for a sub-run.
    Status defaults to "processing" in the database.
    """
    model_config = ConfigDict(frozen=True)

    sub_run_id: int
    started_at: datetime | None = None


class EtoSubRunPipelineExecutionUpdate(BaseModel):
    """
    Data for updating a pipeline execution record.

    Uses Pydantic's model_fields_set to distinguish between:
    - Field not provided: not in model_fields_set (don't update)
    - Field set to None: in model_fields_set with None value (set NULL)
    - Field set to value: in model_fields_set with value (update)
    """
    status: str | None = None
    error_message: str | None = None
    transformed_data: str | None = None  # JSON string of output channel values
    started_at: datetime | None = None
    completed_at: datetime | None = None


class EtoSubRunPipelineExecution(BaseModel):
    """
    Complete pipeline execution record as stored in the database.
    Represents the eto_sub_run_pipeline_executions table exactly.
    """
    model_config = ConfigDict(frozen=True)

    id: int
    sub_run_id: int
    status: str
    error_message: str | None
    transformed_data: str | None  # JSON string of output channel values
    started_at: datetime | None
    completed_at: datetime | None
    created_at: datetime
    updated_at: datetime
