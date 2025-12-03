"""
ETO Sub-Run Output Execution Domain Types
Dataclasses representing eto_sub_run_output_executions table and related operations
"""
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Dict, Literal, Optional, TypedDict

# =========================
# Status and Action Type Literals
# =========================

OutputExecutionStatus = Literal[
    "pending",            # Record created, not yet started
    "processing",         # Actively checking HAWB or executing create/update
    "awaiting_approval",  # HAWB found once, needs user approval for update
    "success",            # Completed successfully (order created or updated)
    "rejected",           # User rejected the update
    "error",              # Failed (multiple HAWBs, DB error, etc.)
]

ActionType = Literal["create", "update"]


# =========================
# ETO Sub-Run Output Execution Types
# =========================

@dataclass
class EtoSubRunOutputExecutionCreate:
    """
    Data required to create a new output execution record for a sub-run.

    This is created by PipelineResultService after pipeline execution succeeds.
    The module_id and input_data come from the pipeline execution's return value.
    HAWB is extracted from input_data for easy querying.
    Status defaults to "pending" in the database.
    """
    sub_run_id: int
    module_id: str
    input_data: Dict[str, Any]  # Stored as JSON in DB
    hawb: str  # Extracted from input_data


class EtoSubRunOutputExecutionUpdate(TypedDict, total=False):
    """
    Dict for updating an output execution record.
    All fields are optional - only provided fields will be updated.

    Uses dict keys to distinguish between:
    - Field not provided (key absent) - field will not be updated
    - Field set to None (key present, value None) - field will be cleared/nulled in database
    - Field set to value (key present, value set) - field will be updated to that value

    Note: input_data, result, and existing_order_data are Dict in domain but stored as JSON string in DB.
    Repository handles serialization.
    """
    status: OutputExecutionStatus
    action_type: ActionType | None
    input_data: Dict[str, Any] | None
    result: Dict[str, Any] | None
    error_message: str | None
    error_type: str | None
    existing_order_number: int | None
    existing_order_data: Dict[str, Any] | None
    started_at: datetime | None
    completed_at: datetime | None


@dataclass
class EtoSubRunOutputExecution:
    """
    Complete output execution record as stored in the database.

    Represents the eto_sub_run_output_executions table.

    input_data format (from output module inputs):
    {
        "customer_id": 123,
        "hawb": "12345678",
        "pickup_address_id": 456,
        ...
    }

    result format for successful create:
    {
        "action": "create",
        "order_number": 12345,
        "hawb": "ABC123",
        "customer_id": 5,
        "email_sent": true,
        "email_recipient": "sender@example.com"
    }

    result format for successful update:
    {
        "action": "update",
        "order_number": 12345,
        "hawb": "ABC123",
        "fields_updated": ["pickup_time_start", "pickup_time_end"],
        "email_sent": true,
        "email_recipient": "sender@example.com"
    }

    existing_order_data format (snapshot for comparison UI):
    {
        "OrderNumber": 12345,
        "HAWB": "ABC123",
        "CustomerID": 5,
        "PickupTimeStart": "08:00",
        ...
    }
    """
    id: int
    sub_run_id: int
    module_id: str
    input_data: Dict[str, Any]
    hawb: str
    status: OutputExecutionStatus
    action_type: Optional[ActionType]
    existing_order_number: Optional[int]
    existing_order_data: Optional[Dict[str, Any]]
    result: Optional[Dict[str, Any]]
    error_message: Optional[str]
    error_type: Optional[str]
    started_at: Optional[datetime]
    completed_at: Optional[datetime]
    created_at: datetime
    updated_at: datetime
