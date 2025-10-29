"""
ETO Runs FastAPI Router
REST endpoints for ETO processing control and monitoring
"""
import logging
from typing import Optional, Literal, Any
from fastapi import APIRouter, Query, status, Depends, File, UploadFile

from api.schemas.eto_runs import (
    # TODO: Import schemas once defined
    # EtoRunListItem,
    # EtoRunDetail,
    # CreateEtoRunResponse,
)
from api.mappers.eto_runs import (
    # TODO: Import mappers once defined
    # eto_run_list_to_api,
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


@router.get("")  # , response_model=list[EtoRunListItem])
async def list_eto_runs(
    status_filter: Optional[Literal["not_started", "processing", "success", "failure", "needs_template", "skipped"]] = Query(
        None,
        description="Filter by run status"
    ),
    limit: int = Query(50, ge=1, le=200, description="Number of runs to return"),
    offset: int = Query(0, ge=0, description="Number of runs to skip"),
    sort_by: Literal["started_at", "completed_at"] = Query("started_at", description="Field to sort by"),
    sort_order: Literal["asc", "desc"] = Query("desc", description="Sort order"),
    # service: EtoProcessingService = Depends(lambda: ServiceContainer.get_eto_processing_service())
) -> Any:  # list[EtoRunListItem]:
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
    # runs = service.list_runs(
    #     status=status_filter,
    #     limit=limit,
    #     offset=offset,
    #     sort_by=sort_by,
    #     sort_order=sort_order
    # )
    # return eto_run_list_to_api(runs)

    logger.info(f"List ETO runs: status={status_filter}, limit={limit}, offset={offset}")
    return []  # TODO: Implement


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


@router.post("", status_code=status.HTTP_201_CREATED)  # , response_model=CreateEtoRunResponse)
async def create_eto_run(
    file: UploadFile = File(..., description="PDF file to process"),
    # service: EtoProcessingService = Depends(lambda: ServiceContainer.get_eto_processing_service())
) -> Any:  # CreateEtoRunResponse:
    """
    Create new ETO run via manual PDF upload.

    Flow:
    1. Upload PDF file and create pdf_files record
    2. Create eto_runs record with status="not_started"
    3. Background worker automatically picks up and processes run

    Returns:
    - Created run ID
    - Initial status: "not_started"
    - PDF file ID
    """
    # run = service.create_run_from_upload(file)
    # return {
    #     "id": run.id,
    #     "status": run.status,
    #     "pdf_file_id": run.pdf_file_id
    # }

    logger.info(f"Create ETO run from upload: filename={file.filename}")
    return {}  # TODO: Implement


@router.post("/{id}/reprocess")  # , response_model=EtoRunDetail)
async def reprocess_eto_run(
    id: int,
    # service: EtoProcessingService = Depends(lambda: ServiceContainer.get_eto_processing_service())
) -> Any:  # EtoRunDetail:
    """
    Reprocess failed or skipped ETO run.

    Flow:
    1. Verify run status is "failure" or "skipped"
    2. Delete all stage records (template_matching, extraction, pipeline_execution + steps)
    3. Reset status to "not_started"
    4. Clear error fields
    5. Worker picks up and reprocesses from beginning

    Errors:
    - 404: Run not found
    - 400: Invalid status (can only reprocess failure/skipped runs)
    """
    # run = service.reprocess_run(id)
    # return eto_run_detail_to_api(run)

    logger.info(f"Reprocess ETO run: id={id}")
    return {}  # TODO: Implement


@router.post("/{id}/skip")  # , response_model=EtoRunDetail)
async def skip_eto_run(
    id: int,
    # service: EtoProcessingService = Depends(lambda: ServiceContainer.get_eto_processing_service())
) -> Any:  # EtoRunDetail:
    """
    Mark ETO run as skipped.

    Flow:
    1. Verify run status is "failure" or "needs_template"
    2. Set status to "skipped"
    3. Preserves all stage data (for historical reference)

    Purpose:
    - Exclude from bulk reprocessing operations
    - Indicate intentional decision to not process this PDF
    - Can be reprocessed or deleted later

    Errors:
    - 404: Run not found
    - 400: Invalid status (can only skip failure/needs_template runs)
    """
    # run = service.skip_run(id)
    # return eto_run_detail_to_api(run)

    logger.info(f"Skip ETO run: id={id}")
    return {}  # TODO: Implement


@router.delete("/{id}")  # , response_model=EtoRunDetail)
async def delete_eto_run(
    id: int,
    # service: EtoProcessingService = Depends(lambda: ServiceContainer.get_eto_processing_service())
) -> Any:  # EtoRunDetail:
    """
    Permanently delete ETO run.

    Flow:
    1. Verify run status is "skipped"
    2. Cascade delete all stage records
    3. Delete run record
    4. Optionally delete PDF file if not referenced elsewhere

    Restrictions:
    - Can only delete runs with status="skipped"
    - Deletion is permanent (no recovery)

    Errors:
    - 404: Run not found
    - 400: Invalid status (can only delete skipped runs)
    """
    # deleted_run = service.delete_run(id)
    # return eto_run_detail_to_api(deleted_run)

    logger.info(f"Delete ETO run: id={id}")
    return {}  # TODO: Implement


# ========== Bulk Operations (Future) ==========

@router.post("/bulk-reprocess")
async def bulk_reprocess_runs(
    # run_ids: list[int],
    # service: EtoProcessingService = Depends(lambda: ServiceContainer.get_eto_processing_service())
) -> Any:
    """
    Reprocess multiple failed runs in bulk.

    Future enhancement - not required for MVP.
    """
    logger.info("Bulk reprocess runs")
    return {}  # TODO: Implement


@router.post("/bulk-skip")
async def bulk_skip_runs(
    # run_ids: list[int],
    # service: EtoProcessingService = Depends(lambda: ServiceContainer.get_eto_processing_service())
) -> Any:
    """
    Skip multiple failed/needs_template runs in bulk.

    Future enhancement - not required for MVP.
    """
    logger.info("Bulk skip runs")
    return {}  # TODO: Implement
