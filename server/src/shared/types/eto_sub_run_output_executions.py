"""
ETO Sub-Run Output Execution Domain Types
Dataclasses representing eto_sub_run_output_executions table and related operations
"""
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Dict, Optional, TypedDict

# =========================
# ETO Sub-Run Output Execution Types
# =========================

@dataclass
class EtoSubRunOutputExecutionCreate:
    """
    Data required to create a new output execution record for a sub-run.

    This is created by the orchestrator after pipeline execution succeeds.
    The module_id and input_data come from the pipeline execution's return value.
    Status defaults to "pending" in the database.
    """
    sub_run_id: int
    module_id: str
    input_data: Dict[str, Any]  # Stored as JSON in DB


class EtoSubRunOutputExecutionUpdate(TypedDict, total=False):
    """
    Dict for updating an output execution record.
    All fields are optional - only provided fields will be updated.

    Uses dict keys to distinguish between:
    - Field not provided (key absent) - field will not be updated
    - Field set to None (key present, value None) - field will be cleared/nulled in database
    - Field set to value (key present, value set) - field will be updated to that value

    Note: input_data and result are Dict in domain but stored as JSON string in DB.
    Repository handles serialization.
    """
    status: str
    input_data: Dict[str, Any] | None
    result: Dict[str, Any] | None
    error_message: str | None
    error_type: str | None
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

    result format (from output service execution):
    {
        "order_number": 12345,
        "pdf_transferred_to": "\\\\server\\path\\12345.pdf",
        "database_inserts": {
            "orders": 1,
            "dimensions": 3
        }
    }
    """
    id: int
    sub_run_id: int
    module_id: str
    input_data: Dict[str, Any]
    status: str
    result: Optional[Dict[str, Any]]
    error_message: Optional[str]
    error_type: Optional[str]
    started_at: Optional[datetime]
    completed_at: Optional[datetime]
    created_at: datetime
    updated_at: datetime
