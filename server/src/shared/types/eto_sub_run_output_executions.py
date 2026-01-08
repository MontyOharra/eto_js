"""
ETO Sub-Run Output Execution Domain Types
Pydantic models representing eto_sub_run_output_executions table and related operations
"""
from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict


# =========================
# Status Literal
# =========================

OutputExecutionStatus = Literal[
    "pending",     # Record created, not yet started
    "processing",  # Actively processing
    "success",     # Completed successfully
    "error",       # Failed
]

# Action taken after processing
ActionTaken = Literal[
    "pending_order_created",   # New pending order created
    "pending_order_updated",   # Added to existing pending order
    "pending_updates_created", # HAWB exists in HTC, queued updates for approval
    "order_created",           # Pending order was complete, created in HTC
]


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


class EtoSubRunOutputExecutionUpdate(BaseModel):
    """
    Data for updating an output execution record.

    Uses Pydantic's model_fields_set to distinguish between:
    - Field not provided: not in model_fields_set (don't update)
    - Field set to None: in model_fields_set with None value (set NULL)
    - Field set to value: in model_fields_set with value (update)
    """
    status: OutputExecutionStatus | None = None
    action_taken: str | None = None
    htc_order_number: float | None = None
    error_message: str | None = None
    error_type: str | None = None
    started_at: datetime | None = None
    completed_at: datetime | None = None


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
    status: OutputExecutionStatus
    action_taken: str | None
    htc_order_number: float | None
    error_message: str | None
    error_type: str | None
    started_at: datetime | None
    completed_at: datetime | None
    created_at: datetime
    updated_at: datetime
