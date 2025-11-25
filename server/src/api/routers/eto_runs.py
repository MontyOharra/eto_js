"""
ETO Runs FastAPI Router
REST endpoints for ETO processing control and monitoring
"""
import asyncio
import json
import logging
from typing import Optional, Literal, Any
from fastapi import APIRouter, Query, status, Depends, File, UploadFile, Request
from fastapi.responses import StreamingResponse

from api.schemas.eto_runs import (
    GetEtoRunsResponse,
    BulkRunIdsRequest,
    CreateEtoRunRequest,
    CreateEtoRunResponse,
    EtoRunDetail,
)
from api.mappers.eto_runs import (
    eto_run_list_to_api,
    eto_run_to_create_response,
    eto_run_detail_to_api,
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
    status_filter: Optional[Literal["not_started", "processing", "success", "failure", "needs_template", "skipped"]] = Query(
        None,
        description="Filter by run status"
    ),
    limit: int = Query(50, ge=1, le=200, description="Number of runs to return"),
    offset: int = Query(0, ge=0, description="Number of runs to skip"),
    sort_by: Literal["started_at", "completed_at", "created_at"] = Query("created_at", description="Field to sort by"),
    sort_order: Literal["asc", "desc"] = Query("desc", description="Sort order"),
    service = Depends(lambda: ServiceContainer.get_eto_runs_service())
) -> GetEtoRunsResponse:
    """
    List ETO runs with filtering by status and pagination.

    Status filter creates 6 separate views (one per status) for frontend tables:
    - not_started: Queued for processing
    - processing: Currently executing
    - success: Completed successfully
    - failure: Failed during processing
    - needs_template: No matching template found
    - skipped: Manually skipped by user
    """
    logger.info(f"List ETO runs: status={status_filter}, limit={limit}, offset={offset}")

    # Get runs with all related data using efficient SQL joins
    runs = service.list_runs_with_relations(
        status=status_filter,
        limit=limit,
        offset=offset,
        order_by=sort_by,
        desc=(sort_order == "desc")
    )

    # Get total count for pagination (using same filters but no limit/offset)
    all_runs = service.list_runs(
        status=status_filter,
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
        logger.info(f"SSE client connected - total: {eto_event_manager.get_client_count()}")

        try:
            # Send initial connection event to establish the stream
            yield f": connected\n\n"  # SSE comment - keeps connection alive

            while not eto_event_manager.is_shutting_down():
                try:
                    # Check if client disconnected
                    try:
                        if await asyncio.wait_for(request.is_disconnected(), timeout=0.1):
                            logger.info("SSE client disconnected")
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
                        logger.info("SSE shutdown event received")
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
            logger.info(f"SSE client disconnected - remaining: {eto_event_manager.get_client_count()}")

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
    run = service.create_run(request.pdf_file_id)

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
