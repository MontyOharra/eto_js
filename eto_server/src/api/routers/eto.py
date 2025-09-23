"""
ETO Processing API Router
API endpoints for managing ETO (Extract, Transform, Order) processing workflows
"""
import logging
from typing import List, Optional, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, status, Query
from pydantic import BaseModel

from shared.services.service_container import ServiceContainer, get_service_container
from shared.models.eto_processing import (
    EtoRun, EtoRunSummary, EtoRunStatus, EtoRunResetResult
)
from shared.exceptions import ObjectNotFoundError, ServiceError, ValidationError
from shared.utils import DateTimeUtils

logger = logging.getLogger(__name__)

# Request models for bulk operations
class BulkRunRequest(BaseModel):
    """Request model for bulk operations on ETO runs"""
    run_ids: List[int]

router = APIRouter(
    prefix="/eto-runs",
    tags=["ETO Processing"]
)


@router.get("/", response_model=List[EtoRunSummary])
def get_runs(
    eto_run_status: Optional[str] = Query(None, description="Filter by processing status"),
    limit: Optional[int] = Query(50, ge=1, le=1000, description="Maximum number of results"),
    offset: Optional[int] = Query(0, ge=0, description="Number of results to skip"),
    order_by: str = Query("created_at", description="Field to order by"),
    order_direction: str = Query("desc", description="Sort direction (asc, desc)"),
    since_date: Optional[str] = Query(None, description="Only include runs created after this date (ISO format)"),
    container: ServiceContainer = Depends(get_service_container)
):
    """
    Get ETO runs with filtering, pagination, and ordering

    Query parameters:
    - **status**: Filter by processing status (not_started, processing, success, failure, needs_template, skipped)
    - **limit**: Maximum number of results (1-1000, default: 50)
    - **offset**: Number of results to skip (default: 0)
    - **order_by**: Field to order by (created_at, started_at, completed_at, default: created_at)
    - **order_direction**: Sort direction (asc, desc, default: desc)
    - **since_date**: Only include runs created after this date (ISO 8601 format)

    Returns runs with email information when the PDF originated from email ingestion.
    """
    try:
        eto_service = container.get_eto_service()

        # Parse since_date if provided
        since_date_parsed = None
        if since_date:
            try:
                since_date_parsed = DateTimeUtils.parse_iso_datetime(since_date)
            except Exception as e:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Invalid since_date format. Use ISO 8601 format: {e}"
                )

        # Get runs with filters
        runs = eto_service.get_runs(
            status=eto_run_status,
            limit=limit,
            offset=offset,
            order_by=order_by,
            order_direction=order_direction,
            since_date=since_date_parsed
        )

        logger.debug(f"Retrieved {len(runs)} ETO runs with filters")
        return runs

    except ServiceError as e:
        logger.error(f"Failed to get ETO runs: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Unexpected error getting ETO runs: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error"
        )


@router.get("/{run_id}", response_model=EtoRun)
def get_run_details(
    run_id: int,
    container: ServiceContainer = Depends(get_service_container)
):
    """
    Get detailed information for a specific ETO run

    For successful runs: includes extracted data, matched template, transformation process
    For failed runs: includes error details
    For all runs: includes processing timeline and status history
    """
    try:
        eto_service = container.get_eto_service()

        run = eto_service.get_run_by_id(run_id)
        if not run:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"ETO run {run_id} not found"
            )

        logger.debug(f"Retrieved ETO run {run_id} details")
        return run

    except ServiceError as e:
        logger.error(f"Failed to get ETO run {run_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Unexpected error getting ETO run {run_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error"
        )


@router.patch("/{run_id}/skip", response_model=EtoRun)
def skip_run(
    run_id: int,
    container: ServiceContainer = Depends(get_service_container)
):
    """
    Mark a needs_template or failed run as skipped

    Only runs with status 'failure' or 'needs_template' can be skipped.
    """
    try:
        eto_service = container.get_eto_service()

        updated_run = eto_service.skip_run(run_id)
        return updated_run

    except ObjectNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"ETO run {run_id} not found"
        )
    except ValidationError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except ServiceError as e:
        logger.error(f"Failed to skip ETO run {run_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Unexpected error skipping ETO run {run_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error"
        )


@router.delete("/{run_id}", response_model=EtoRun)
def delete_run(
    run_id: int,
    container: ServiceContainer = Depends(get_service_container)
):
    """
    Permanently delete a skipped ETO run from the database

    Only runs with status 'skipped' can be permanently deleted.
    """
    try:
        eto_service = container.get_eto_service()

        deleted_run = eto_service.delete_run(run_id)

        logger.info(f"Permanently deleted ETO run {run_id}")
        return deleted_run

    except ObjectNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"ETO run {run_id} not found"
        )
    except ValidationError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except ServiceError as e:
        logger.error(f"Failed to delete ETO run {run_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Unexpected error deleting ETO run {run_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error"
        )


@router.patch("/{run_id}/reprocess", response_model=EtoRun)
def reprocess_run(
    run_id: int,
    force: bool = Query(False, description="Force reprocessing even if already successful"),
    container: ServiceContainer = Depends(get_service_container)
):
    """
    Reset a run back to not_started status for background reprocessing

    Only runs with status 'skipped', 'failure', or 'needs_template' can be reset.
    Use force=true to reprocess successful runs.
    """
    try:
        eto_service = container.get_eto_service()

        reset_run = eto_service.reprocess_run(run_id, force=force)

        logger.info(f"Queued ETO run {run_id} for background reprocessing")
        return reset_run

    except ObjectNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"ETO run {run_id} not found"
        )
    except ValidationError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except ServiceError as e:
        logger.error(f"Failed to queue ETO run {run_id} for reprocessing: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Unexpected error queueing ETO run {run_id} for reprocessing: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error"
        )


@router.get("/health", response_model=Dict[str, Any])
def get_eto_health(
    container: ServiceContainer = Depends(get_service_container)
):
    """
    Get ETO service health and status information

    Returns detailed health information about the ETO processing service
    including worker status, processing capacity, and service health.
    """
    try:
        eto_service = container.get_eto_service()

        # Check if service is healthy
        is_healthy = eto_service.is_healthy()

        # Get worker status
        worker_status = eto_service.get_worker_status()

        health_data = {
            "status": "healthy" if is_healthy else "unhealthy",
            "service_name": "ETO Processing Service",
            "timestamp": DateTimeUtils.utc_now().isoformat(),
            "worker": worker_status,
            "details": {
                "processing_enabled": is_healthy,
                "database_connected": True,  # If we got worker status, DB is connected
                "template_service_available": True,  # Implied if service is working
                "background_processing": worker_status.get("worker_running", False)
            }
        }

        # Set appropriate HTTP status based on health
        if not is_healthy:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail=health_data
            )

        logger.debug("Retrieved ETO service health information")
        return health_data

    except HTTPException:
        # Re-raise HTTP exceptions (like 503 above)
        raise
    except ServiceError as e:
        logger.error(f"Failed to get ETO health: {e}")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={
                "status": "error",
                "service_name": "ETO Processing Service",
                "timestamp": DateTimeUtils.utc_now().isoformat(),
                "error": str(e)
            }
        )
    except Exception as e:
        logger.error(f"Unexpected error getting ETO health: {e}")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={
                "status": "error",
                "service_name": "ETO Processing Service",
                "timestamp": DateTimeUtils.utc_now().isoformat(),
                "error": "Internal server error"
            }
        )


# ========== PDF Processing Entry Point ==========

@router.post("/process-pdf/{pdf_file_id}", response_model=EtoRun)
def queue_pdf_processing(
    pdf_file_id: int,
    container: ServiceContainer = Depends(get_service_container)
):
    """
    Queue a PDF file for background ETO processing

    Creates an ETO run with 'not_started' status that will be picked up
    by the background worker for automatic processing.

    Args:
        pdf_file_id: ID of the PDF file to process

    Returns:
        EtoRun with 'not_started' status - processing will happen in background
    """
    try:
        eto_service = container.get_eto_service()

        eto_run = eto_service.process_pdf(pdf_file_id)

        logger.info(f"Queued PDF {pdf_file_id} for background processing as ETO run {eto_run.id}")
        return eto_run

    except ServiceError as e:
        logger.error(f"Failed to queue PDF {pdf_file_id} for processing: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Unexpected error queueing PDF {pdf_file_id} for processing: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error"
        )


# ========== Worker Management ==========

@router.post("/worker/start", response_model=Dict[str, Any])
async def start_worker(
    container: ServiceContainer = Depends(get_service_container)
):
    """
    Start the background ETO processing worker

    The worker will continuously process runs with 'not_started' status.
    """
    try:
        eto_service = container.get_eto_service()

        success = await eto_service.start_worker()

        return {
            "action": "start_worker",
            "success": success,
            "message": "Worker started successfully" if success else "Worker was already running or disabled",
            "timestamp": DateTimeUtils.utc_now().isoformat()
        }

    except Exception as e:
        logger.error(f"Error starting ETO worker: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to start worker: {str(e)}"
        )


@router.post("/worker/stop", response_model=Dict[str, Any])
async def stop_worker(
    graceful: bool = Query(True, description="Whether to allow current batch to complete"),
    container: ServiceContainer = Depends(get_service_container)
):
    """
    Stop the background ETO processing worker

    Args:
        graceful: If true, allows current batch to complete before stopping
    """
    try:
        eto_service = container.get_eto_service()

        success = await eto_service.stop_worker(graceful=graceful)

        return {
            "action": "stop_worker",
            "success": success,
            "graceful": graceful,
            "message": "Worker stopped successfully" if success else "Worker was not running",
            "timestamp": DateTimeUtils.utc_now().isoformat()
        }

    except Exception as e:
        logger.error(f"Error stopping ETO worker: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to stop worker: {str(e)}"
        )


@router.post("/worker/pause", response_model=Dict[str, Any])
def pause_worker(
    container: ServiceContainer = Depends(get_service_container)
):
    """
    Emergency pause the background worker (stops processing new runs)

    Current runs will continue but no new runs will be started.
    """
    try:
        eto_service = container.get_eto_service()

        success = eto_service.pause_worker()

        return {
            "action": "pause_worker",
            "success": success,
            "message": "Worker paused successfully" if success else "Worker was not running",
            "timestamp": DateTimeUtils.utc_now().isoformat()
        }

    except Exception as e:
        logger.error(f"Error pausing ETO worker: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to pause worker: {str(e)}"
        )


@router.post("/worker/resume", response_model=Dict[str, Any])
def resume_worker(
    container: ServiceContainer = Depends(get_service_container)
):
    """
    Resume the background worker from paused state
    """
    try:
        eto_service = container.get_eto_service()

        success = eto_service.resume_worker()

        return {
            "action": "resume_worker",
            "success": success,
            "message": "Worker resumed successfully" if success else "Worker was not running or not paused",
            "timestamp": DateTimeUtils.utc_now().isoformat()
        }

    except Exception as e:
        logger.error(f"Error resuming ETO worker: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to resume worker: {str(e)}"
        )


@router.get("/worker/status", response_model=Dict[str, Any])
def get_worker_status(
    container: ServiceContainer = Depends(get_service_container)
):
    """
    Get detailed worker status and statistics

    Returns information about worker state, processing capacity,
    and current workload.
    """
    try:
        eto_service = container.get_eto_service()

        worker_status = eto_service.get_worker_status()

        return {
            **worker_status,
            "timestamp": DateTimeUtils.utc_now().isoformat()
        }

    except Exception as e:
        logger.error(f"Error getting ETO worker status: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get worker status: {str(e)}"
        )


# ========== Bulk Operations ==========

@router.patch("/bulk/skip", response_model=Dict[str, Any])
def bulk_skip_runs(
    request: BulkRunRequest,
    container: ServiceContainer = Depends(get_service_container)
):
    """
    Bulk skip multiple ETO runs

    Marks multiple needs_template or failed runs as skipped.
    Returns summary of the operation including which runs were successfully skipped.
    """
    try:
        if not request.run_ids:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No run IDs provided"
            )

        eto_service = container.get_eto_service()

        results = []
        errors = []

        for run_id in request.run_ids:
            try:
                updated_run = eto_service.skip_run(run_id)
                results.append({
                    "run_id": run_id,
                    "status": "success",
                    "new_status": updated_run.status.value
                })
            except (ObjectNotFoundError, ValidationError) as e:
                errors.append({
                    "run_id": run_id,
                    "status": "error",
                    "error": str(e)
                })
            except Exception as e:
                logger.error(f"Error skipping run {run_id}: {e}")
                errors.append({
                    "run_id": run_id,
                    "status": "error",
                    "error": "Internal error"
                })

        response = {
            "operation": "bulk_skip",
            "total_requested": len(request.run_ids),
            "successful": len(results),
            "failed": len(errors),
            "results": results,
            "errors": errors,
            "timestamp": DateTimeUtils.utc_now().isoformat()
        }

        logger.info(f"Bulk skip operation: {len(results)} successful, {len(errors)} failed")
        return response

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Unexpected error in bulk skip: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error"
        )


@router.patch("/bulk/reprocess", response_model=Dict[str, Any])
def bulk_reprocess_runs(
    request: BulkRunRequest,
    container: ServiceContainer = Depends(get_service_container)
):
    """
    Bulk reprocess multiple ETO runs

    Resets multiple skipped runs back to not_started status for reprocessing.
    Returns summary of the operation including which runs were successfully reset.
    """
    try:
        if not request.run_ids:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No run IDs provided"
            )

        eto_service = container.get_eto_service()

        results = []
        errors = []

        for run_id in request.run_ids:
            try:
                reset_run = eto_service.reprocess_run(run_id)
                results.append({
                    "run_id": run_id,
                    "status": "success",
                    "new_status": reset_run.status.value
                })
            except (ObjectNotFoundError, ValidationError) as e:
                errors.append({
                    "run_id": run_id,
                    "status": "error",
                    "error": str(e)
                })
            except Exception as e:
                logger.error(f"Error reprocessing run {run_id}: {e}")
                errors.append({
                    "run_id": run_id,
                    "status": "error",
                    "error": "Internal error"
                })

        response = {
            "operation": "bulk_reprocess",
            "total_requested": len(request.run_ids),
            "successful": len(results),
            "failed": len(errors),
            "results": results,
            "errors": errors,
            "timestamp": DateTimeUtils.utc_now().isoformat()
        }

        logger.info(f"Bulk reprocess operation: {len(results)} successful, {len(errors)} failed")
        return response

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Unexpected error in bulk reprocess: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error"
        )


@router.post("/reprocess-failed", response_model=Dict[str, Any])
def reprocess_all_failed_runs(
    container: ServiceContainer = Depends(get_service_container)
):
    """
    Reprocess all failed and needs_template runs

    Automatically finds all runs with 'failure' or 'needs_template' status
    and resets them to 'not_started' for reprocessing.
    """
    try:
        eto_service = container.get_eto_service()

        # Get all failed and needs_template runs
        failed_runs = eto_service.get_runs(
            status="failure",
            limit=1000
        )
        needs_template_runs = eto_service.get_runs(
            status="needs_template",
            limit=1000
        )

        all_runs = failed_runs + needs_template_runs
        total_found = len(all_runs)

        if total_found == 0:
            return {
                "operation": "reprocess_all_failed",
                "total_found": 0,
                "total_reprocessed": 0,
                "failed_count": 0,
                "needs_template_count": 0,
                "message": "No failed or needs_template runs found",
                "timestamp": DateTimeUtils.utc_now().isoformat()
            }

        # Reprocess each run
        results = []
        errors = []

        for run in all_runs:
            try:
                reset_run = eto_service.reprocess_run(run.id)
                results.append({
                    "run_id": run.id,
                    "original_status": run.status.value,
                    "new_status": reset_run.status.value
                })
            except Exception as e:
                logger.error(f"Error reprocessing run {run.id}: {e}")
                errors.append({
                    "run_id": run.id,
                    "original_status": run.status.value,
                    "error": str(e)
                })

        return {
            "operation": "reprocess_all_failed",
            "total_found": total_found,
            "total_reprocessed": len(results),
            "failed_count": len([r for r in failed_runs]),
            "needs_template_count": len([r for r in needs_template_runs]),
            "successful_reprocessed": results,
            "errors": errors,
            "message": f"Reprocessed {len(results)} runs, {len(errors)} failed",
            "timestamp": DateTimeUtils.utc_now().isoformat()
        }

    except Exception as e:
        logger.error(f"Error in reprocess all failed runs: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to reprocess runs: {str(e)}"
        )