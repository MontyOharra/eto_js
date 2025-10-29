"""
ETO Runs FastAPI Router
REST endpoints for ETO processing control and monitoring
"""
import logging
from typing import Optional, Literal, Any
from fastapi import APIRouter, Query, status, Depends, File, UploadFile

from api.schemas.eto_runs import (
    GetEtoRunsResponse,
    BulkRunIdsRequest,
    CreateEtoRunRequest,
    CreateEtoRunResponse,
    # TODO: Import additional schemas once defined
    # EtoRunDetail,
)
from api.mappers.eto_runs import (
    eto_run_list_to_api,
    eto_run_to_create_response,
    # TODO: Import additional mappers once defined
    # eto_run_detail_to_api,
)

from shared.services.service_container import ServiceContainer
from shared.exceptions.service import ValidationError
# from features.eto_processing.service import EtoProcessingService

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


@router.get("/{id}")  # , response_model=EtoRunDetail)
async def get_eto_run(
    id: int,
    # service: EtoProcessingService = Depends(lambda: ServiceContainer.get_eto_processing_service())
) -> Any:  # EtoRunDetail:
    """
    Get full ETO run details including all stage information.

    Returns:
    - Core run data (status, timestamps, errors)
    - Stage 1: Template matching (status, matched template)
    - Stage 2: Data extraction (status, extracted data)
    - Stage 3: Pipeline execution (status, executed actions, step-by-step trace)

    Different data shown based on run status:
    - success: All stages with full data
    - failure: Partial stages, error details, which stage failed
    - needs_template: Template matching results only
    """
    # run_detail = service.get_run_detail(id)
    # return eto_run_detail_to_api(run_detail)

    logger.info(f"Get ETO run detail: id={id}")
    return {}  # TODO: Implement


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
    # request: ReprocessEtoRunsRequest,
    # service: EtoProcessingService = Depends(lambda: ServiceContainer.get_eto_processing_service())
) -> None:
    """
    Reprocess failed or skipped ETO runs (bulk operation).

    Request body: { run_ids: [1, 2, 3] }

    For single run, send array with one ID: { run_ids: [1] }

    Flow (for each run):
    1. Verify run status is "failure" or "skipped"
    2. Delete all stage records (template_matching, extraction, pipeline_execution + steps)
    3. Reset status to "not_started"
    4. Clear error fields
    5. Worker picks up and reprocesses from beginning

    Response: 204 No Content

    Errors:
    - 404: One or more runs not found
    - 400: One or more runs have invalid status (can only reprocess failure/skipped runs)
    """
    # service.reprocess_runs(request.run_ids)
    logger.info("Reprocess ETO runs")
    return None  # TODO: Implement


@router.post("/skip", status_code=status.HTTP_204_NO_CONTENT)
async def skip_eto_runs(
    # request: SkipEtoRunsRequest,
    # service: EtoProcessingService = Depends(lambda: ServiceContainer.get_eto_processing_service())
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
    # service.skip_runs(request.run_ids)
    logger.info("Skip ETO runs")
    return None  # TODO: Implement


@router.delete("", status_code=status.HTTP_204_NO_CONTENT)
async def delete_eto_runs(
    # request: DeleteEtoRunsRequest,
    # service: EtoProcessingService = Depends(lambda: ServiceContainer.get_eto_processing_service())
) -> None:
    """
    Permanently delete ETO runs (bulk operation).

    Request body: { run_ids: [1, 2, 3] }

    For single run, send array with one ID: { run_ids: [1] }

    Flow (for each run):
    1. Verify run status is "skipped"
    2. Cascade delete all stage records
    3. Delete run record
    4. Optionally delete PDF file if not referenced elsewhere

    Restrictions:
    - Can only delete runs with status="skipped"
    - Deletion is permanent (no recovery)

    Response: 204 No Content

    Errors:
    - 404: One or more runs not found
    - 400: One or more runs have invalid status (can only delete skipped runs)
    """
    # service.delete_runs(request.run_ids)
    logger.info("Delete ETO runs")
    return None  # TODO: Implement
