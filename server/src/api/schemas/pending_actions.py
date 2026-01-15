"""
Pending Actions API Schemas

Pydantic models for pending actions list and detail endpoints.
"""
from datetime import datetime
from typing import Any

from pydantic import BaseModel

from shared.types.pending_actions import (
    PendingActionType,
    PendingActionStatus,
    OrderFieldDataType,
)


# =============================================================================
# List Response
# =============================================================================

class PendingActionListItem(BaseModel):
    """Pending action item for list view."""
    id: int
    customer_id: int
    customer_name: str | None
    hawb: str
    htc_order_number: float | None
    action_type: PendingActionType
    status: PendingActionStatus
    required_fields_present: int
    required_fields_total: int
    optional_fields_present: int
    optional_fields_total: int
    field_names: list[str]  # List of field names (for updates, shown as comma-separated)
    conflict_count: int
    is_read: bool
    created_at: datetime
    updated_at: datetime
    last_processed_at: datetime | None


class GetPendingActionsResponse(BaseModel):
    """Response for GET /pending-actions."""
    items: list[PendingActionListItem]
    total: int
    limit: int
    offset: int


# =============================================================================
# Detail Response
# =============================================================================

class PendingActionFieldItem(BaseModel):
    """
    Field value for detail view.

    Links to sub_run_id for frontend cross-highlighting between
    field rows and contributing source cards.
    """
    id: int
    field_name: str
    value: Any
    is_selected: bool
    is_approved_for_update: bool
    sub_run_id: int | None  # None for user-provided values


class ContributingSourceItem(BaseModel):
    """
    A source (sub-run) that contributed field values.

    Used for displaying source cards and cross-highlighting with fields.
    """
    sub_run_id: int
    pdf_filename: str
    template_name: str | None
    source_type: str  # "email" or "manual"
    source_identifier: str  # Email address or "Manual Upload"
    fields_contributed: list[str]
    contributed_at: datetime


class FieldMetadataItem(BaseModel):
    """
    Metadata for an order field.

    Sent with detail response so frontend knows how to display each field.
    """
    name: str              # Field identifier (e.g., "pickup_location")
    label: str             # Human-readable label (e.g., "Pickup Location")
    data_type: OrderFieldDataType  # "string", "location", or "dims"
    required: bool         # Required for order creation?
    display_order: int     # Order in which to display the field


class GetPendingActionDetailResponse(BaseModel):
    """Response for GET /pending-actions/{id}."""
    # Core action data
    id: int
    customer_id: int
    customer_name: str | None
    hawb: str
    htc_order_number: float | None
    action_type: PendingActionType
    status: PendingActionStatus
    required_fields_present: int
    required_fields_total: int
    optional_fields_present: int
    optional_fields_total: int
    conflict_count: int
    error_message: str | None
    error_at: datetime | None
    is_read: bool
    created_at: datetime
    updated_at: datetime
    last_processed_at: datetime | None

    # Field values grouped by field_name
    fields: dict[str, list[PendingActionFieldItem]]

    # Field metadata for display (labels, required, data_type, display_order)
    field_metadata: dict[str, FieldMetadataItem]

    # Contributing sources for cross-highlighting
    contributing_sources: list[ContributingSourceItem]

    # Current HTC values for updates (None for creates)
    current_htc_values: dict[str, Any] | None


# =============================================================================
# Set Read Status
# =============================================================================

class SetReadStatusRequest(BaseModel):
    """Request for PATCH /pending-actions/{id}/read-status."""
    is_read: bool


class SetReadStatusResponse(BaseModel):
    """Response for PATCH /pending-actions/{id}/read-status."""
    id: int
    is_read: bool


# =============================================================================
# Mock Data Creation
# =============================================================================

class CreateMockOutputRequest(BaseModel):
    """
    Request for POST /pending-actions/mock.

    Creates a mock output execution and processes it through the normal flow.
    """
    customer_id: int
    hawb: str
    output_channel_data: dict[str, Any]
    pdf_filename: str | None = None  # Defaults to "mock_document.pdf"


class CreateMockOutputResponse(BaseModel):
    """Response for POST /pending-actions/mock."""
    pending_action_id: int
    action_type: PendingActionType
    status: PendingActionStatus
    message: str


# =============================================================================
# Approve/Reject Actions
# =============================================================================

class ApproveActionRequest(BaseModel):
    """Request for POST /pending-actions/{id}/approve."""
    pass  # No additional data needed for now


class ApproveActionResponse(BaseModel):
    """Response for POST /pending-actions/{id}/approve."""
    pending_action_id: int
    success: bool
    action_type: PendingActionType
    htc_order_number: float | None
    new_status: PendingActionStatus
    message: str | None


class RejectActionRequest(BaseModel):
    """Request for POST /pending-actions/{id}/reject."""
    reason: str | None = None


class RejectActionResponse(BaseModel):
    """Response for POST /pending-actions/{id}/reject."""
    pending_action_id: int
    success: bool
    new_status: PendingActionStatus
    message: str | None


class SelectFieldValueRequest(BaseModel):
    """Request for POST /pending-actions/{id}/select-field."""
    field_id: int


class SelectFieldValueResponse(BaseModel):
    """Response for POST /pending-actions/{id}/select-field."""
    pending_action_id: int
    field_id: int
    field_name: str
    new_status: PendingActionStatus
    success: bool
    message: str | None


class SetFieldApprovalRequest(BaseModel):
    """Request for POST /pending-actions/{id}/set-field-approval."""
    field_name: str
    is_approved: bool


class SetFieldApprovalResponse(BaseModel):
    """Response for POST /pending-actions/{id}/set-field-approval."""
    pending_action_id: int
    field_name: str
    is_approved: bool
    success: bool
    message: str | None
