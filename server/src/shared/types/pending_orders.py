"""
Pending Orders Domain Types
Dataclasses representing pending_orders, pending_order_history, and pending_updates tables
"""
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Literal, Optional, TypedDict


# =========================
# Status Literals
# =========================

PendingOrderStatus = Literal[
    "incomplete",   # Missing one or more required fields
    "ready",        # All required fields present, queued for HTC creation
    "processing",   # Worker is currently creating HTC order
    "created",      # Successfully created in HTC
    "failed",       # HTC creation failed (see error_message)
]

PendingUpdateStatus = Literal[
    "pending",   # Awaiting user review
    "approved",  # User approved, applied to HTC
    "rejected",  # User rejected the change
]

# Field state computed from history
FieldState = Literal[
    "empty",      # No values received yet
    "set",        # Single value or all sources agree (auto-set)
    "conflict",   # Multiple different values, needs resolution
    "confirmed",  # User explicitly selected a value
]


# =========================
# Required Fields Configuration
# =========================

REQUIRED_FIELDS = [
    "pickup_company_name",
    "pickup_address",
    "pickup_time_start",
    "pickup_time_end",
    "delivery_company_name",
    "delivery_address",
    "delivery_time_start",
    "delivery_time_end",
]

# All valid field names for pending orders
VALID_FIELD_NAMES = [
    "pickup_company_name",
    "pickup_address",
    "pickup_time_start",
    "pickup_time_end",
    "pickup_notes",
    "delivery_company_name",
    "delivery_address",
    "delivery_time_start",
    "delivery_time_end",
    "delivery_notes",
    "order_notes",
    "mawb",
    "pieces",
    "weight",
]


# =========================
# Pending Order Types
# =========================

@dataclass
class PendingOrderCreate:
    """
    Data required to create a new pending order.
    """
    customer_id: int
    hawb: str


class PendingOrderUpdate(TypedDict, total=False):
    """
    Dict for updating a pending order record.
    All fields are optional - only provided fields will be updated.
    """
    status: PendingOrderStatus
    htc_order_number: float | None
    htc_created_at: datetime | None
    # Error tracking (for failed HTC creation)
    error_message: str | None
    error_at: datetime | None
    # Order fields
    pickup_company_name: str | None
    pickup_address: str | None
    pickup_time_start: str | None
    pickup_time_end: str | None
    delivery_company_name: str | None
    delivery_address: str | None
    delivery_time_start: str | None
    delivery_time_end: str | None
    mawb: str | None
    pickup_notes: str | None
    delivery_notes: str | None
    order_notes: str | None
    pieces: int | None
    weight: float | None


@dataclass
class PendingOrder:
    """
    Complete pending order record as stored in the database.
    """
    id: int
    customer_id: int
    hawb: str
    status: PendingOrderStatus
    htc_order_number: Optional[float]
    htc_created_at: Optional[datetime]
    # Error tracking (for failed HTC creation)
    error_message: Optional[str]
    error_at: Optional[datetime]
    # Required fields
    pickup_company_name: Optional[str]
    pickup_address: Optional[str]
    pickup_time_start: Optional[str]
    pickup_time_end: Optional[str]
    delivery_company_name: Optional[str]
    delivery_address: Optional[str]
    delivery_time_start: Optional[str]
    delivery_time_end: Optional[str]
    # Optional fields
    mawb: Optional[str]
    pickup_notes: Optional[str]
    delivery_notes: Optional[str]
    order_notes: Optional[str]
    pieces: Optional[int]
    weight: Optional[float]
    # Timestamps
    created_at: datetime
    updated_at: datetime


# =========================
# Pending Order History Types
# =========================

@dataclass
class PendingOrderHistoryCreate:
    """
    Data required to create a new history entry.
    """
    pending_order_id: int
    sub_run_id: int
    field_name: str
    field_value: str
    is_selected: bool = False


class PendingOrderHistoryUpdate(TypedDict, total=False):
    """
    Dict for updating a history entry.
    Typically only is_selected is updated (for conflict resolution).
    """
    is_selected: bool


@dataclass
class PendingOrderHistory:
    """
    Complete history entry as stored in the database.
    """
    id: int
    pending_order_id: int
    sub_run_id: Optional[int]  # Can be null if sub-run deleted
    field_name: str
    field_value: str
    is_selected: bool
    contributed_at: datetime


# =========================
# Pending Update Types
# =========================

@dataclass
class PendingUpdateCreate:
    """
    Data required to create a new pending update.
    """
    customer_id: int
    hawb: str
    htc_order_number: float
    sub_run_id: int
    field_name: str
    proposed_value: str


class PendingUpdateUpdate(TypedDict, total=False):
    """
    Dict for updating a pending update record.
    """
    status: PendingUpdateStatus
    reviewed_at: datetime | None


@dataclass
class PendingUpdate:
    """
    Complete pending update record as stored in the database.
    """
    id: int
    customer_id: int
    hawb: str
    htc_order_number: float
    sub_run_id: Optional[int]  # Can be null if sub-run deleted
    field_name: str
    proposed_value: str
    status: PendingUpdateStatus
    proposed_at: datetime
    reviewed_at: Optional[datetime]


# =========================
# Computed Field State Types
# =========================

@dataclass
class FieldSource:
    """
    Source information for a field value.
    """
    history_id: int
    sub_run_id: Optional[int]
    contributed_at: datetime


@dataclass
class FieldStateEmpty:
    """Field has no values yet."""
    state: Literal["empty"] = "empty"


@dataclass
class FieldStateSet:
    """Field has a single value (or all sources agree)."""
    state: Literal["set"] = "set"
    value: str = ""
    source: Optional[FieldSource] = None


@dataclass
class FieldStateConfirmed:
    """User explicitly selected a value."""
    state: Literal["confirmed"] = "confirmed"
    value: str = ""
    source: Optional[FieldSource] = None


@dataclass
class FieldStateConflict:
    """Multiple different values exist, needs resolution."""
    state: Literal["conflict"] = "conflict"
    options: List[Dict[str, Any]] = field(default_factory=list)


# Union type for field state
FieldStateResult = FieldStateEmpty | FieldStateSet | FieldStateConfirmed | FieldStateConflict


# =========================
# Processing Result Types
# =========================

@dataclass
class ProcessingResult:
    """
    Result of processing a single HAWB's output channel data.
    Returned by PendingOrdersService.process_output_channels().
    """
    hawb: str
    action: Literal[
        "pending_order_created",
        "pending_order_updated",
        "pending_updates_created",
        "order_created",
    ]
    # Set when action involves pending_order
    pending_order_id: Optional[int] = None
    # Set when action='pending_updates_created'
    pending_update_ids: Optional[List[int]] = None
    # Set when action='order_created'
    htc_order_number: Optional[float] = None
    # Fields that were added to history
    fields_contributed: List[str] = field(default_factory=list)
    # Any conflicts introduced by this contribution
    conflicts_introduced: List[str] = field(default_factory=list)
