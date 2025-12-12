"""
Order Management FastAPI Router
REST endpoints for pending orders and pending updates
"""
import logging
from typing import Optional, Literal
from fastapi import APIRouter, Query, Depends, HTTPException, status

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
    ApprovePendingUpdateResponse,
    RejectPendingUpdateResponse,
    BulkUpdateActionRequest,
    BulkUpdateActionResponse,
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
    pending_order_repo.update(pending_order_id, {request.field_name: history_entry.field_value})

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

    These are proposed changes that need user approval before
    being applied to HTC.
    """
    logger.debug(f"List pending updates: status={status}, customer_id={customer_id}, hawb={hawb}")

    pending_update_repo = service._pending_update_repo

    # Get filtered list
    updates = pending_update_repo.list_all(
        status=status,
        customer_id=customer_id,
        hawb=hawb,
        limit=limit,
        offset=offset,
    )

    # Build response items with customer name lookup
    items = []
    for update in updates:
        customer_name = htc_service.get_customer_name(update.customer_id)
        items.append(PendingUpdateListItem(
            id=update.id,
            customer_id=update.customer_id,
            hawb=update.hawb,
            htc_order_number=update.htc_order_number,
            customer_name=customer_name,
            field_name=update.field_name,
            field_label=get_field_label(update.field_name),
            proposed_value=update.proposed_value,
            sub_run_id=update.sub_run_id,
            status=update.status,
            proposed_at=update.proposed_at.isoformat(),
            reviewed_at=update.reviewed_at.isoformat() if update.reviewed_at else None,
        ))

    # Get total count
    all_updates = pending_update_repo.list_all(status=status, customer_id=customer_id, hawb=hawb)
    total = len(all_updates)

    return GetPendingUpdatesResponse(
        items=items,
        total=total,
        limit=limit,
        offset=offset,
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
        # Check if HAWB already exists in HTC
        htc_order_number = htc_service.lookup_order_by_customer_and_hawb(
            customer_id=request.customer_id,
            hawb=request.hawb
        )

        if htc_order_number is not None:
            # Order exists in HTC - use existing order handler
            # This creates pending_updates for user approval
            action = output_service._handle_existing_order(
                customer_id=request.customer_id,
                hawb=request.hawb,
                htc_order_number=htc_order_number,
                sub_run_id=None,  # NULL for mock data
                output_channel_data=request.output_channel_data,
            )
            return MockOutputProcessingResponse(
                success=True,
                action=action,
                message=f"HAWB '{request.hawb}' exists in HTC as order {htc_order_number}. Created pending updates.",
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
