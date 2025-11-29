"""
ETO Runs FastAPI Router
REST endpoints for ETO processing control and monitoring
"""
import asyncio
import json
import logging
from datetime import datetime
from typing import Optional, Literal, Any
from fastapi import APIRouter, Query, status, Depends, File, UploadFile, Request
from fastapi.responses import StreamingResponse

from api.schemas.eto_runs import (
    GetEtoRunsResponse,
    BulkRunIdsRequest,
    CreateEtoRunRequest,
    CreateEtoRunResponse,
    UpdateEtoRunRequest,
    EtoRunDetail,
    SubRunOperationResponse,
    RunOperationResponse,
    EtoSubRunFullDetail,
)
from api.mappers.eto_runs import (
    eto_run_list_to_api,
    eto_run_to_create_response,
    eto_run_detail_to_api,
    eto_sub_run_full_detail_to_api,
)

from shared.services.service_container import ServiceContainer
from shared.exceptions.service import ValidationError
from shared.events.eto_events import eto_event_manager
from features.eto_runs.service import EtoRunsService

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/eto-runs",
    tags=["ETO Runs"]
)


@router.get("", response_model=GetEtoRunsResponse)
async def list_eto_runs(
    is_read: Optional[bool] = Query(
        None,
        description="Filter by read status (true=read, false=unread)"
    ),
    has_sub_run_status: Optional[Literal["needs_template", "failure", "success", "skipped", "processing"]] = Query(
        None,
        description="Filter runs that have at least one sub-run with this status"
    ),
    search: Optional[str] = Query(
        None,
        description="Search in PDF filename, email sender, and subject"
    ),
    date_from: Optional[datetime] = Query(
        None,
        description="Filter runs created on or after this date (ISO 8601)"
    ),
    date_to: Optional[datetime] = Query(
        None,
        description="Filter runs created on or before this date (ISO 8601)"
    ),
    limit: int = Query(50, ge=1, le=200, description="Number of runs to return"),
    offset: int = Query(0, ge=0, description="Number of runs to skip"),
    sort_by: Literal["last_processed_at", "created_at", "started_at", "completed_at"] = Query(
        "last_processed_at",
        description="Field to sort by"
    ),
    sort_order: Literal["asc", "desc"] = Query("desc", description="Sort order"),
    service = Depends(lambda: ServiceContainer.get_eto_runs_service())
) -> GetEtoRunsResponse:
    """
    List ETO runs with filtering, search, and pagination.

    Filters:
    - is_read: Filter by read/unread status
    - has_sub_run_status: Filter runs containing sub-runs with specific status
      (e.g., "needs_template" to find runs needing user attention)
    - search: Text search across PDF filename, email sender, and subject
    - date_from/date_to: Date range filter on created_at

    Sorting:
    - last_processed_at: Most recently processed (default)
    - created_at: When the run was created
    - started_at: When processing started
    - completed_at: When processing completed
    """
    logger.debug(f"List ETO runs: is_read={is_read}, has_sub_run_status={has_sub_run_status}, search={search}, limit={limit}, offset={offset}")

    # Get runs with all related data using efficient SQL joins
    runs = service.list_runs_with_relations(
        is_read=is_read,
        has_sub_run_status=has_sub_run_status,
        search_query=search,
        date_from=date_from,
        date_to=date_to,
        limit=limit,
        offset=offset,
        order_by=sort_by,
        desc=(sort_order == "desc")
    )

    # Get total count for pagination (using same filters but no limit/offset)
    # TODO: Optimize this with a COUNT query instead of fetching all
    all_runs = service.list_runs_with_relations(
        is_read=is_read,
        has_sub_run_status=has_sub_run_status,
        search_query=search,
        date_from=date_from,
        date_to=date_to,
        limit=None,
        offset=None
    )
    total = len(all_runs)

    # Convert domain objects to API schema
    items = eto_run_list_to_api(runs)

    return GetEtoRunsResponse(
        items=items,
        total=total,
        limit=limit,
        offset=offset
    )


@router.get("/events")
async def eto_run_events_stream(request: Request):
    """
    Server-Sent Events (SSE) endpoint for real-time ETO run updates.

    Streams events to connected clients whenever ETO runs are created, updated, or deleted.
    Multiple clients can connect simultaneously - each gets their own event stream.

    Event Types:
    - run_created: New run created (manual upload or email ingestion)
    - run_updated: Run status or processing_step changed
    - run_deleted: Run deleted

    Event Format:
    data: {
        "type": "run_created" | "run_updated" | "run_deleted",
        "data": { ... run data ... },
        "timestamp": "2025-10-29T10:00:00Z"
    }

    Connection automatically reconnects if dropped.
    """
    # Create a unique queue for this client connection
    client_queue = asyncio.Queue(maxsize=100)  # Buffer up to 100 events

    async def event_generator():
        # Register this client with the global event manager
        eto_event_manager.register_client(client_queue)
        logger.debug(f"SSE client connected - total: {eto_event_manager.get_client_count()}")

        try:
            # Send initial connection event to establish the stream
            yield f": connected\n\n"  # SSE comment - keeps connection alive

            while not eto_event_manager.is_shutting_down():
                try:
                    # Check if client disconnected
                    try:
                        if await asyncio.wait_for(request.is_disconnected(), timeout=0.1):
                            logger.debug("SSE client disconnected")
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
                        logger.debug("SSE shutdown event received")
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
            logger.error(f"SSE error: {e}", exc_info=True)
        finally:
            # Always cleanup when connection closes
            eto_event_manager.unregister_client(client_queue)
            logger.debug(f"SSE client disconnected - remaining: {eto_event_manager.get_client_count()}")

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",  # Disable nginx buffering if behind nginx
        }
    )


@router.get("/{id}", response_model=EtoRunDetail)
async def get_eto_run(
    id: int,
    service = Depends(lambda: ServiceContainer.get_eto_runs_service())
) -> EtoRunDetail:
    """
    Get full ETO run details including all sub-run information.

    Returns:
    - Core run data (status, timestamps, errors)
    - PDF file info and source (manual or email)
    - List of sub-runs, each with:
      - Template info (if matched)
      - Extraction stage data (status, extracted fields)
      - Pipeline execution stage data (status, executed actions, steps)

    Sub-runs represent page sets matched to templates:
    - Matched sub-runs: Pages that matched a template, processed through extraction and pipeline
    - Unmatched groups: Pages that didn't match any template (needs_template status)
    - Skipped sub-runs: Pages manually skipped by user
    """
    logger.info(f"Get ETO run detail: id={id}")

    # Get detailed view from service
    detail_view = service.get_run_detail(id)

    # Convert to API schema
    return eto_run_detail_to_api(detail_view)


@router.patch("/{id}", status_code=status.HTTP_204_NO_CONTENT)
async def update_eto_run(
    id: int,
    request: UpdateEtoRunRequest,
    service = Depends(lambda: ServiceContainer.get_eto_runs_service())
) -> None:
    """
    Update an ETO run.

    Currently supports:
    - is_read: Mark run as read (True) or unread (False)

    Request body example:
    { "is_read": true }

    Response: 204 No Content

    Errors:
    - 404: Run not found
    """
    logger.info(f"Updating ETO run {id}: {request.model_dump(exclude_none=True)}")

    # Build updates dict from request, excluding None values
    updates = {}
    if request.is_read is not None:
        updates["is_read"] = request.is_read

    if updates:
        service.update_run(id, updates)

    return None


@router.post("", status_code=status.HTTP_201_CREATED, response_model=CreateEtoRunResponse)
async def create_eto_run(
    request: CreateEtoRunRequest,
    service = Depends(lambda: ServiceContainer.get_eto_runs_service())
) -> CreateEtoRunResponse:
    """
    Create new ETO run from an already-uploaded PDF.

    Prerequisites:
    1. PDF must be uploaded first via POST /api/pdf-files
    2. Use the returned pdf_file_id in this request

    Flow:
    1. Validates PDF file exists
    2. Creates eto_runs record with status="not_started"
    3. Background worker automatically picks up and processes run

    Returns:
    - Created run ID
    - Initial status: "not_started"
    - PDF file ID
    - Created timestamp
    """
    logger.info(f"Creating ETO run for PDF file {request.pdf_file_id}")

    # Create the run using the service
    # Manual uploads have source_type='manual' and no email association
    run = service.create_run(
        pdf_file_id=request.pdf_file_id,
        source_type='manual',
        source_email_id=None
    )

    # Convert to API response
    response = eto_run_to_create_response(run)

    logger.info(f"Created ETO run {response.id} for PDF {response.pdf_file_id}")
    return response


@router.post("/reprocess", status_code=status.HTTP_204_NO_CONTENT)
async def reprocess_eto_runs(
    request: BulkRunIdsRequest,
    service: EtoRunsService = Depends(lambda: ServiceContainer.get_eto_runs_service())
) -> None:
    """
    Reprocess failed or skipped ETO runs (bulk operation).

    Request body: { run_ids: [1, 2, 3] }

    For single run, send array with one ID: { run_ids: [1] }

    Flow (for each run):
    1. Verify run status is "failure", "skipped", or "needs_template"
    2. Get all sub-runs for the parent run
    3. Delete sub-run stage records (extraction, pipeline_execution)
    4. Reset each sub-run to "not_started" status
    5. Reset parent run to "processing" status
    6. Clear error fields
    7. Worker picks up sub-runs and reprocesses

    Response: 204 No Content

    Errors:
    - 404: One or more runs not found
    - 400: One or more runs have invalid status (can only reprocess failure/skipped/needs_template runs)
    """
    logger.info(f"Reprocessing {len(request.run_ids)} ETO runs: {request.run_ids}")
    service.reprocess_runs(request.run_ids)
    return None


@router.post("/skip", status_code=status.HTTP_204_NO_CONTENT)
async def skip_eto_runs(
    request: BulkRunIdsRequest,
    service: EtoRunsService = Depends(lambda: ServiceContainer.get_eto_runs_service())
) -> None:
    """
    Mark ETO runs as skipped (bulk operation).

    Request body: { run_ids: [1, 2, 3] }

    For single run, send array with one ID: { run_ids: [1] }

    Flow (for each run):
    1. Verify run status is "failure" or "needs_template"
    2. Set status to "skipped"
    3. Preserves all stage data (for historical reference)

    Purpose:
    - Exclude from bulk reprocessing operations
    - Indicate intentional decision to not process this PDF
    - Can be reprocessed or deleted later

    Response: 204 No Content

    Errors:
    - 404: One or more runs not found
    - 400: One or more runs have invalid status (can only skip failure/needs_template runs)
    """
    logger.info(f"Skipping {len(request.run_ids)} ETO runs: {request.run_ids}")
    service.skip_runs(request.run_ids)
    return None


@router.delete("", status_code=status.HTTP_204_NO_CONTENT)
async def delete_eto_runs(
    request: BulkRunIdsRequest,
    service: EtoRunsService = Depends(lambda: ServiceContainer.get_eto_runs_service())
) -> None:
    """
    Permanently delete ETO runs (bulk operation).

    Request body: { run_ids: [1, 2, 3] }

    For single run, send array with one ID: { run_ids: [1] }

    Flow (for each run):
    1. Verify run status is "skipped"
    2. Delete run record (cascade deletes all sub-runs and their stage records)
    3. Note: PDF file is NOT deleted (may be referenced elsewhere)

    Database cascade chain:
    - eto_runs → eto_sub_runs
    - eto_sub_runs → eto_sub_run_extractions
    - eto_sub_runs → eto_sub_run_pipeline_executions
    - eto_sub_run_pipeline_executions → eto_sub_run_pipeline_execution_steps

    Restrictions:
    - Can only delete runs with status="skipped"
    - Deletion is permanent (no recovery)

    Response: 204 No Content

    Errors:
    - 404: One or more runs not found
    - 400: One or more runs have invalid status (can only delete skipped runs)
    """
    logger.info(f"Deleting {len(request.run_ids)} ETO runs: {request.run_ids}")
    service.delete_runs(request.run_ids)
    return None


# =============================================================================
# Sub-Run Level Operations
# =============================================================================

@router.get("/sub-runs/{sub_run_id}", response_model=EtoSubRunFullDetail)
async def get_sub_run_detail(
    sub_run_id: int,
    service: EtoRunsService = Depends(lambda: ServiceContainer.get_eto_runs_service())
) -> EtoSubRunFullDetail:
    """
    Get full sub-run details including extraction and pipeline execution data.

    Returns:
    - Core sub-run data (status, matched_pages, template info)
    - PDF file info (from parent run)
    - Extraction stage data (status, extracted fields with bounding boxes)
    - Pipeline execution stage data (status, executed actions)
    - Error information (if failed)

    Used by the sub-run detail modal to display extracted fields overlaid on
    the PDF viewer and show pipeline execution results.
    """
    logger.info(f"Get sub-run detail: sub_run_id={sub_run_id}")

    # Get detailed view from service
    detail_view = service.get_sub_run_detail(sub_run_id)

    # Convert to API schema
    return eto_sub_run_full_detail_to_api(detail_view)


@router.post("/sub-runs/{sub_run_id}/reprocess", response_model=SubRunOperationResponse)
async def reprocess_sub_run(
    sub_run_id: int,
    service: EtoRunsService = Depends(lambda: ServiceContainer.get_eto_runs_service())
) -> SubRunOperationResponse:
    """
    Reprocess a single sub-run.

    Deletes the sub-run and all its stage data (extraction, pipeline execution),
    then creates a new sub-run with the same pages for the worker to process.

    Flow:
    1. Delete extraction record (if exists)
    2. Delete pipeline execution record (if exists)
    3. Delete the sub-run
    4. Create new sub-run with same pages, status='not_started', no template
    5. Worker picks up and runs template matching (Phase 1)

    Returns:
    - new_sub_run_id: ID of the newly created sub-run
    - eto_run_id: Parent ETO run ID

    Errors:
    - 404: Sub-run not found
    """
    logger.info(f"Reprocessing sub-run {sub_run_id}")

    # Get parent run ID before reprocessing (sub-run will be deleted)
    sub_run = service.sub_run_repo.get_by_id(sub_run_id)
    if not sub_run:
        from shared.exceptions.service import ObjectNotFoundError
        raise ObjectNotFoundError(f"Sub-run {sub_run_id} not found")

    eto_run_id = sub_run.eto_run_id
    new_sub_run_id = service.reprocess_sub_run(sub_run_id)

    return SubRunOperationResponse(
        new_sub_run_id=new_sub_run_id,
        eto_run_id=eto_run_id
    )


@router.post("/sub-runs/{sub_run_id}/skip", response_model=SubRunOperationResponse)
async def skip_sub_run(
    sub_run_id: int,
    service: EtoRunsService = Depends(lambda: ServiceContainer.get_eto_runs_service())
) -> SubRunOperationResponse:
    """
    Skip a single sub-run.

    Deletes the sub-run and all its stage data (extraction, pipeline execution),
    then creates a new sub-run with the same pages and status='skipped'.

    Can only skip sub-runs with status 'failure' or 'needs_template'.

    Flow:
    1. Validate sub-run status
    2. Delete extraction record (if exists)
    3. Delete pipeline execution record (if exists)
    4. Delete the sub-run
    5. Create new sub-run with same pages, status='skipped'

    Returns:
    - new_sub_run_id: ID of the newly created skipped sub-run
    - eto_run_id: Parent ETO run ID

    Errors:
    - 404: Sub-run not found
    - 400: Sub-run has invalid status (can only skip failure/needs_template)
    """
    logger.info(f"Skipping sub-run {sub_run_id}")

    # Get parent run ID before skipping (sub-run will be deleted)
    sub_run = service.sub_run_repo.get_by_id(sub_run_id)
    if not sub_run:
        from shared.exceptions.service import ObjectNotFoundError
        raise ObjectNotFoundError(f"Sub-run {sub_run_id} not found")

    eto_run_id = sub_run.eto_run_id
    new_sub_run_id = service.skip_sub_run(sub_run_id)

    return SubRunOperationResponse(
        new_sub_run_id=new_sub_run_id,
        eto_run_id=eto_run_id
    )


# =============================================================================
# Run-Level Aggregated Operations
# =============================================================================

@router.post("/{run_id}/reprocess", response_model=RunOperationResponse)
async def reprocess_run(
    run_id: int,
    service: EtoRunsService = Depends(lambda: ServiceContainer.get_eto_runs_service())
) -> RunOperationResponse:
    """
    Reprocess all failed/needs_template sub-runs for a run.

    Aggregates all sub-runs with status 'failure' or 'needs_template' into a single
    new sub-run with status 'not_started'. The worker will pick this up and run
    template matching (Phase 1).

    Flow:
    1. Get all sub-runs with status 'failure' or 'needs_template'
    2. Collect all their pages
    3. Delete those sub-runs (with child extraction/pipeline records)
    4. Create one new sub-run with all pages, status='not_started', no template
    5. Update parent run status

    Returns:
    - run_id: The ETO run ID
    - new_sub_run_id: ID of the newly created sub-run (None if no eligible sub-runs)
    - message: Description of what was done

    Errors:
    - 404: Run not found
    """
    logger.info(f"Reprocessing run {run_id}")

    new_sub_run_id = service.reprocess_run(run_id)

    if new_sub_run_id is None:
        return RunOperationResponse(
            run_id=run_id,
            new_sub_run_id=None,
            message="No eligible sub-runs to reprocess (no failure or needs_template sub-runs found)"
        )

    return RunOperationResponse(
        run_id=run_id,
        new_sub_run_id=new_sub_run_id,
        message="Successfully aggregated failed/needs_template sub-runs into new sub-run for reprocessing"
    )


@router.post("/{run_id}/skip", response_model=RunOperationResponse)
async def skip_run(
    run_id: int,
    service: EtoRunsService = Depends(lambda: ServiceContainer.get_eto_runs_service())
) -> RunOperationResponse:
    """
    Skip all failed/needs_template sub-runs for a run.

    Aggregates all sub-runs with status 'failure' or 'needs_template' into a single
    new sub-run with status 'skipped'.

    Flow:
    1. Get all sub-runs with status 'failure' or 'needs_template'
    2. Collect all their pages
    3. Delete those sub-runs (with child extraction/pipeline records)
    4. Create one new sub-run with all pages, status='skipped'
    5. Update parent run status

    Returns:
    - run_id: The ETO run ID
    - new_sub_run_id: ID of the newly created skipped sub-run (None if no eligible sub-runs)
    - message: Description of what was done

    Errors:
    - 404: Run not found
    """
    logger.info(f"Skipping run {run_id}")

    new_sub_run_id = service.skip_run(run_id)

    if new_sub_run_id is None:
        return RunOperationResponse(
            run_id=run_id,
            new_sub_run_id=None,
            message="No eligible sub-runs to skip (no failure or needs_template sub-runs found)"
        )

    return RunOperationResponse(
        run_id=run_id,
        new_sub_run_id=new_sub_run_id,
        message="Successfully aggregated failed/needs_template sub-runs into skipped sub-run"
    )
