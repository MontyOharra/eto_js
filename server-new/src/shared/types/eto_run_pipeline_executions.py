"""
ETO Run Pipeline Execution Domain Types
Dataclasses representing eto_run_pipeline_executions table and related operations
"""
from dataclasses import dataclass
from datetime import datetime
from typing import Literal, Optional

# =========================
# ETO Run Pipeline Execution Types
# =========================

@dataclass
class EtoRunPipelineExecutionCreate:
    """
    Data required to create a new pipeline execution record.
    Status defaults to "processing" in the database.
    """
    eto_run_id: int
    started_at: Optional[datetime] = None


@dataclass
class EtoRunPipelineExecutionUpdate:
    """
    Data for updating a pipeline execution record.
    All fields are optional - only provided fields will be updated.
    """
    status: Optional[str] = None
    executed_actions: Optional[str] = None
    completed_at: Optional[datetime] = None


@dataclass
class EtoRunPipelineExecution:
    """
    Complete pipeline execution record as stored in the database.
    Represents the eto_run_pipeline_executions table exactly.
    """
    id: int
    eto_run_id: int
    status: str
    executed_actions: Optional[str]
    started_at: Optional[datetime]
    completed_at: Optional[datetime]
    created_at: datetime
    updated_at: datetime
