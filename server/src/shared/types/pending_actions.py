"""
Pending Actions Domain Types

Pydantic models for the unified pending actions system that handles both
order creation and order updates. Replaces the old pending_orders and
pending_updates separate systems.

Key concepts:
- PendingAction: Main record tracking an order action (create or update)
- PendingActionField: Individual field values with conflict resolution support
- Action type determined at execution time, not accumulation time (TOCTOU protection)
"""
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict


# =========================
# Status Types
# =========================

PendingActionType = Literal["create", "update", "ambiguous"]
"""
Action type for pending actions:
- create: No existing HTC order for this (customer_id, hawb)
- update: One existing HTC order found
- ambiguous: Multiple HTC orders found, user must specify which one
"""

PendingActionStatus = Literal[
    "incomplete",    # Missing required fields
    "conflict",      # Has unresolved field conflicts
    "ambiguous",     # Multiple HTC orders exist (action_type='ambiguous')
    "ready",         # Ready for execution (auto or manual)
    "processing",    # Currently executing against HTC
    "completed",     # Successfully executed
    "failed",        # Execution failed (retryable)
    "rejected",      # User rejected the action
]
"""
Status flow:
- incomplete → (fields added) → conflict/ambiguous/ready
- ready → processing → completed/failed
- failed → ready (on retry)
- Any non-terminal → rejected (user action)
"""


# =========================
# Order Field Definitions
# =========================

OrderFieldDataType = Literal["string", "location", "dims", "datetime_range"]
"""
Data types for order fields:
- string: Simple string value (1:1 mapping from output channel)
- location: Complex JSON with address_id, name, address (resolved from company_name + address channels)
- dims: JSON array of dimension objects with calculated dim_weight
- datetime_range: Date + time range from two datetime inputs (validates dates match)
"""


@dataclass(frozen=True)
class OrderFieldDef:
    """
    Definition of an order field and its mapping from output channels.

    Used to transform pipeline output channels into order fields for HTC.
    """
    name: str                    # Field identifier (e.g., "pickup_location")
    label: str                   # Human-readable label (e.g., "Pickup Location")
    data_type: OrderFieldDataType
    required: bool               # Required for order creation?
    source_channels: tuple[str, ...]  # Output channels that feed this field
    display_order: int           # Order in which to display the field (lower = first)


# Order field definitions - maps output channels to order fields
# display_order groups: Pickup (1-19), Delivery (20-39), Other (40+)
ORDER_FIELDS: dict[str, OrderFieldDef] = {
    # Pickup fields
    "pickup_location": OrderFieldDef(
        "pickup_location", "Pickup Location", "location", True,
        ("pickup_address_id", "pickup_company_name", "pickup_address"), 1
    ),
    "pickup_datetime": OrderFieldDef(
        "pickup_datetime", "Pickup Time", "datetime_range", True,
        ("pickup_time_start", "pickup_time_end"), 2
    ),
    "pickup_notes": OrderFieldDef("pickup_notes", "Pickup Notes", "string", False, ("pickup_notes",), 3),

    # Delivery fields
    "delivery_location": OrderFieldDef(
        "delivery_location", "Delivery Location", "location", True,
        ("delivery_address_id", "delivery_company_name", "delivery_address"), 20
    ),
    "delivery_datetime": OrderFieldDef(
        "delivery_datetime", "Delivery Time", "datetime_range", True,
        ("delivery_time_start", "delivery_time_end"), 21
    ),
    "delivery_notes": OrderFieldDef("delivery_notes", "Delivery Notes", "string", False, ("delivery_notes",), 22),

    # Other fields
    "mawb": OrderFieldDef("mawb", "MAWB", "string", False, ("mawb",), 40),
    "order_notes": OrderFieldDef("order_notes", "Order Notes", "string", False, ("order_notes",), 41),
    "dims": OrderFieldDef("dims", "Dimensions", "dims", False, ("dims",), 42),
}

REQUIRED_ORDER_FIELDS: list[str] = [f.name for f in ORDER_FIELDS.values() if f.required]
OPTIONAL_ORDER_FIELDS: list[str] = [f.name for f in ORDER_FIELDS.values() if not f.required]
VALID_ORDER_FIELD_NAMES: list[str] = list(ORDER_FIELDS.keys())


# =========================
# Location Field Structure
# =========================

class LocationValue(BaseModel):
    """
    Resolved location field value.

    Stored as JSON in pending_action_fields.value for location-type fields.
    """
    model_config = ConfigDict(frozen=True)

    address_id: int | None  # HTC address ID if matched, None if new address needed
    name: str               # Company name
    address: str            # Full address string


# =========================
# Dims Field Structure
# =========================

class DimObject(BaseModel):
    """
    Single dimension entry.

    Stored as JSON array in pending_action_fields.value for dims field.
    """
    model_config = ConfigDict(frozen=True)

    length: float
    width: float
    height: float
    qty: int
    weight: float
    dim_weight: float  # Calculated: L*W*H/144


# =========================
# Datetime Range Field Structure
# =========================

class DatetimeRangeValue(BaseModel):
    """
    Date + time range for pickup/delivery windows.

    Created from two datetime inputs (e.g., pickup_time_start, pickup_time_end).
    Validates that both datetimes are on the same date.

    Stored as JSON in pending_action_fields.value for datetime_range fields.
    """
    model_config = ConfigDict(frozen=True)

    date: str          # Date portion: "2024-01-15"
    time_start: str    # Start time: "09:00"
    time_end: str      # End time: "17:00"


class DatetimeRangeError(Exception):
    """Raised when datetime range validation fails (e.g., different dates)."""
    pass


# =========================
# Pending Action Types
# =========================

class PendingActionCreate(BaseModel):
    """
    Data required to create a new pending action.

    Created when first sub-run output is processed for a (customer_id, hawb) pair.
    """
    model_config = ConfigDict(frozen=True)

    customer_id: int
    hawb: str
    action_type: PendingActionType
    htc_order_number: float | None = None  # Set for updates


class PendingActionUpdate(BaseModel):
    """
    Data for updating a pending action.

    Uses Pydantic's model_fields_set to distinguish between:
    - Field not provided: not in model_fields_set (don't update)
    - Field set to None: in model_fields_set with None value (set NULL)
    - Field set to value: in model_fields_set with value (update)
    """
    action_type: PendingActionType | None = None
    htc_order_number: float | None = None
    status: PendingActionStatus | None = None
    required_fields_present: int | None = None
    optional_fields_present: int | None = None
    conflict_count: int | None = None
    error_message: str | None = None
    error_at: datetime | None = None
    is_read: bool | None = None
    last_processed_at: datetime | None = None


class PendingAction(BaseModel):
    """
    Complete pending action record as stored in the database.
    Represents the pending_actions table exactly.
    """
    model_config = ConfigDict(frozen=True)

    id: int
    customer_id: int
    hawb: str
    htc_order_number: float | None
    action_type: PendingActionType
    status: PendingActionStatus
    required_fields_present: int
    optional_fields_present: int
    conflict_count: int
    error_message: str | None
    error_at: datetime | None
    is_read: bool
    created_at: datetime
    updated_at: datetime
    last_processed_at: datetime | None


# =========================
# Pending Action Field Types
# =========================

class PendingActionFieldCreate(BaseModel):
    """
    Data required to create a new pending action field entry.

    Created when an output execution contributes a field value, or when user
    provides a manual value (output_execution_id=None).
    """
    model_config = ConfigDict(frozen=True)

    pending_action_id: int
    output_execution_id: int | None  # None for user-provided values
    field_name: str
    value: Any  # JSON - string, dict, or list depending on field type
    is_selected: bool = False
    is_approved_for_update: bool = True


class PendingActionFieldUpdate(BaseModel):
    """
    Data for updating a pending action field.

    Primarily used for:
    - Setting is_selected during conflict resolution
    - Setting is_approved_for_update for partial updates
    """
    is_selected: bool | None = None
    is_approved_for_update: bool | None = None


class PendingActionField(BaseModel):
    """
    Complete pending action field record as stored in the database.
    Represents the pending_action_fields table exactly.
    """
    model_config = ConfigDict(frozen=True)

    id: int
    pending_action_id: int
    output_execution_id: int | None  # None = user-provided value
    field_name: str
    value: Any  # JSON - string, dict, or list depending on field type
    is_selected: bool
    is_approved_for_update: bool


# =========================
# View Types (for API responses)
# =========================

class PendingActionFieldView(BaseModel):
    """
    Field value with source information for UI display.

    Used in detail views to show all values for a field with their sources.
    Links directly to sub_run_id for frontend cross-highlighting between
    field rows and contributing source cards.
    """
    model_config = ConfigDict(frozen=True)

    id: int
    field_name: str
    value: Any
    is_selected: bool
    is_approved_for_update: bool
    sub_run_id: int | None  # Resolved from output_execution, None for user-provided


class PendingActionListView(BaseModel):
    """
    Pending action with summary info for list display.

    Used by GET /api/pending-actions list endpoint.
    """
    model_config = ConfigDict(frozen=True)

    id: int
    customer_id: int
    customer_name: str | None  # Enriched from HTC
    hawb: str
    htc_order_number: float | None
    action_type: PendingActionType
    status: PendingActionStatus
    required_fields_present: int
    required_fields_total: int  # len(REQUIRED_ORDER_FIELDS) - for display like "2/8"
    optional_fields_present: int
    optional_fields_total: int  # len(OPTIONAL_ORDER_FIELDS) - for display like "1/4"
    conflict_count: int
    is_read: bool
    created_at: datetime
    updated_at: datetime
    last_processed_at: datetime | None


class ContributingSource(BaseModel):
    """
    A source (sub-run) that contributed field values to a pending action.

    Used in detail views to show where data came from and enable
    cross-highlighting between field rows and source cards.
    """
    model_config = ConfigDict(frozen=True)

    sub_run_id: int
    pdf_filename: str
    template_name: str | None  # None if no template matched
    source_type: str  # "email" or "manual"
    source_identifier: str  # Email address or "Manual Upload"
    fields_contributed: list[str]  # Field names this source contributed
    contributed_at: datetime


class PendingActionDetailView(BaseModel):
    """
    Complete pending action with all field values for detail display.

    Used by GET /api/pending-actions/{id} endpoint.
    """
    model_config = ConfigDict(frozen=True)

    # Core action data
    id: int
    customer_id: int
    customer_name: str | None  # Enriched from HTC
    hawb: str
    htc_order_number: float | None
    action_type: PendingActionType
    status: PendingActionStatus
    required_fields_present: int
    required_fields_total: int  # len(REQUIRED_ORDER_FIELDS) - for display like "2/8"
    optional_fields_present: int
    optional_fields_total: int  # len(OPTIONAL_ORDER_FIELDS) - for display like "1/4"
    conflict_count: int
    error_message: str | None
    error_at: datetime | None
    is_read: bool
    created_at: datetime
    updated_at: datetime
    last_processed_at: datetime | None

    # All field values grouped by field_name
    # Each field may have multiple values (for conflict resolution display)
    fields: dict[str, list[PendingActionFieldView]]

    # Contributing sources for cross-highlighting with fields
    contributing_sources: list[ContributingSource]

    # Current HTC values for updates (None for creates)
    # Used to show "Current → Proposed" comparison in update detail view
    current_htc_values: dict[str, Any] | None


# =========================
# Service Result Types
# =========================

class CleanupResult(BaseModel):
    """
    Result of cleanup_output_execution_contributions operation.

    Returned when an output execution is reprocessed or deleted.
    """
    model_config = ConfigDict(frozen=True)

    output_execution_id: int
    affected_action_ids: list[int]  # Actions that had fields removed
    deleted_action_ids: list[int]   # Actions that were fully deleted (no extracted fields remaining)
    fields_removed_count: int


class ExecuteResult(BaseModel):
    """
    Result of execute_action operation.

    Returned when attempting to create/update an order in HTC.
    """
    model_config = ConfigDict(frozen=True)

    pending_action_id: int
    success: bool
    action_type: PendingActionType
    htc_order_number: float | None  # Set on successful create
    error_message: str | None
