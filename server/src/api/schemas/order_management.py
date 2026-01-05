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


class ConflictOptionSource(BaseModel):
    """A single source that contributed a value"""
    history_id: int
    sub_run_id: Optional[int] = None
    contributed_at: str  # ISO 8601


class ConflictOption(BaseModel):
    """A unique value option in a conflict, with all sources that contributed it"""
    value: str
    sources: List[ConflictOptionSource]
    # For backwards compatibility and convenience - use first source's history_id for selection
    history_id: int


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
    status: Literal["incomplete", "ready", "processing", "created", "failed", "rejected"]

    # HTC info (only set if status == 'created')
    # order_number is DOUBLE in Access but always whole numbers
    htc_order_number: Optional[int] = None
    htc_created_at: Optional[str] = None  # ISO 8601

    # Error info (only set if status == 'failed')
    error_message: Optional[str] = None
    error_at: Optional[str] = None  # ISO 8601

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
    sub_run_id: Optional[int] = None  # None for mock/test data
    run_id: Optional[int] = None  # None for mock/test data
    source_type: str  # "email", "manual", or "mock"
    source_identifier: str  # email sender, "Manual Upload", or "Mock Test Data"
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
    status: Literal["incomplete", "ready", "processing", "created", "failed", "rejected"]

    # HTC info (order_number is DOUBLE in Access but always whole numbers)
    htc_order_number: Optional[int] = None
    htc_created_at: Optional[str] = None

    # Error info (only set if status == 'failed')
    error_message: Optional[str] = None
    error_at: Optional[str] = None

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

class ConfirmFieldRequest(BaseModel):
    """Request to confirm/select a field value from history"""
    field_name: str
    history_id: int


class ConfirmFieldResponse(BaseModel):
    """Response after confirming a field selection"""
    success: bool
    field_name: str
    selected_value: str
    new_status: Literal["incomplete", "ready", "processing", "created", "failed", "rejected"]
    message: Optional[str] = None


# Legacy aliases for backwards compatibility
ResolveConflictRequest = ConfirmFieldRequest
ResolveConflictResponse = ConfirmFieldResponse


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


class RetryPendingOrderResponse(BaseModel):
    """Response after retrying a failed pending order"""
    success: bool
    pending_order_id: int
    new_status: str
    message: Optional[str] = None


class ApprovePendingOrderRequest(BaseModel):
    """Request to manually approve a pending order for HTC creation"""
    approver_username: str = Field(..., description="Staff_Login of the user approving (for audit trail)")


class ApprovePendingOrderResponse(BaseModel):
    """Response after manually approving a pending order"""
    success: bool
    pending_order_id: int
    htc_order_number: Optional[int] = None  # The created HTC order number
    new_status: str
    message: Optional[str] = None


class RejectPendingOrderRequest(BaseModel):
    """Request to reject a pending order"""
    reason: Optional[str] = Field(None, description="Optional reason for rejection")


class RejectPendingOrderResponse(BaseModel):
    """Response after rejecting a pending order"""
    success: bool
    pending_order_id: int
    new_status: str
    message: Optional[str] = None


# =============================================================================
# Pending Updates (for existing HTC orders)
# =============================================================================

class PendingUpdateListItem(BaseModel):
    """Pending update summary for list/table view - mirrors PendingOrderListItem"""
    id: int
    hawb: str
    customer_id: int
    customer_name: Optional[str] = None  # Resolved from Access DB
    htc_order_number: Optional[int] = None  # None when multiple HTC orders exist (manual_review)
    status: Literal["pending", "approved", "rejected", "manual_review"]

    # Field summary - count of fields being changed
    fields_with_changes: int  # Number of fields with proposed changes (non-NULL)
    conflict_count: int  # Number of fields with conflicting values

    # Source tracking
    contributing_sub_run_count: int

    # Timestamps
    created_at: str  # ISO 8601
    updated_at: str  # ISO 8601
    reviewed_at: Optional[str] = None


class GetPendingUpdatesResponse(BaseModel):
    """Response for GET /pending-updates"""
    items: List[PendingUpdateListItem]
    total: int
    limit: int
    offset: int


# =============================================================================
# Pending Update Detail
# =============================================================================

class PendingUpdateFieldDetail(BaseModel):
    """Detail for a single field in a pending update"""
    name: str
    label: str
    current_value: Optional[str] = None  # The current HTC value
    proposed_value: Optional[str] = None  # The proposed new value (NULL if conflict)
    state: Literal["empty", "set", "confirmed", "conflict"]
    # Only present if state == "conflict"
    conflict_options: Optional[List[ConflictOption]] = None
    # Source info (for set/confirmed states)
    source: Optional[FieldSource] = None


class PendingUpdateDetail(BaseModel):
    """Full pending update detail for single view"""
    id: int
    hawb: str
    customer_id: int
    customer_name: Optional[str] = None
    htc_order_number: Optional[int] = None  # None when multiple HTC orders exist (manual_review)
    status: Literal["pending", "approved", "rejected", "manual_review"]

    # All fields with their proposed changes
    fields: List[PendingUpdateFieldDetail]

    # Contributing sources
    contributing_sub_runs: List[ContributingSubRun]

    # Timestamps
    created_at: str
    updated_at: str
    reviewed_at: Optional[str] = None


# =============================================================================
# Pending Update Actions
# =============================================================================

class ApprovePendingUpdateRequest(BaseModel):
    """Request to approve a pending update"""
    approver_username: str  # Staff_Login of the user approving (for audit trail)


class ApprovePendingUpdateResponse(BaseModel):
    """Response after approving a pending update"""
    success: bool
    update_id: int
    htc_order_number: Optional[int] = None
    new_status: str
    fields_updated: List[str]  # Field names that were updated
    message: Optional[str] = None


class RejectPendingUpdateResponse(BaseModel):
    """Response after rejecting a pending update"""
    success: bool
    update_id: int
    new_status: str
    message: Optional[str] = None


class ConfirmUpdateFieldRequest(BaseModel):
    """Request to confirm/select a field value for a pending update"""
    field_name: str
    history_id: int


class ConfirmUpdateFieldResponse(BaseModel):
    """Response after confirming a field selection for pending update"""
    success: bool
    field_name: str
    selected_value: str
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
    "pickup_company_name": "Pickup Company",
    "pickup_address": "Pickup Address",
    "pickup_time_start": "Pickup Start Time",
    "pickup_time_end": "Pickup End Time",
    "pickup_notes": "Pickup Notes",
    "delivery_company_name": "Delivery Company",
    "delivery_address": "Delivery Address",
    "delivery_time_start": "Delivery Start Time",
    "delivery_time_end": "Delivery End Time",
    "delivery_notes": "Delivery Notes",
    "order_notes": "Order Notes",
    "mawb": "MAWB",
    "dims": "Dimensions",
}


def get_field_label(field_name: str) -> str:
    """Get human-readable label for a field name"""
    return FIELD_LABELS.get(field_name, field_name.replace("_", " ").title())


# =============================================================================
# Mock Output Processing (for testing)
# =============================================================================

class MockOutputProcessingRequest(BaseModel):
    """
    Request to mock pipeline output processing for testing.

    Simulates the effect of a full ETO pipeline run without
    actually processing a PDF. Useful for testing pending order
    workflows.
    """
    customer_id: int = Field(..., description="Customer ID (must exist in HTC)")
    hawb: str = Field(..., description="HAWB identifier")
    output_channel_data: Dict[str, Any] = Field(
        ...,
        description="Output channel data dict. Valid fields: pickup_company_name, pickup_address, "
                    "pickup_time_start, pickup_time_end, pickup_notes, delivery_company_name, "
                    "delivery_address, delivery_time_start, delivery_time_end, delivery_notes, "
                    "order_notes, mawb"
    )


class MockOutputProcessingResponse(BaseModel):
    """Response from mock output processing"""
    success: bool
    action: str  # "pending_order_created", "pending_order_updated", "pending_update_created", "pending_update_updated", "no_valid_fields"
    # For new orders (HAWB not in HTC)
    pending_order_id: Optional[int] = None
    pending_order_status: Optional[str] = None
    # For updates (HAWB exists in HTC)
    pending_update_id: Optional[int] = None
    htc_order_number: Optional[int] = None
    # Common fields
    fields_contributed: List[str] = []
    conflicts_introduced: List[str] = []
    message: Optional[str] = None


# =============================================================================
# Unified Action List (Combined Orders + Updates)
# =============================================================================

# Action types for unified list
ActionType = Literal["create", "update"]

# Combined status for unified filtering
# For creates: incomplete, ready, processing, created, failed
# For updates: pending, approved, rejected
UnifiedStatus = Literal[
    # Create statuses
    "incomplete", "ready", "processing", "created", "failed", "rejected",
    # Update statuses (rejected shared with create, manual_review unique to updates)
    "pending", "approved", "manual_review",
]


class UnifiedActionListItem(BaseModel):
    """
    A single item in the unified action list.
    Represents either a pending order (create) or pending update.
    """
    # Discriminator
    type: ActionType

    # Common identifiers
    id: int
    hawb: str
    customer_id: int
    customer_name: Optional[str] = None

    # HTC order number (always present for updates, only after creation for orders)
    htc_order_number: Optional[int] = None

    # Status (type-specific values)
    status: str

    # Read/unread state
    is_read: bool

    # Summary info
    # For creates: field progress counts
    # For updates: list of fields with changes
    required_fields_present: Optional[int] = None  # Creates only
    required_field_count: Optional[int] = None     # Creates only
    optional_fields_present: Optional[int] = None  # Creates only
    optional_field_count: Optional[int] = None     # Creates only
    fields_with_changes: Optional[List[str]] = None  # Updates only

    # Conflict info (both types)
    conflict_count: int = 0

    # Error info (creates only - failed status)
    error_message: Optional[str] = None

    # Timestamps
    last_processed_at: Optional[str] = None  # When actual processing occurred (not read/unread toggle)
    created_at: str
    updated_at: str


class UnifiedActionListResponse(BaseModel):
    """Paginated response for unified action list"""
    items: List[UnifiedActionListItem]
    total: int
    limit: int
    offset: int


class MarkReadRequest(BaseModel):
    """Request to mark item(s) as read/unread"""
    type: ActionType
    id: int
    is_read: bool


class MarkReadResponse(BaseModel):
    """Response after marking item as read/unread"""
    success: bool
    type: ActionType
    id: int
    is_read: bool
