"""
ETO Sub-Run Output Execution Domain Types

Pydantic models representing eto_sub_run_output_executions table.
This table serves as a data snapshot of pipeline output - all processing
state tracking is handled by the pending_actions system.
"""
from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict


# =========================
# ETO Sub-Run Output Execution Types
# =========================

class EtoSubRunOutputExecutionCreate(BaseModel):
    """
    Data required to create a new output execution record.

    One record is created per HAWB (if pipeline returns multiple HAWBs,
    multiple records are created with the same output_channel_data).
    """
    model_config = ConfigDict(frozen=True)

    sub_run_id: int
    customer_id: int
    hawb: str
    output_channel_data: dict[str, Any]  # Stored as JSON in DB


class EtoSubRunOutputExecution(BaseModel):
    """
    Complete output execution record as stored in the database.

    Represents the eto_sub_run_output_executions table.
    The unique order identifier is (customer_id, hawb).
    """
    model_config = ConfigDict(frozen=True)

    id: int
    sub_run_id: int
    customer_id: int
    hawb: str
    output_channel_data: dict[str, Any]
    created_at: datetime
    updated_at: datetime
