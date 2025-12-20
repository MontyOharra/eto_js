"""
Order Management FastAPI Router
REST endpoints for pending orders and pending updates
"""
import asyncio
import json
import logging
from datetime import datetime
from typing import Optional, Literal
from fastapi import APIRouter, Query, Depends, HTTPException, status, Request
from fastapi.responses import StreamingResponse

from shared.events.order_events import order_event_manager

from api.schemas.order_management import (
    # Pending Orders
    GetPendingOrdersResponse,
    PendingOrderListItem,
    PendingOrderDetail,
    ConfirmFieldRequest,
    ConfirmFieldResponse,
    CreateOrderResponse,
    RetryPendingOrderResponse,
    # Pending Updates
    GetPendingUpdatesResponse,
    PendingUpdateListItem,
    PendingUpdateDetail,
    PendingUpdateFieldDetail,
    ApprovePendingUpdateRequest,
    ApprovePendingUpdateResponse,
    RejectPendingUpdateResponse,
    ConfirmUpdateFieldRequest,
    ConfirmUpdateFieldResponse,
    BulkUpdateActionRequest,
    BulkUpdateActionResponse,
    # Unified Action List
    UnifiedActionListItem,
    UnifiedActionListResponse,
    MarkReadRequest,
    MarkReadResponse,
    ActionType,
    # Field state types
    FieldSource,
    ConflictOption,
    ContributingSubRun,
    # Mock Testing
    MockOutputProcessingRequest,
    MockOutputProcessingResponse,
    # Helpers
    get_field_label,
    FIELD_LABELS,
)
from api.mappers.order_management import map_pending_order_detail_to_api
from shared.services.service_container import ServiceContainer
from shared.types.pending_orders import REQUIRED_FIELDS, VALID_FIELD_NAMES

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/order-management",
    tags=["Order Management"]
)


# =============================================================================
# Unified Actions Endpoint (Orders + Updates)
# =============================================================================

@router.get("/unified-actions", response_model=UnifiedActionListResponse)
async def list_unified_actions(
    type_filter: Optional[Literal["create", "update"]] = Query(
        None,
        description="Filter by type (create = pending orders, update = pending updates)",
        alias="type",
    ),
    status_filter: Optional[str] = Query(
        None,
        description="Filter by status. Creates: incomplete,ready,processing,created,failed. Updates: pending,approved,rejected",
        alias="status",
    ),
    is_read_filter: Optional[bool] = Query(
        None,
        description="Filter by read/unread status",
        alias="is_read",
    ),
    limit: int = Query(50, ge=1, le=100, description="Page size"),
    offset: int = Query(0, ge=0, description="Offset for pagination"),
    service = Depends(lambda: ServiceContainer.get_order_management_service()),
    htc_service = Depends(lambda: ServiceContainer.get_htc_integration_service())
) -> UnifiedActionListResponse:
    """
    Get unified list of pending orders (creates) and pending updates.

    Returns both types in a single list, sorted by updated_at descending (most recent first).
    Supports filtering by type, status, and read/unread state.

    Query Parameters:
    - type: Filter by "create" (pending orders) or "update" (pending updates)
    - status: Filter by status value (validates against type)
    - is_read: Filter by read/unread state (true/false)
    - limit: Page size (default 50, max 100)
    - offset: Pagination offset
    """
    logger.debug(f"List unified actions: type={type_filter}, status={status_filter}, is_read={is_read_filter}")

    # Validate status filter against type
    create_statuses = {"incomplete", "ready", "processing", "created", "failed"}
    update_statuses = {"pending", "approved", "rejected"}

    if status_filter:
        if type_filter == "create" and status_filter not in create_statuses:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid status '{status_filter}' for type 'create'. Valid: {create_statuses}"
            )
        if type_filter == "update" and status_filter not in update_statuses:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid status '{status_filter}' for type 'update'. Valid: {update_statuses}"
            )

    items = []
    total = 0

    # Get repositories
    pending_order_repo = service._pending_order_repo
    pending_order_history_repo = service._pending_order_history_repo
    pending_update_repo = service._pending_update_repo
    pending_update_history_repo = service._pending_update_history_repo

    # Collect pending orders if not filtered to updates only
    if type_filter != "update":
        orders = pending_order_repo.list_all()

        # Apply status filter
        if status_filter and status_filter in create_statuses:
            orders = [o for o in orders if o.status == status_filter]

        # Apply is_read filter
        if is_read_filter is not None:
            orders = [o for o in orders if o.is_read == is_read_filter]

        for order in orders:
            # Get history for conflict counting
            history = pending_order_history_repo.get_by_pending_order_id(order.id)
            by_field = {}
            for h in history:
                if h.field_name not in by_field:
                    by_field[h.field_name] = []
                by_field[h.field_name].append(h)

            # Count conflicts and field completeness
            conflict_count = 0
            required_present = 0
            optional_present = 0

            for field_name in VALID_FIELD_NAMES:
                field_history = by_field.get(field_name, [])
                current_value = getattr(order, field_name, None)

                # Check for conflict
                if len(field_history) > 1:
                    unique_values = set(h.field_value for h in field_history)
                    if len(unique_values) > 1 and not any(h.is_selected for h in field_history):
                        conflict_count += 1

                # Count present fields
                if current_value is not None:
                    if field_name in REQUIRED_FIELDS:
                        required_present += 1
                    else:
                        optional_present += 1

            # Get customer name
            customer_name = htc_service.get_customer_name(order.customer_id)

            items.append(UnifiedActionListItem(
                type="create",
                id=order.id,
                hawb=order.hawb,
                customer_id=order.customer_id,
                customer_name=customer_name,
                htc_order_number=int(order.htc_order_number) if order.htc_order_number else None,
                status=order.status,
                is_read=order.is_read,
                required_fields_present=required_present,
                required_field_count=len(REQUIRED_FIELDS),
                optional_fields_present=optional_present,
                optional_field_count=len(VALID_FIELD_NAMES) - len(REQUIRED_FIELDS),
                conflict_count=conflict_count,
                error_message=order.error_message,
                last_processed_at=order.last_processed_at.isoformat() if order.last_processed_at else None,
                created_at=order.created_at.isoformat(),
                updated_at=order.updated_at.isoformat(),
            ))

    # Collect pending updates if not filtered to creates only
    if type_filter != "create":
        updates, _ = pending_update_repo.list_all()

        # Apply status filter
        if status_filter and status_filter in update_statuses:
            updates = [u for u in updates if u.status == status_filter]

        # Apply is_read filter
        if is_read_filter is not None:
            updates = [u for u in updates if u.is_read == is_read_filter]

        for update in updates:
            # Get history for conflict counting and fields with changes
            history = pending_update_history_repo.get_by_pending_update_id(update.id)
            by_field = {}
            for h in history:
                if h.field_name not in by_field:
                    by_field[h.field_name] = []
                by_field[h.field_name].append(h)

            # Calculate conflicts and fields with changes
            conflict_count = 0
            fields_with_changes = []

            for field_name in VALID_FIELD_NAMES:
                field_history = by_field.get(field_name, [])
                current_value = getattr(update, field_name, None)

                # Track fields with any proposed value
                if current_value is not None or len(field_history) > 0:
                    fields_with_changes.append(field_name)

                # Check for conflict
                if len(field_history) > 1:
                    unique_values = set(h.field_value for h in field_history)
                    if len(unique_values) > 1 and not any(h.is_selected for h in field_history):
                        conflict_count += 1

            # Get customer name
            customer_name = htc_service.get_customer_name(update.customer_id)

            items.append(UnifiedActionListItem(
                type="update",
                id=update.id,
                hawb=update.hawb,
                customer_id=update.customer_id,
                customer_name=customer_name,
                htc_order_number=int(update.htc_order_number) if update.htc_order_number is not None else None,
                status=update.status,
                is_read=update.is_read,
                fields_with_changes=fields_with_changes,
                conflict_count=conflict_count,
                last_processed_at=update.last_processed_at.isoformat() if update.last_processed_at else None,
                created_at=update.created_at.isoformat(),
                updated_at=update.updated_at.isoformat(),
            ))

    # Sort by last_processed_at descending (most recent first), falling back to updated_at
    items.sort(key=lambda x: x.last_processed_at or x.updated_at, reverse=True)

    # Calculate total before pagination
    total = len(items)

    # Apply pagination
    items = items[offset:offset + limit]

    return UnifiedActionListResponse(
        items=items,
        total=total,
        limit=limit,
        offset=offset,
    )


@router.post("/mark-read", response_model=MarkReadResponse)
async def mark_as_read(
    request: MarkReadRequest,
    service = Depends(lambda: ServiceContainer.get_order_management_service())
) -> MarkReadResponse:
    """
    Mark a pending order or update as read/unread.
    """
    logger.debug(f"Mark as read: type={request.type}, id={request.id}, is_read={request.is_read}")

    if request.type == "create":
        repo = service._pending_order_repo
        item = repo.get_by_id(request.id)
        if not item:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Pending order {request.id} not found"
            )
        repo.update(request.id, {"is_read": request.is_read})
    else:
        repo = service._pending_update_repo
        item = repo.get_by_id(request.id)
        if not item:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Pending update {request.id} not found"
            )
        repo.update(request.id, {"is_read": request.is_read})

    return MarkReadResponse(
        success=True,
        type=request.type,
        id=request.id,
        is_read=request.is_read,
    )


# =============================================================================
# Pending Orders Endpoints
# =============================================================================

@router.get("/pending-orders", response_model=GetPendingOrdersResponse)
async def list_pending_orders(
    status: Optional[Literal["incomplete", "ready", "processing", "created", "failed"]] = Query(
        None,
        description="Filter by status"
    ),
    customer_id: Optional[int] = Query(
        None,
        description="Filter by customer ID"
    ),
    search: Optional[str] = Query(
        None,
        description="Search by HAWB"
    ),
    limit: int = Query(50, ge=1, le=200, description="Number of items to return"),
    offset: int = Query(0, ge=0, description="Number of items to skip"),
    sort_by: Literal["created_at", "updated_at", "hawb"] = Query(
        "updated_at",
        description="Field to sort by"
    ),
    sort_order: Literal["asc", "desc"] = Query("desc", description="Sort order"),
    service = Depends(lambda: ServiceContainer.get_order_management_service()),
    htc_service = Depends(lambda: ServiceContainer.get_htc_integration_service())
) -> GetPendingOrdersResponse:
    """
    List pending orders with filtering and pagination.

    Returns orders that are being compiled from pipeline outputs,
    awaiting completion or HTC creation.
    """
    logger.debug(f"List pending orders: status={status}, customer_id={customer_id}, limit={limit}, offset={offset}")

    # Get pending orders from repository
    pending_order_repo = service._pending_order_repo
    pending_order_history_repo = service._pending_order_history_repo

    # Get filtered list
    orders = pending_order_repo.list_all(
        status=status,
        customer_id=customer_id,
        limit=limit,
        offset=offset,
    )

    # Build response items with computed fields
    items = []
    for order in orders:
        # Count fields and conflicts for this order
        required_present = 0
        optional_present = 0
        conflict_count = 0

        for field_name in VALID_FIELD_NAMES:
            value = getattr(order, field_name, None)
            is_required = field_name in REQUIRED_FIELDS

            # Check for conflicts
            unique_values = pending_order_history_repo.get_unique_values_for_field(
                order.id, field_name
            )
            selected = pending_order_history_repo.get_selected_for_field(
                order.id, field_name
            )

            has_conflict = len(unique_values) > 1 and selected is None

            if has_conflict:
                conflict_count += 1
            elif value is not None:
                if is_required:
                    required_present += 1
                else:
                    optional_present += 1

        # Count contributing sub-runs
        history = pending_order_history_repo.get_by_pending_order_id(order.id)
        sub_run_ids = set(h.sub_run_id for h in history if h.sub_run_id is not None)

        # Look up customer name
        customer_name = htc_service.get_customer_name(order.customer_id)

        items.append(PendingOrderListItem(
            id=order.id,
            hawb=order.hawb,
            customer_id=order.customer_id,
            customer_name=customer_name,
            status=order.status,
            htc_order_number=int(order.htc_order_number) if order.htc_order_number is not None else None,
            htc_created_at=order.htc_created_at.isoformat() if order.htc_created_at else None,
            error_message=order.error_message,
            error_at=order.error_at.isoformat() if order.error_at else None,
            required_field_count=len(REQUIRED_FIELDS),
            required_fields_present=required_present,
            optional_field_count=len(VALID_FIELD_NAMES) - len(REQUIRED_FIELDS),
            optional_fields_present=optional_present,
            conflict_count=conflict_count,
            contributing_sub_run_count=len(sub_run_ids),
            created_at=order.created_at.isoformat(),
            updated_at=order.updated_at.isoformat(),
        ))

    # Get total count (without pagination)
    # For now, use len of full query - could optimize later
    all_orders = pending_order_repo.list_all(status=status, customer_id=customer_id)
    total = len(all_orders)

    return GetPendingOrdersResponse(
        items=items,
        total=total,
        limit=limit,
        offset=offset,
    )


@router.get("/pending-orders/{pending_order_id}", response_model=PendingOrderDetail)
async def get_pending_order_detail(
    pending_order_id: int,
    service = Depends(lambda: ServiceContainer.get_order_management_service())
) -> PendingOrderDetail:
    """
    Get detailed view of a pending order including all fields and their states.
    """
    logger.debug(f"Get pending order detail: id={pending_order_id}")

    # Get detail from service
    detail = service.get_pending_order_detail(pending_order_id)

    if not detail:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Pending order {pending_order_id} not found"
        )

    # Map to API response
    return map_pending_order_detail_to_api(detail)


@router.post("/pending-orders/{pending_order_id}/retry", response_model=RetryPendingOrderResponse)
async def retry_pending_order(
    pending_order_id: int,
    htc_service = Depends(lambda: ServiceContainer.get_htc_integration_service())
) -> RetryPendingOrderResponse:
    """
    Retry a failed pending order.

    Resets the status from 'failed' to 'ready' so the HTC order worker
    will attempt to create it again. Only works for orders with status='failed'.
    """
    logger.info(f"Retry pending order: id={pending_order_id}")

    # Use HTC service to retry (it has access to the pending order repo)
    success = htc_service.retry_pending_order(pending_order_id)

    if not success:
        # Check if order exists
        pending_order_repo = htc_service._pending_order_repo
        order = pending_order_repo.get_by_id(pending_order_id) if pending_order_repo else None

        if not order:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Pending order {pending_order_id} not found"
            )
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Cannot retry pending order with status '{order.status}'. Only 'failed' orders can be retried."
            )

    return RetryPendingOrderResponse(
        success=True,
        pending_order_id=pending_order_id,
        new_status="ready",
        message="Pending order reset to 'ready' for retry. The worker will attempt HTC creation shortly."
    )


@router.post("/pending-orders/{pending_order_id}/confirm-field", response_model=ConfirmFieldResponse)
async def confirm_field(
    pending_order_id: int,
    request: ConfirmFieldRequest,
    service = Depends(lambda: ServiceContainer.get_order_management_service())
) -> ConfirmFieldResponse:
    """
    Confirm/select a field value from history to resolve a conflict.

    Sets the selected history entry as the confirmed value for the field.
    This updates:
    - is_selected=TRUE on the chosen history entry
    - is_selected=FALSE on all other history entries for that field
    - The field value on the pending order

    After confirmation, the order status is re-evaluated:
    - If all required fields are set and no conflicts remain -> 'ready'
    - Otherwise -> 'incomplete'

    Guards:
    - Cannot confirm fields on orders with status 'processing', 'created', or 'failed'
    """
    logger.info(f"Confirm field: order={pending_order_id}, field={request.field_name}, history_id={request.history_id}")

    # Get the pending order
    pending_order_repo = service._pending_order_repo
    pending_order = pending_order_repo.get_by_id(pending_order_id)

    if not pending_order:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Pending order {pending_order_id} not found"
        )

    # Guard: Cannot modify orders that are processing, created, or failed
    if pending_order.status in ("processing", "created", "failed"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot modify pending order with status '{pending_order.status}'. "
                   f"Only 'incomplete' or 'ready' orders can be modified."
        )

    # Validate field name
    if request.field_name not in VALID_FIELD_NAMES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid field name: {request.field_name}"
        )

    # Get the history entry
    history_repo = service._pending_order_history_repo
    history_entry = history_repo.get_by_id(request.history_id)

    if not history_entry:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"History entry {request.history_id} not found"
        )

    # Validate history entry belongs to this order and field
    if history_entry.pending_order_id != pending_order_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"History entry {request.history_id} does not belong to pending order {pending_order_id}"
        )

    if history_entry.field_name != request.field_name:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"History entry {request.history_id} is for field '{history_entry.field_name}', not '{request.field_name}'"
        )

    # Clear selection on all history entries for this field
    history_repo.clear_selection_for_field(pending_order_id, request.field_name)

    # Set selection on the chosen entry
    history_repo.update(request.history_id, {"is_selected": True})

    # Update the field value on the pending order
    pending_order_repo.update(pending_order_id, {
        request.field_name: history_entry.field_value,
        "last_processed_at": datetime.now()
    })

    # Re-evaluate status
    service._update_pending_order_status(pending_order_id)

    # Get updated order
    updated_order = pending_order_repo.get_by_id(pending_order_id)

    logger.info(f"Confirmed {request.field_name}='{history_entry.field_value}' for order {pending_order_id}, new status: {updated_order.status}")

    return ConfirmFieldResponse(
        success=True,
        field_name=request.field_name,
        selected_value=history_entry.field_value,
        new_status=updated_order.status,
        message=f"Field '{request.field_name}' confirmed with value '{history_entry.field_value}'"
    )


# =============================================================================
# Pending Updates Endpoints
# =============================================================================

@router.get("/pending-updates", response_model=GetPendingUpdatesResponse)
async def list_pending_updates(
    status: Optional[Literal["pending", "approved", "rejected"]] = Query(
        None,
        description="Filter by status"
    ),
    customer_id: Optional[int] = Query(
        None,
        description="Filter by customer ID"
    ),
    hawb: Optional[str] = Query(
        None,
        description="Filter by HAWB"
    ),
    limit: int = Query(50, ge=1, le=200, description="Number of items to return"),
    offset: int = Query(0, ge=0, description="Number of items to skip"),
    service = Depends(lambda: ServiceContainer.get_order_management_service()),
    htc_service = Depends(lambda: ServiceContainer.get_htc_integration_service())
) -> GetPendingUpdatesResponse:
    """
    List pending updates for existing HTC orders.

    These are proposed changes (one record per HAWB) that need user
    approval before being applied to HTC. Multiple field changes
    accumulate into a single pending_update record.
    """
    logger.debug(f"List pending updates: status={status}, customer_id={customer_id}, hawb={hawb}")

    pending_update_repo = service._pending_update_repo
    pending_update_history_repo = service._pending_update_history_repo

    # Get filtered list with total count
    updates, total = pending_update_repo.list_all(
        status=status,
        customer_id=customer_id,
        hawb=hawb,
        limit=limit,
        offset=offset,
    )

    # Build response items with computed fields
    items = []
    for update in updates:
        # Count fields with changes and conflicts
        fields_with_changes = 0
        conflict_count = 0

        for field_name in VALID_FIELD_NAMES:
            value = getattr(update, field_name, None)

            # Check for conflicts (multiple unique values, none selected)
            unique_values = pending_update_history_repo.get_unique_values_for_field(
                update.id, field_name
            )
            selected = pending_update_history_repo.get_selected_for_field(
                update.id, field_name
            )

            has_conflict = len(unique_values) > 1 and selected is None

            if has_conflict:
                conflict_count += 1
            elif value is not None:
                fields_with_changes += 1

        # Count contributing sub-runs
        history = pending_update_history_repo.get_by_pending_update_id(update.id)
        sub_run_ids = set(h.sub_run_id for h in history if h.sub_run_id is not None)

        # Look up customer name
        customer_name = htc_service.get_customer_name(update.customer_id)

        items.append(PendingUpdateListItem(
            id=update.id,
            hawb=update.hawb,
            customer_id=update.customer_id,
            customer_name=customer_name,
            htc_order_number=int(update.htc_order_number) if update.htc_order_number is not None else None,
            status=update.status,
            fields_with_changes=fields_with_changes,
            conflict_count=conflict_count,
            contributing_sub_run_count=len(sub_run_ids),
            created_at=update.created_at.isoformat(),
            updated_at=update.updated_at.isoformat(),
            reviewed_at=update.reviewed_at.isoformat() if update.reviewed_at else None,
        ))

    return GetPendingUpdatesResponse(
        items=items,
        total=total,
        limit=limit,
        offset=offset,
    )


@router.get("/pending-updates/{pending_update_id}", response_model=PendingUpdateDetail)
async def get_pending_update_detail(
    pending_update_id: int,
    service = Depends(lambda: ServiceContainer.get_order_management_service()),
    htc_service = Depends(lambda: ServiceContainer.get_htc_integration_service())
) -> PendingUpdateDetail:
    """
    Get detailed view of a pending update including all fields and their proposed changes.

    Includes current HTC values alongside proposed changes for comparison.
    """
    logger.debug(f"Get pending update detail: id={pending_update_id}")

    pending_update_repo = service._pending_update_repo
    pending_update_history_repo = service._pending_update_history_repo

    # Get the pending update
    pending_update = pending_update_repo.get_by_id(pending_update_id)
    if not pending_update:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Pending update {pending_update_id} not found"
        )

    # Get current HTC order fields for comparison
    htc_fields = htc_service.get_order_fields(pending_update.htc_order_number)
    htc_values: dict = {}
    if htc_fields:
        # Build a dict of field_name -> current HTC value (as string)
        htc_values = {
            "pickup_company_name": htc_fields.pickup_company_name,
            "pickup_address": htc_fields.pickup_address,
            "pickup_time_start": htc_fields.pickup_time_start,
            "pickup_time_end": htc_fields.pickup_time_end,
            "delivery_company_name": htc_fields.delivery_company_name,
            "delivery_address": htc_fields.delivery_address,
            "delivery_time_start": htc_fields.delivery_time_start,
            "delivery_time_end": htc_fields.delivery_time_end,
            "mawb": htc_fields.mawb,
            "pickup_notes": htc_fields.pickup_notes,
            "delivery_notes": htc_fields.delivery_notes,
            "order_notes": htc_fields.order_notes,
        }

    # Get history records
    history_records = pending_update_history_repo.get_by_pending_update_id(pending_update_id)

    # Build fields with their states
    fields = []
    by_field: dict = {}
    for record in history_records:
        if record.field_name not in by_field:
            by_field[record.field_name] = []
        by_field[record.field_name].append(record)

    for field_name in VALID_FIELD_NAMES:
        history_for_field = by_field.get(field_name, [])
        proposed_value = getattr(pending_update, field_name, None)
        current_htc_value = htc_values.get(field_name)

        # Calculate state
        if len(history_for_field) == 0:
            state = "empty"
            source = None
        elif any(h.is_selected for h in history_for_field):
            state = "confirmed"
            selected = next(h for h in history_for_field if h.is_selected)
            source = FieldSource(
                history_id=selected.id,
                sub_run_id=selected.sub_run_id,
                contributed_at=selected.contributed_at.isoformat()
            )
        elif len(set(h.field_value for h in history_for_field)) > 1 and proposed_value is None:
            state = "conflict"
            source = None
        else:
            state = "set"
            # Use the first history entry as source
            if history_for_field:
                first = history_for_field[0]
                source = FieldSource(
                    history_id=first.id,
                    sub_run_id=first.sub_run_id,
                    contributed_at=first.contributed_at.isoformat()
                )
            else:
                source = None

        # Always build conflict_options when there are multiple history entries
        # This allows users to change their selection even after confirming
        conflict_options = None
        if len(history_for_field) > 1:
            conflict_options = [
                ConflictOption(
                    history_id=h.id,
                    value=h.field_value,
                    sub_run_id=h.sub_run_id,
                    contributed_at=h.contributed_at.isoformat()
                )
                for h in history_for_field
            ]

        fields.append(PendingUpdateFieldDetail(
            name=field_name,
            label=get_field_label(field_name),
            current_value=current_htc_value,
            proposed_value=str(proposed_value) if proposed_value is not None else None,
            state=state,
            conflict_options=conflict_options,
            source=source,
        ))

    # Build contributing sub-runs list
    sub_run_ids = set(h.sub_run_id for h in history_records if h.sub_run_id is not None)
    contributing_sub_runs = []

    # For mock data (sub_run_id is None)
    mock_records = [h for h in history_records if h.sub_run_id is None]
    if mock_records:
        contributing_sub_runs.append(ContributingSubRun(
            sub_run_id=None,
            run_id=None,
            source_type="mock",
            source_identifier="Mock Test Data",
            pdf_filename="(No PDF)",
            template_name=None,
            fields_contributed=[h.field_name for h in mock_records],
            contributed_at=mock_records[0].contributed_at.isoformat(),
        ))

    # For real sub-runs, we'd need to look up details (simplified for now)
    for sub_run_id in sub_run_ids:
        records = [h for h in history_records if h.sub_run_id == sub_run_id]
        contributing_sub_runs.append(ContributingSubRun(
            sub_run_id=sub_run_id,
            run_id=None,  # Would need lookup
            source_type="pipeline",
            source_identifier=f"Sub-run {sub_run_id}",
            pdf_filename="Unknown",  # Would need lookup
            template_name=None,
            fields_contributed=[h.field_name for h in records],
            contributed_at=records[0].contributed_at.isoformat(),
        ))

    # Get customer name
    customer_name = htc_service.get_customer_name(pending_update.customer_id)

    return PendingUpdateDetail(
        id=pending_update.id,
        hawb=pending_update.hawb,
        customer_id=pending_update.customer_id,
        customer_name=customer_name,
        htc_order_number=int(pending_update.htc_order_number) if pending_update.htc_order_number is not None else None,
        status=pending_update.status,
        fields=fields,
        contributing_sub_runs=contributing_sub_runs,
        created_at=pending_update.created_at.isoformat(),
        updated_at=pending_update.updated_at.isoformat(),
        reviewed_at=pending_update.reviewed_at.isoformat() if pending_update.reviewed_at else None,
    )


@router.post("/pending-updates/{pending_update_id}/approve", response_model=ApprovePendingUpdateResponse)
async def approve_pending_update(
    pending_update_id: int,
    request: ApprovePendingUpdateRequest,
    service = Depends(lambda: ServiceContainer.get_order_management_service()),
    htc_service = Depends(lambda: ServiceContainer.get_htc_integration_service())
) -> ApprovePendingUpdateResponse:
    """
    Approve a pending update and apply it to the HTC order.

    This will:
    1. Validate the pending update is in 'pending' status
    2. Get current HTC values for audit trail comparison
    3. Call the HTC update_order method to apply all field changes
    4. Create an audit history record with old->new values
    5. Mark the pending update as 'approved'
    """
    logger.info(f"Approve pending update: id={pending_update_id}, approver={request.approver_username}")

    pending_update_repo = service._pending_update_repo

    # Get the pending update
    pending_update = pending_update_repo.get_by_id(pending_update_id)
    if not pending_update:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Pending update {pending_update_id} not found"
        )

    # Guard: Only approve pending updates
    if pending_update.status != "pending":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot approve pending update with status '{pending_update.status}'. Only 'pending' updates can be approved."
        )

    # Guard: Must have htc_order_number to update
    if pending_update.htc_order_number is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot approve: no HTC order number associated with this update. This may be a manual_review item."
        )

    htc_order_number = pending_update.htc_order_number

    # Get current HTC values BEFORE the update (for audit trail)
    htc_fields = htc_service.get_order_fields(htc_order_number)
    old_values: dict = {}
    if htc_fields:
        old_values = {
            "pickup_company_name": htc_fields.pickup_company_name,
            "pickup_address": htc_fields.pickup_address,
            "pickup_time_start": htc_fields.pickup_time_start,
            "pickup_time_end": htc_fields.pickup_time_end,
            "delivery_company_name": htc_fields.delivery_company_name,
            "delivery_address": htc_fields.delivery_address,
            "delivery_time_start": htc_fields.delivery_time_start,
            "delivery_time_end": htc_fields.delivery_time_end,
            "mawb": htc_fields.mawb,
            "pickup_notes": htc_fields.pickup_notes,
            "delivery_notes": htc_fields.delivery_notes,
            "order_notes": htc_fields.order_notes,
        }

    # Collect fields that have proposed changes (non-NULL values)
    fields_to_update = []
    new_values: dict = {}
    for field_name in VALID_FIELD_NAMES:
        value = getattr(pending_update, field_name, None)
        if value is not None:
            fields_to_update.append(field_name)
            new_values[field_name] = str(value) if value is not None else None

    # Log what we're about to update
    htc_order_str = str(int(htc_order_number))
    logger.info(f"Applying {len(fields_to_update)} field updates to HTC order {htc_order_str}")

    try:
        # Call the HTC update_order method with all the field values and approver info
        updated_fields = htc_service.update_order(
            order_number=htc_order_number,
            pickup_company_name=pending_update.pickup_company_name,
            pickup_address=pending_update.pickup_address,
            pickup_time_start=pending_update.pickup_time_start,
            pickup_time_end=pending_update.pickup_time_end,
            delivery_company_name=pending_update.delivery_company_name,
            delivery_address=pending_update.delivery_address,
            delivery_time_start=pending_update.delivery_time_start,
            delivery_time_end=pending_update.delivery_time_end,
            mawb=pending_update.mawb,
            pickup_notes=pending_update.pickup_notes,
            delivery_notes=pending_update.delivery_notes,
            order_notes=pending_update.order_notes,
            approver_username=request.approver_username,
            old_values=old_values,
            new_values=new_values,
        )

        # Update status to approved
        pending_update_repo.update(pending_update_id, {
            "status": "approved",
            "reviewed_at": datetime.utcnow(),
            "last_processed_at": datetime.now(),
        })

        logger.info(f"Approved pending update {pending_update_id}: {len(updated_fields)} fields updated in HTC")

        # Broadcast SSE event
        order_event_manager.broadcast_sync("pending_update_resolved", {
            "id": pending_update_id,
            "status": "approved",
            "htc_order_number": int(htc_order_number),
            "fields_updated": updated_fields,
        })

        return ApprovePendingUpdateResponse(
            success=True,
            update_id=pending_update_id,
            htc_order_number=int(htc_order_number),
            new_status="approved",
            fields_updated=updated_fields,
            message=f"Successfully updated HTC order {htc_order_str} with {len(updated_fields)} fields."
        )

    except Exception as e:
        logger.error(f"Failed to apply update to HTC order {htc_order_str}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update HTC order: {str(e)}"
        )


@router.post("/pending-updates/{pending_update_id}/reject", response_model=RejectPendingUpdateResponse)
async def reject_pending_update(
    pending_update_id: int,
    service = Depends(lambda: ServiceContainer.get_order_management_service())
) -> RejectPendingUpdateResponse:
    """
    Reject a pending update.

    Marks the pending update as rejected without applying any changes.
    """
    logger.info(f"Reject pending update: id={pending_update_id}")

    pending_update_repo = service._pending_update_repo

    # Get the pending update
    pending_update = pending_update_repo.get_by_id(pending_update_id)
    if not pending_update:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Pending update {pending_update_id} not found"
        )

    # Guard: Only reject pending updates
    if pending_update.status != "pending":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot reject pending update with status '{pending_update.status}'. Only 'pending' updates can be rejected."
        )

    # Update status to rejected
    pending_update_repo.update(pending_update_id, {
        "status": "rejected",
        "reviewed_at": datetime.utcnow(),
        "last_processed_at": datetime.now(),
    })

    logger.info(f"Rejected pending update {pending_update_id}")

    # Broadcast SSE event
    order_event_manager.broadcast_sync("pending_update_resolved", {
        "id": pending_update_id,
        "status": "rejected",
        "htc_order_number": int(pending_update.htc_order_number) if pending_update.htc_order_number else None,
    })

    htc_order_str = str(int(pending_update.htc_order_number)) if pending_update.htc_order_number is not None else "N/A"
    return RejectPendingUpdateResponse(
        success=True,
        update_id=pending_update_id,
        new_status="rejected",
        message=f"Rejected update for HTC order {htc_order_str}."
    )


@router.post("/pending-updates/{pending_update_id}/confirm-field", response_model=ConfirmUpdateFieldResponse)
async def confirm_update_field(
    pending_update_id: int,
    request: ConfirmUpdateFieldRequest,
    service = Depends(lambda: ServiceContainer.get_order_management_service())
) -> ConfirmUpdateFieldResponse:
    """
    Confirm/select a field value from history to resolve a conflict in a pending update.
    """
    logger.info(f"Confirm field for pending update: id={pending_update_id}, field={request.field_name}, history_id={request.history_id}")

    pending_update_repo = service._pending_update_repo
    pending_update_history_repo = service._pending_update_history_repo

    # Get the pending update
    pending_update = pending_update_repo.get_by_id(pending_update_id)
    if not pending_update:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Pending update {pending_update_id} not found"
        )

    # Guard: Cannot modify non-pending updates
    if pending_update.status != "pending":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot modify pending update with status '{pending_update.status}'. Only 'pending' updates can be modified."
        )

    # Validate field name
    if request.field_name not in VALID_FIELD_NAMES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid field name: {request.field_name}"
        )

    # Get the history entry
    history_entry = pending_update_history_repo.get_by_id(request.history_id)
    if not history_entry:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"History entry {request.history_id} not found"
        )

    # Validate history entry belongs to this update and field
    if history_entry.pending_update_id != pending_update_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"History entry {request.history_id} does not belong to pending update {pending_update_id}"
        )

    if history_entry.field_name != request.field_name:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"History entry {request.history_id} is for field '{history_entry.field_name}', not '{request.field_name}'"
        )

    # Clear selection on all history entries for this field
    pending_update_history_repo.clear_selection_for_field(pending_update_id, request.field_name)

    # Set selection on the chosen entry
    pending_update_history_repo.update(request.history_id, {"is_selected": True})

    # Update the field value on the pending update
    pending_update_repo.update(pending_update_id, {
        request.field_name: history_entry.field_value,
        "last_processed_at": datetime.now()
    })

    logger.info(f"Confirmed {request.field_name}='{history_entry.field_value}' for pending update {pending_update_id}")

    return ConfirmUpdateFieldResponse(
        success=True,
        field_name=request.field_name,
        selected_value=history_entry.field_value,
        message=f"Field '{request.field_name}' confirmed with value '{history_entry.field_value}'"
    )


# =============================================================================
# Mock Testing Endpoints
# =============================================================================

@router.post("/mock/process-output", response_model=MockOutputProcessingResponse)
async def mock_process_output(
    request: MockOutputProcessingRequest,
    output_service = Depends(lambda: ServiceContainer.get_output_processing_service()),
    htc_service = Depends(lambda: ServiceContainer.get_htc_integration_service())
) -> MockOutputProcessingResponse:
    """
    Mock pipeline output processing for testing.

    Simulates the effect of a full ETO pipeline run completing and
    contributing output channel data to the pending orders system.

    This bypasses:
    - PDF upload and storage
    - Template matching
    - OCR extraction
    - Pipeline execution
    - Output execution record creation

    And directly calls the pending order processing logic with
    the provided output channel data.

    Use this endpoint to test:
    - Pending order creation
    - Conflict detection and resolution
    - Status transitions (incomplete -> ready)
    - HTC order lookup (existing orders create pending_updates instead)

    Note: History records created by this endpoint will have sub_run_id=NULL
    to indicate they are mock/test data.
    """
    logger.info(f"Mock output processing: customer_id={request.customer_id}, hawb='{request.hawb}'")

    try:
        # Check for duplicate orders in HTC (requires manual review)
        htc_order_count = htc_service.count_orders_by_customer_and_hawb(
            customer_id=request.customer_id,
            hawb=request.hawb
        )

        # Check if HAWB already exists in HTC
        htc_order_number = htc_service.lookup_order_by_customer_and_hawb(
            customer_id=request.customer_id,
            hawb=request.hawb
        )

        if htc_order_number is not None:
            # Order exists in HTC - use existing order handler
            # Get state before processing
            pending_update_repo = output_service._pending_update_repo
            existing_update = pending_update_repo.get_active_by_customer_and_hawb(
                request.customer_id, request.hawb
            )
            existing_field_values = {}
            if existing_update:
                for field_name in VALID_FIELD_NAMES:
                    existing_field_values[field_name] = getattr(existing_update, field_name, None)

            # This creates or updates pending_update for user approval
            # Pass htc_order_count so it can flag for manual_review if duplicates exist
            action = output_service._handle_existing_order(
                customer_id=request.customer_id,
                hawb=request.hawb,
                htc_order_number=htc_order_number,
                sub_run_id=None,  # NULL for mock data
                output_channel_data=request.output_channel_data,
                htc_order_count=htc_order_count,
            )

            # Get the pending update to return details
            pending_update = pending_update_repo.get_active_by_customer_and_hawb(
                request.customer_id, request.hawb
            )

            # Determine which fields were contributed and which have conflicts
            fields_contributed = []
            conflicts_introduced = []

            valid_fields = output_service._extract_valid_fields(request.output_channel_data)
            for field_name in valid_fields.keys():
                fields_contributed.append(field_name)

                # Check if this field is now NULL (conflict)
                if pending_update:
                    current_value = getattr(pending_update, field_name, None)
                    old_value = existing_field_values.get(field_name)

                    # Conflict if: had a value before, now NULL
                    if old_value is not None and current_value is None:
                        conflicts_introduced.append(field_name)

            return MockOutputProcessingResponse(
                success=True,
                action=action,
                pending_update_id=pending_update.id if pending_update else None,
                htc_order_number=int(htc_order_number),
                fields_contributed=fields_contributed,
                conflicts_introduced=conflicts_introduced,
                message=f"HAWB '{request.hawb}' exists in HTC as order {int(htc_order_number)}. Processed {len(fields_contributed)} fields.",
            )

        # Order doesn't exist in HTC - get pending order state before processing
        pending_order_repo = output_service._pending_order_repo
        existing_order = pending_order_repo.get_by_customer_and_hawb(
            request.customer_id, request.hawb
        )
        existing_field_values = {}
        if existing_order:
            for field_name in VALID_FIELD_NAMES:
                existing_field_values[field_name] = getattr(existing_order, field_name, None)

        # Process as new order
        action = output_service._handle_new_order(
            customer_id=request.customer_id,
            hawb=request.hawb,
            sub_run_id=None,  # NULL for mock data
            output_channel_data=request.output_channel_data,
        )

        # Get the pending order to return details
        pending_order = pending_order_repo.get_by_customer_and_hawb(
            request.customer_id, request.hawb
        )

        # Determine which fields were contributed and which have conflicts
        fields_contributed = []
        conflicts_introduced = []

        valid_fields = output_service._extract_valid_fields(request.output_channel_data)
        for field_name in valid_fields.keys():
            fields_contributed.append(field_name)

            # Check if this field is now NULL (conflict)
            if pending_order:
                current_value = getattr(pending_order, field_name, None)
                old_value = existing_field_values.get(field_name)

                # Conflict if: had a value before, now NULL
                if old_value is not None and current_value is None:
                    conflicts_introduced.append(field_name)

        return MockOutputProcessingResponse(
            success=True,
            action=action,
            pending_order_id=pending_order.id if pending_order else None,
            pending_order_status=pending_order.status if pending_order else None,
            fields_contributed=fields_contributed,
            conflicts_introduced=conflicts_introduced,
            message=f"Processed {len(fields_contributed)} fields for HAWB '{request.hawb}'",
        )

    except Exception as e:
        logger.error(f"Mock output processing failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


# =============================================================================
# Server-Sent Events (SSE) Endpoint
# =============================================================================

@router.get("/events")
async def order_events_stream(request: Request):
    """
    Server-Sent Events (SSE) endpoint for real-time order management updates.

    Streams events to connected clients whenever pending orders or updates change.
    Multiple clients can connect simultaneously - each gets their own event stream.

    Event Types:
    - pending_order_created: New pending order created
    - pending_order_updated: Pending order status, fields, or conflicts changed
    - pending_order_deleted: Pending order deleted
    - pending_update_created: New pending update created (for existing HTC order)
    - pending_update_updated: Pending update fields or status changed
    - pending_update_resolved: Pending update approved or rejected

    Event Format:
    data: {
        "type": "pending_order_created" | "pending_order_updated" | ...,
        "data": { ... event data ... },
        "timestamp": "2025-10-29T10:00:00Z"
    }

    Connection automatically reconnects if dropped.
    """
    # Create a unique queue for this client connection
    client_queue = asyncio.Queue(maxsize=100)  # Buffer up to 100 events

    async def event_generator():
        # Register this client with the global event manager
        order_event_manager.register_client(client_queue)
        logger.debug(f"Order SSE client connected - total: {order_event_manager.get_client_count()}")

        try:
            # Send initial connection event to establish the stream
            yield ": connected\n\n"  # SSE comment - keeps connection alive

            while not order_event_manager.is_shutting_down():
                try:
                    # Check if client disconnected
                    try:
                        if await asyncio.wait_for(request.is_disconnected(), timeout=0.1):
                            logger.debug("Order SSE client disconnected")
                            break
                    except asyncio.TimeoutError:
                        pass  # Client still connected

                    # Wait for next event with timeout
                    event = await asyncio.wait_for(
                        client_queue.get(),
                        timeout=1.0  # Short timeout to check shutdown flag frequently
                    )

                    # Format as SSE: "data: {...}\n\n"
                    yield f"data: {json.dumps(event)}\n\n"

                    # If this was a shutdown event, exit gracefully
                    if event.get("type") == "server_shutdown":
                        logger.debug("Order SSE shutdown event received")
                        break

                except asyncio.TimeoutError:
                    # No event - continue to next iteration
                    continue
                except asyncio.CancelledError:
                    # If cancelled during any await, exit immediately
                    return

        except asyncio.CancelledError:
            return  # Exit generator immediately
        except Exception as e:
            logger.error(f"Order SSE error: {e}", exc_info=True)
        finally:
            # Always cleanup when connection closes
            order_event_manager.unregister_client(client_queue)
            logger.debug(f"Order SSE client disconnected - remaining: {order_event_manager.get_client_count()}")

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",  # Disable nginx buffering if behind nginx
        }
    )
