"""
Pending Actions FastAPI Router

REST endpoints for pending action management (unified order creates and updates).
"""
import asyncio
import json
import logging
from typing import Literal

from fastapi import APIRouter, Query, Depends, HTTPException, Request
from fastapi.responses import StreamingResponse

from api.schemas.pending_actions import (
    GetPendingActionsResponse,
    PendingActionListItem,
    GetPendingActionDetailResponse,
    PendingActionFieldItem,
    ContributingSourceItem,
    FieldMetadataItem,
    ExecutionResultSchema,
    SetReadStatusRequest,
    SetReadStatusResponse,
    CreateMockOutputRequest,
    CreateMockOutputResponse,
    ApproveActionRequest,
    ApproveActionResponse,
    RejectActionRequest,
    RejectActionResponse,
    SelectFieldValueRequest,
    SelectFieldValueResponse,
    SetFieldApprovalRequest,
    SetFieldApprovalResponse,
)
from shared.types.pending_actions import PendingActionStatus, PendingActionType, ORDER_FIELDS
from shared.services.service_container import ServiceContainer
from src.shared.events.order_events import order_event_manager
from features.order_management.service import OrderManagementService

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/pending-actions",
    tags=["Pending Actions"]
)


@router.get("/events")
async def pending_action_events_stream(request: Request):
    """
    Server-Sent Events (SSE) endpoint for real-time pending action updates.

    Streams events to connected clients whenever pending actions are created,
    updated, or deleted. Multiple clients can connect simultaneously.

    Event Types:
    - pending_action_created: New pending action created
    - pending_action_updated: Pending action status, fields, or conflicts changed
    - pending_action_deleted: Pending action deleted

    Event Format:
    data: {
        "type": "pending_action_created" | "pending_action_updated" | "pending_action_deleted",
        "data": { "id": 123, "status": "ready", "action_type": "create", ... },
        "timestamp": "2025-01-13T10:00:00Z"
    }

    Connection automatically reconnects if dropped.
    """
    client_queue: asyncio.Queue = asyncio.Queue(maxsize=100)

    async def event_generator():
        """SSE event generator with clean shutdown handling."""
        order_event_manager.register_client(client_queue)
        logger.debug(f"Order SSE client connected - total: {order_event_manager.get_client_count()}")

        try:
            # Send initial connection comment to establish the stream
            yield ": connected\n\n"

            while True:
                try:
                    event = await client_queue.get()
                    yield f"data: {json.dumps(event)}\n\n"
                except asyncio.CancelledError:
                    return
        except asyncio.CancelledError:
            return
        except Exception as e:
            logger.error(f"Order SSE error: {e}", exc_info=True)
        finally:
            order_event_manager.unregister_client(client_queue)
            logger.debug(f"Order SSE client disconnected - remaining: {order_event_manager.get_client_count()}")

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        }
    )


@router.get("", response_model=GetPendingActionsResponse)
async def list_pending_actions(
    status: Literal["incomplete", "conflict", "ambiguous", "ready", "processing", "completed", "failed", "rejected"] | None = Query(
        None,
        description="Filter by status"
    ),
    action_type: Literal["create", "update", "ambiguous"] | None = Query(
        None,
        description="Filter by action type"
    ),
    is_read: bool | None = Query(
        None,
        description="Filter by read status (true=read, false=unread)"
    ),
    customer_id: int | None = Query(
        None,
        description="Filter by customer ID"
    ),
    search: str | None = Query(
        None,
        description="Search in HAWB"
    ),
    limit: int = Query(50, ge=1, le=200, description="Number of items to return"),
    offset: int = Query(0, ge=0, description="Number of items to skip"),
    sort_by: Literal["updated_at", "created_at", "last_processed_at", "hawb", "status"] = Query(
        "last_processed_at",
        description="Field to sort by"
    ),
    sort_order: Literal["asc", "desc"] = Query("desc", description="Sort order"),
    service: OrderManagementService = Depends(lambda: ServiceContainer.get_order_management_service())
) -> GetPendingActionsResponse:
    """
    List pending actions with filtering, search, and pagination.

    Pending actions represent order operations (creates or updates) that are
    being accumulated from pipeline outputs before execution against HTC.

    Filters:
    - status: Filter by action status
    - action_type: Filter by type (create for new orders, update for existing)
    - is_read: Filter by read/unread status
    - customer_id: Filter by customer
    - search: Text search in HAWB

    Sorting:
    - updated_at: Most recently updated (default)
    - created_at: When the action was created
    - last_processed_at: When actual processing occurred
    - hawb: Sort by HAWB alphabetically
    - status: Sort by status
    """
    logger.debug(
        f"List pending actions: status={status}, action_type={action_type}, "
        f"is_read={is_read}, customer_id={customer_id}, search={search}, limit={limit}, offset={offset}"
    )

    # Get items from service
    items, total = service.list_pending_actions(
        status=status,
        action_type=action_type,
        is_read=is_read,
        customer_id=customer_id,
        search_query=search,
        limit=limit,
        offset=offset,
        order_by=sort_by,
        desc=(sort_order == "desc"),
    )

    # Convert domain types to API schema
    api_items = [
        PendingActionListItem(
            id=item.id,
            customer_id=item.customer_id,
            customer_name=item.customer_name,
            hawb=item.hawb,
            htc_order_number=item.htc_order_number,
            action_type=item.action_type,
            status=item.status,
            required_fields_present=item.required_fields_present,
            required_fields_total=item.required_fields_total,
            optional_fields_present=item.optional_fields_present,
            optional_fields_total=item.optional_fields_total,
            field_names=item.field_names,
            conflict_count=item.conflict_count,
            error_message=item.error_message,
            is_read=item.is_read,
            created_at=item.created_at,
            updated_at=item.updated_at,
            last_processed_at=item.last_processed_at,
        )
        for item in items
    ]

    return GetPendingActionsResponse(
        items=api_items,
        total=total,
        limit=limit,
        offset=offset,
    )


@router.post("/mock", response_model=CreateMockOutputResponse)
async def create_mock_output(
    request: CreateMockOutputRequest,
    service: OrderManagementService = Depends(lambda: ServiceContainer.get_order_management_service())
) -> CreateMockOutputResponse:
    """
    Create a mock output execution for testing.

    Creates minimal stub records (pdf_file, eto_run, sub_run, output_execution)
    with source_type='mock', then processes through the normal accumulation flow.

    This allows testing the pending action system in isolation from ETO.

    Example output_channel_data:
    ```json
    {
        "pickup_time_start": "2024-01-15 09:00",
        "pickup_time_end": "2024-01-15 12:00",
        "pickup_company_name": "Acme Corp",
        "pickup_address": "123 Main St, New York, NY 10001",
        "delivery_company_name": "XYZ Inc",
        "delivery_address": "456 Oak Ave, Los Angeles, CA 90001"
    }
    ```
    """
    logger.debug(
        f"Create mock output: customer_id={request.customer_id}, "
        f"hawb={request.hawb}, channels={list(request.output_channel_data.keys())}"
    )

    pending_action = service.create_mock_output_execution(
        customer_id=request.customer_id,
        hawb=request.hawb,
        output_channel_data=request.output_channel_data,
        pdf_filename=request.pdf_filename or "mock_document.pdf",
    )

    if pending_action is None:
        # Update had no changes compared to HTC - return informative response
        return CreateMockOutputResponse(
            pending_action_id=0,  # No action created
            action_type="update",
            status="completed",  # Effectively completed - nothing to do
            message="No changes detected compared to current HTC values. No pending action created.",
        )

    return CreateMockOutputResponse(
        pending_action_id=pending_action.id,
        action_type=pending_action.action_type,
        status=pending_action.status,
        message=f"Mock output processed. Pending action {pending_action.id} is now '{pending_action.status}'.",
    )


@router.get("/{action_id}", response_model=GetPendingActionDetailResponse)
async def get_pending_action_detail(
    action_id: int,
    service: OrderManagementService = Depends(lambda: ServiceContainer.get_order_management_service())
) -> GetPendingActionDetailResponse:
    """
    Get detailed view of a pending action.

    Returns complete action data including:
    - Core action information (customer, HAWB, status, etc.)
    - All field values grouped by field name (with conflict options)
    - Contributing sources (sub-runs that contributed data)
    - For updates: current HTC values for comparison

    The response is structured to support frontend cross-highlighting:
    - Each field value includes sub_run_id for linking to source cards
    - Each source includes fields_contributed for linking to field rows
    """
    logger.debug(f"Get pending action detail: action_id={action_id}")

    detail = service.get_pending_action_detail(action_id)

    if detail is None:
        raise HTTPException(status_code=404, detail=f"Pending action {action_id} not found")

    # Convert domain types to API schema
    api_fields: dict[str, list[PendingActionFieldItem]] = {}
    for field_name, field_values in detail.fields.items():
        api_fields[field_name] = [
            PendingActionFieldItem(
                id=fv.id,
                field_name=fv.field_name,
                value=fv.value,
                is_selected=fv.is_selected,
                is_approved_for_update=fv.is_approved_for_update,
                sub_run_id=fv.sub_run_id,
            )
            for fv in field_values
        ]

    api_sources = [
        ContributingSourceItem(
            sub_run_id=src.sub_run_id,
            pdf_filename=src.pdf_filename,
            template_name=src.template_name,
            source_type=src.source_type,
            source_identifier=src.source_identifier,
            fields_contributed=src.fields_contributed,
            contributed_at=src.contributed_at,
        )
        for src in detail.contributing_sources
    ]

    # Build field metadata from ORDER_FIELDS definitions
    api_field_metadata: dict[str, FieldMetadataItem] = {
        field_def.name: FieldMetadataItem(
            name=field_def.name,
            label=field_def.label,
            data_type=field_def.data_type,
            required=field_def.required,
            display_order=field_def.display_order,
        )
        for field_def in ORDER_FIELDS.values()
    }

    # Convert execution_result if present
    api_execution_result = None
    if detail.execution_result:
        api_execution_result = ExecutionResultSchema(
            action_type=detail.execution_result.action_type,
            executed_at=detail.execution_result.executed_at,
            approver_user_id=detail.execution_result.approver_user_id,
            htc_order_number=detail.execution_result.htc_order_number,
            fields_updated=detail.execution_result.fields_updated,
            old_values=detail.execution_result.old_values,
            new_values=detail.execution_result.new_values,
        )

    return GetPendingActionDetailResponse(
        id=detail.id,
        customer_id=detail.customer_id,
        customer_name=detail.customer_name,
        hawb=detail.hawb,
        htc_order_number=detail.htc_order_number,
        action_type=detail.action_type,
        status=detail.status,
        required_fields_present=detail.required_fields_present,
        required_fields_total=detail.required_fields_total,
        optional_fields_present=detail.optional_fields_present,
        optional_fields_total=detail.optional_fields_total,
        conflict_count=detail.conflict_count,
        error_message=detail.error_message,
        error_at=detail.error_at,
        is_read=detail.is_read,
        created_at=detail.created_at,
        updated_at=detail.updated_at,
        last_processed_at=detail.last_processed_at,
        fields=api_fields,
        field_metadata=api_field_metadata,
        contributing_sources=api_sources,
        current_htc_values=detail.current_htc_values,
        execution_result=api_execution_result,
    )


@router.patch("/{action_id}/read-status", response_model=SetReadStatusResponse)
async def set_read_status(
    action_id: int,
    request: SetReadStatusRequest,
    service: OrderManagementService = Depends(lambda: ServiceContainer.get_order_management_service())
) -> SetReadStatusResponse:
    """
    Set the read/unread status of a pending action.

    This is an idempotent operation - setting to the same value has no effect.
    """
    logger.debug(f"Set read status for action {action_id}: is_read={request.is_read}")

    service.set_read_status(
        pending_action_id=action_id,
        is_read=request.is_read,
    )

    return SetReadStatusResponse(
        id=action_id,
        is_read=request.is_read,
    )


@router.post("/{action_id}/approve", response_model=ApproveActionResponse)
async def approve_action(
    action_id: int,
    request: ApproveActionRequest,
    service: OrderManagementService = Depends(lambda: ServiceContainer.get_order_management_service())
) -> ApproveActionResponse:
    """
    Approve a pending action for execution.

    For now, this sets the status to 'completed' and logs what would be sent to HTC.
    In the future, this will actually execute the action against HTC.

    Only actions with status 'ready', 'incomplete', or 'conflict' can be approved.

    If requires_review is True in the response, the action was NOT approved and
    remains in its current status. The frontend should show the review_reason
    to the user and refresh the detail view.
    """
    logger.info(
        f"Approve pending action {action_id}: "
        f"detail_viewed_at={request.detail_viewed_at} "
        f"(type={type(request.detail_viewed_at).__name__ if request.detail_viewed_at else 'None'}), "
        f"approver_user_id={request.approver_user_id}"
    )

    result = service.approve_action(
        pending_action_id=action_id,
        detail_viewed_at=request.detail_viewed_at,
        approver_user_id=request.approver_user_id,
    )

    # Determine new_status and message based on result
    if result.requires_review:
        # Action needs review - status unchanged
        new_status = "ready"  # Action stays in ready state
        message = f"Action requires review: {result.review_reason}"
    elif result.success:
        # Action approved successfully
        new_status = "completed"
        message = "Action approved successfully (mock)"
    else:
        # Action approval failed
        new_status = "ready"
        message = result.error_message

    return ApproveActionResponse(
        pending_action_id=result.pending_action_id,
        success=result.success,
        action_type=result.action_type,
        htc_order_number=result.htc_order_number,
        new_status=new_status,
        message=message,
        requires_review=result.requires_review,
        review_reason=result.review_reason,
    )


@router.post("/{action_id}/reject", response_model=RejectActionResponse)
async def reject_action(
    action_id: int,
    request: RejectActionRequest,
    service: OrderManagementService = Depends(lambda: ServiceContainer.get_order_management_service())
) -> RejectActionResponse:
    """
    Reject a pending action.

    Sets the status to 'rejected'. The action cannot be retried after rejection.
    """
    logger.debug(f"Reject pending action {action_id}: reason={request.reason}")

    success = service.reject_action(
        pending_action_id=action_id,
        reason=request.reason,
    )

    if not success:
        raise HTTPException(
            status_code=400,
            detail="Cannot reject action. It may not exist or is already in a terminal state."
        )

    return RejectActionResponse(
        pending_action_id=action_id,
        success=True,
        new_status="rejected",
        message="Action rejected successfully",
    )


@router.post("/{action_id}/select-field", response_model=SelectFieldValueResponse)
async def select_field_value(
    action_id: int,
    request: SelectFieldValueRequest,
    service: OrderManagementService = Depends(lambda: ServiceContainer.get_order_management_service())
) -> SelectFieldValueResponse:
    """
    Select a specific field value for a pending action.

    Used for:
    - Resolving conflicts by selecting one of multiple conflicting values
    - Changing a previously selected value to a different option

    The selected value will have is_selected=TRUE, and all other values
    for the same field will have is_selected=FALSE.
    """
    logger.info(f"Select field value: action={action_id}, field_id={request.field_id}")

    try:
        # Get the field to return its name in response
        field = service.pending_action_field_repo.get_by_id(request.field_id)
        if field is None:
            raise HTTPException(status_code=404, detail=f"Field {request.field_id} not found")

        updated_action = service.select_field_value(
            pending_action_id=action_id,
            field_id=request.field_id,
        )

        return SelectFieldValueResponse(
            pending_action_id=action_id,
            field_id=request.field_id,
            field_name=field.field_name,
            new_status=updated_action.status,
            success=True,
            message=f"Selected value for field '{field.field_name}'",
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/{action_id}/set-field-approval", response_model=SetFieldApprovalResponse)
async def set_field_approval(
    action_id: int,
    request: SetFieldApprovalRequest,
    service: OrderManagementService = Depends(lambda: ServiceContainer.get_order_management_service())
) -> SetFieldApprovalResponse:
    """
    Set whether a field should be included in an update.

    Only applicable for pending actions with action_type='update'.
    This toggles the is_approved_for_update flag for ALL values of the field
    (approval is per-field-name, not per-value).

    When is_approved=True, the field will be included when the update is executed.
    When is_approved=False, the field will be skipped during update execution.
    """
    logger.info(
        f"Set field approval: action={action_id}, "
        f"field={request.field_name}, approved={request.is_approved}"
    )

    try:
        is_approved = service.set_field_approval(
            pending_action_id=action_id,
            field_name=request.field_name,
            is_approved=request.is_approved,
        )

        return SetFieldApprovalResponse(
            pending_action_id=action_id,
            field_name=request.field_name,
            is_approved=is_approved,
            success=True,
            message=f"Field '{request.field_name}' {'included in' if is_approved else 'excluded from'} update",
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
