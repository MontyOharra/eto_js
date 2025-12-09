"""
Order Management API Schemas
Pydantic models for pending orders and pending updates endpoints
"""
from typing import Optional, List, Dict, Any, Literal
from pydantic import BaseModel, Field


# =============================================================================
# Field State Types
# =============================================================================

class FieldSource(BaseModel):
    """Source information for a field value"""
    history_id: int
    sub_run_id: Optional[int] = None
    contributed_at: str  # ISO 8601


class FieldStateEmpty(BaseModel):
    """Field has no values yet"""
    state: Literal["empty"] = "empty"


class FieldStateSet(BaseModel):
    """Field has a single value (or all sources agree)"""
    state: Literal["set"] = "set"
    value: str
    source: Optional[FieldSource] = None


class FieldStateConfirmed(BaseModel):
    """User explicitly selected a value"""
    state: Literal["confirmed"] = "confirmed"
    value: str
    source: Optional[FieldSource] = None


class ConflictOption(BaseModel):
    """A single option in a conflict"""
    history_id: int
    value: str
    sub_run_id: Optional[int] = None
    contributed_at: str  # ISO 8601


class FieldStateConflict(BaseModel):
    """Multiple different values exist, needs resolution"""
    state: Literal["conflict"] = "conflict"
    options: List[ConflictOption]


# =============================================================================
# Pending Order List Item (for table)
# =============================================================================

class PendingOrderListItem(BaseModel):
    """Pending order summary for list/table view"""
    id: int
    hawb: str
    customer_id: int
    customer_name: Optional[str] = None  # Resolved from Access DB
    status: Literal["incomplete", "ready", "created"]

    # HTC info (only set if status == 'created')
    htc_order_number: Optional[float] = None
    htc_created_at: Optional[str] = None  # ISO 8601

    # Field completion summary
    required_field_count: int
    required_fields_present: int
    optional_field_count: int
    optional_fields_present: int
    conflict_count: int

    # Source tracking
    contributing_sub_run_count: int

    # Timestamps
    created_at: str  # ISO 8601
    updated_at: str  # ISO 8601


class GetPendingOrdersResponse(BaseModel):
    """Response for GET /pending-orders"""
    items: List[PendingOrderListItem]
    total: int
    limit: int
    offset: int


# =============================================================================
# Pending Order Detail
# =============================================================================

class FieldDetail(BaseModel):
    """Detailed field information including state and history"""
    name: str
    label: str
    required: bool
    value: Optional[str] = None
    state: Literal["empty", "set", "confirmed", "conflict"]
    # Only present if state == "conflict"
    conflict_options: Optional[List[ConflictOption]] = None
    # Source info (for set/confirmed states)
    source: Optional[FieldSource] = None


class ContributingSubRun(BaseModel):
    """Information about a sub-run that contributed to this order"""
    sub_run_id: int
    run_id: int
    pdf_filename: str
    template_name: Optional[str] = None
    fields_contributed: List[str]
    contributed_at: str  # ISO 8601


class PendingOrderDetail(BaseModel):
    """Full pending order detail for single view"""
    id: int
    hawb: str
    customer_id: int
    customer_name: Optional[str] = None
    status: Literal["incomplete", "ready", "created"]

    # HTC info
    htc_order_number: Optional[float] = None
    htc_created_at: Optional[str] = None

    # All fields with their states
    fields: List[FieldDetail]

    # Contributing sources
    contributing_sub_runs: List[ContributingSubRun]

    # Timestamps
    created_at: str
    updated_at: str


# =============================================================================
# Pending Order Actions
# =============================================================================

class ResolveConflictRequest(BaseModel):
    """Request to resolve a field conflict"""
    field_name: str
    selected_history_id: int


class ResolveConflictResponse(BaseModel):
    """Response after resolving a conflict"""
    success: bool
    field_name: str
    selected_value: str
    new_status: Literal["incomplete", "ready", "created"]


class CreateOrderRequest(BaseModel):
    """Request to create order in HTC from pending order"""
    # No body needed for now - uses pending order data as-is
    pass


class CreateOrderResponse(BaseModel):
    """Response after creating order in HTC"""
    success: bool
    pending_order_id: int
    htc_order_number: float
    message: Optional[str] = None


# =============================================================================
# Pending Updates (for existing HTC orders)
# =============================================================================

class PendingUpdateListItem(BaseModel):
    """Pending update summary for list/table view"""
    id: int
    customer_id: int
    hawb: str
    htc_order_number: float
    customer_name: Optional[str] = None

    # The proposed change
    field_name: str
    field_label: str
    proposed_value: str

    # Source info
    sub_run_id: Optional[int] = None

    # Status
    status: Literal["pending", "approved", "rejected"]

    # Timestamps
    proposed_at: str  # ISO 8601
    reviewed_at: Optional[str] = None


class GetPendingUpdatesResponse(BaseModel):
    """Response for GET /pending-updates"""
    items: List[PendingUpdateListItem]
    total: int
    limit: int
    offset: int


class ApprovePendingUpdateResponse(BaseModel):
    """Response after approving a pending update"""
    success: bool
    update_id: int
    new_status: str
    message: Optional[str] = None


class RejectPendingUpdateResponse(BaseModel):
    """Response after rejecting a pending update"""
    success: bool
    update_id: int
    new_status: str
    message: Optional[str] = None


class BulkUpdateActionRequest(BaseModel):
    """Request for bulk approve/reject"""
    update_ids: List[int]


class BulkUpdateActionResponse(BaseModel):
    """Response for bulk operations"""
    success_count: int
    failure_count: int
    results: List[Dict[str, Any]]


# =============================================================================
# Field Label Mapping
# =============================================================================

FIELD_LABELS: Dict[str, str] = {
    "pickup_address": "Pickup Address",
    "pickup_time_start": "Pickup Start Time",
    "pickup_time_end": "Pickup End Time",
    "pickup_notes": "Pickup Notes",
    "delivery_address": "Delivery Address",
    "delivery_time_start": "Delivery Start Time",
    "delivery_time_end": "Delivery End Time",
    "delivery_notes": "Delivery Notes",
    "order_notes": "Order Notes",
    "mawb": "MAWB",
    "pieces": "Pieces",
    "weight": "Weight",
}


def get_field_label(field_name: str) -> str:
    """Get human-readable label for a field name"""
    return FIELD_LABELS.get(field_name, field_name.replace("_", " ").title())
