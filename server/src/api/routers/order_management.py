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
    ResolveConflictRequest,
    ResolveConflictResponse,
    CreateOrderResponse,
    # Pending Updates
    GetPendingUpdatesResponse,
    PendingUpdateListItem,
    ApprovePendingUpdateResponse,
    RejectPendingUpdateResponse,
    BulkUpdateActionRequest,
    BulkUpdateActionResponse,
    # Helpers
    get_field_label,
    FIELD_LABELS,
)
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
    status: Optional[Literal["incomplete", "ready", "created"]] = Query(
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
    service = Depends(lambda: ServiceContainer.get_pending_orders_service())
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

        items.append(PendingOrderListItem(
            id=order.id,
            hawb=order.hawb,
            customer_id=order.customer_id,
            customer_name=None,  # TODO: Resolve from Access DB
            status=order.status,
            htc_order_number=order.htc_order_number,
            htc_created_at=order.htc_created_at.isoformat() if order.htc_created_at else None,
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
    service = Depends(lambda: ServiceContainer.get_pending_orders_service())
) -> PendingOrderDetail:
    """
    Get detailed view of a pending order including all fields and their states.
    """
    logger.debug(f"Get pending order detail: id={pending_order_id}")

    pending_order_repo = service._pending_order_repo
    pending_order_history_repo = service._pending_order_history_repo

    # Get the order
    order = pending_order_repo.get_by_id(pending_order_id)
    if not order:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Pending order {pending_order_id} not found"
        )

    # Build field details
    from api.schemas.order_management import FieldDetail, FieldSource, ConflictOption

    fields = []
    for field_name in VALID_FIELD_NAMES:
        value = getattr(order, field_name, None)
        is_required = field_name in REQUIRED_FIELDS

        # Get history for this field
        history_entries = pending_order_history_repo.get_by_field(order.id, field_name)
        unique_values = pending_order_history_repo.get_unique_values_for_field(order.id, field_name)
        selected = pending_order_history_repo.get_selected_for_field(order.id, field_name)

        # Determine state
        if len(history_entries) == 0:
            state = "empty"
            conflict_options = None
            source = None
        elif selected is not None:
            state = "confirmed"
            conflict_options = None
            source = FieldSource(
                history_id=selected.id,
                sub_run_id=selected.sub_run_id,
                contributed_at=selected.contributed_at.isoformat(),
            )
        elif len(unique_values) > 1:
            state = "conflict"
            conflict_options = [
                ConflictOption(
                    history_id=h.id,
                    value=h.field_value,
                    sub_run_id=h.sub_run_id,
                    contributed_at=h.contributed_at.isoformat(),
                )
                for h in history_entries
            ]
            source = None
        else:
            state = "set"
            conflict_options = None
            # Use first history entry as source
            if history_entries:
                h = history_entries[0]
                source = FieldSource(
                    history_id=h.id,
                    sub_run_id=h.sub_run_id,
                    contributed_at=h.contributed_at.isoformat(),
                )
            else:
                source = None

        fields.append(FieldDetail(
            name=field_name,
            label=get_field_label(field_name),
            required=is_required,
            value=value,
            state=state,
            conflict_options=conflict_options,
            source=source,
        ))

    # Build contributing sub-runs
    from api.schemas.order_management import ContributingSubRun

    all_history = pending_order_history_repo.get_by_pending_order_id(order.id)

    # Group by sub_run_id
    sub_run_contributions: dict = {}
    for h in all_history:
        if h.sub_run_id is None:
            continue
        if h.sub_run_id not in sub_run_contributions:
            sub_run_contributions[h.sub_run_id] = {
                "sub_run_id": h.sub_run_id,
                "fields": [],
                "contributed_at": h.contributed_at,
            }
        sub_run_contributions[h.sub_run_id]["fields"].append(h.field_name)
        # Use earliest contributed_at
        if h.contributed_at < sub_run_contributions[h.sub_run_id]["contributed_at"]:
            sub_run_contributions[h.sub_run_id]["contributed_at"] = h.contributed_at

    contributing_sub_runs = [
        ContributingSubRun(
            sub_run_id=data["sub_run_id"],
            run_id=0,  # TODO: Get from sub_run relation
            pdf_filename="",  # TODO: Get from sub_run relation
            template_name=None,  # TODO: Get from sub_run relation
            fields_contributed=data["fields"],
            contributed_at=data["contributed_at"].isoformat(),
        )
        for data in sub_run_contributions.values()
    ]

    return PendingOrderDetail(
        id=order.id,
        hawb=order.hawb,
        customer_id=order.customer_id,
        customer_name=None,  # TODO: Resolve from Access DB
        status=order.status,
        htc_order_number=order.htc_order_number,
        htc_created_at=order.htc_created_at.isoformat() if order.htc_created_at else None,
        fields=fields,
        contributing_sub_runs=contributing_sub_runs,
        created_at=order.created_at.isoformat(),
        updated_at=order.updated_at.isoformat(),
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
    service = Depends(lambda: ServiceContainer.get_pending_orders_service())
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

    # Build response items
    items = [
        PendingUpdateListItem(
            id=update.id,
            customer_id=update.customer_id,
            hawb=update.hawb,
            htc_order_number=update.htc_order_number,
            customer_name=None,  # TODO: Resolve from Access DB
            field_name=update.field_name,
            field_label=get_field_label(update.field_name),
            proposed_value=update.proposed_value,
            sub_run_id=update.sub_run_id,
            status=update.status,
            proposed_at=update.proposed_at.isoformat(),
            reviewed_at=update.reviewed_at.isoformat() if update.reviewed_at else None,
        )
        for update in updates
    ]

    # Get total count
    all_updates = pending_update_repo.list_all(status=status, customer_id=customer_id, hawb=hawb)
    total = len(all_updates)

    return GetPendingUpdatesResponse(
        items=items,
        total=total,
        limit=limit,
        offset=offset,
    )
