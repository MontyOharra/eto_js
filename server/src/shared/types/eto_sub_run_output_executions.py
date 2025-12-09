"""
ETO Sub-Run Output Execution Domain Types
Dataclasses representing eto_sub_run_output_executions table and related operations
"""
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Dict, Literal, Optional, TypedDict

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

@dataclass
class EtoSubRunOutputExecutionCreate:
    """
    Data required to create a new output execution record.

    One record is created per HAWB (if pipeline returns multiple HAWBs,
    multiple records are created with the same output_channel_data).
    """
    sub_run_id: int
    customer_id: int
    hawb: str
    output_channel_data: Dict[str, Any]  # Stored as JSON in DB


class EtoSubRunOutputExecutionUpdate(TypedDict, total=False):
    """
    Dict for updating an output execution record.
    All fields are optional - only provided fields will be updated.
    """
    status: OutputExecutionStatus
    action_taken: str | None
    htc_order_number: float | None
    error_message: str | None
    error_type: str | None
    started_at: datetime | None
    completed_at: datetime | None


@dataclass
class EtoSubRunOutputExecution:
    """
    Complete output execution record as stored in the database.

    Represents the eto_sub_run_output_executions table.
    The unique order identifier is (customer_id, hawb).
    """
    id: int
    sub_run_id: int
    customer_id: int
    hawb: str
    output_channel_data: Dict[str, Any]
    status: OutputExecutionStatus
    action_taken: Optional[str]
    htc_order_number: Optional[float]
    error_message: Optional[str]
    error_type: Optional[str]
    started_at: Optional[datetime]
    completed_at: Optional[datetime]
    created_at: datetime
    updated_at: datetime
