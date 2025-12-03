"""
ETO Sub-Run Pipeline Execution Domain Types
Dataclasses representing eto_sub_run_pipeline_executions table and related operations
"""
from dataclasses import dataclass
from datetime import datetime
from typing import Literal, Optional, TypedDict

# =========================
# ETO Sub-Run Pipeline Execution Types
# =========================

@dataclass
class EtoSubRunPipelineExecutionCreate:
    """
    Data required to create a new pipeline execution record for a sub-run.
    Status defaults to "processing" in the database.
    """
    sub_run_id: int
    started_at: Optional[datetime] = None


class EtoSubRunPipelineExecutionUpdate(TypedDict, total=False):
    """
    Dict for updating a pipeline execution record.
    All fields are optional - only provided fields will be updated.

    Uses dict keys to distinguish between:
    - Field not provided (key absent) - field will not be updated
    - Field set to None (key present, value None) - field will be cleared/nulled in database
    - Field set to value (key present, value set) - field will be updated to that value
    """
    status: str
    error_message: str | None
    started_at: datetime | None
    completed_at: datetime | None


@dataclass
class EtoSubRunPipelineExecution:
    """
    Complete pipeline execution record as stored in the database.
    Represents the eto_sub_run_pipeline_executions table exactly.
    """
    id: int
    sub_run_id: int
    status: str
    error_message: Optional[str]
    started_at: Optional[datetime]
    completed_at: Optional[datetime]
    created_at: datetime
    updated_at: datetime
