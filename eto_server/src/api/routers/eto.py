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
    prefix="/eto",
    tags=["ETO Processing"]
)


@router.get("/dashboard", response_model=Dict[str, Any])
def get_dashboard(
    container: ServiceContainer = Depends(get_service_container)
):
    """
    Get ETO dashboard data with runs segmented by status

    Returns runs grouped by status with summary data including email information
    when the PDF file is associated with an email.
    """
    try:
        eto_service = container.get_eto_processing_service()

        # Get all runs grouped by status
        runs_by_status = eto_service.get_all_runs_grouped_by_status()

        # Get processing statistics
        stats = eto_service.get_processing_statistics()

        # Format response
        dashboard_data = {
            "runs_by_status": runs_by_status,
            "statistics": stats,
            "last_updated": DateTimeUtils.utc_now().isoformat()
        }

        logger.debug(f"Retrieved ETO dashboard data with {sum(len(runs) for runs in runs_by_status.values())} total runs")
        return dashboard_data

    except ServiceError as e:
        logger.error(f"Failed to get ETO dashboard data: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Unexpected error getting ETO dashboard: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error"
        )


@router.get("/runs/{run_id}", response_model=EtoRun)
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
        eto_service = container.get_eto_processing_service()

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


@router.patch("/runs/{run_id}/skip", response_model=EtoRun)
def skip_run(
    run_id: int,
    container: ServiceContainer = Depends(get_service_container)
):
    """
    Mark a needs_template or failed run as skipped

    Only runs with status 'failure' or 'needs_template' can be skipped.
    """
    try:
        eto_service = container.get_eto_processing_service()

        updated_run = eto_service.mark_run_as_skipped(run_id)

        logger.info(f"Marked ETO run {run_id} as skipped")
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


@router.delete("/runs/{run_id}", response_model=EtoRun)
def delete_run(
    run_id: int,
    container: ServiceContainer = Depends(get_service_container)
):
    """
    Permanently delete a skipped ETO run from the database

    Only runs with status 'skipped' can be permanently deleted.
    """
    try:
        eto_service = container.get_eto_processing_service()

        deleted_run = eto_service.delete_skipped_run(run_id)

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


@router.patch("/runs/{run_id}/reprocess", response_model=EtoRun)
def reprocess_run(
    run_id: int,
    container: ServiceContainer = Depends(get_service_container)
):
    """
    Reset a skipped run back to not_started status for reprocessing

    Only runs with status 'skipped' can be reset for reprocessing.
    """
    try:
        eto_service = container.get_eto_processing_service()

        reset_run = eto_service.reset_run_for_reprocessing(run_id)

        logger.info(f"Reset ETO run {run_id} for reprocessing")
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
        logger.error(f"Failed to reset ETO run {run_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Unexpected error resetting ETO run {run_id}: {e}")
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
    including processing capacity, recent activity, and service status.
    """
    try:
        eto_service = container.get_eto_processing_service()

        # Check if service is healthy
        is_healthy = eto_service.is_healthy()

        # Get recent processing statistics
        stats = eto_service.get_processing_statistics()

        health_data = {
            "status": "healthy" if is_healthy else "unhealthy",
            "service_name": "ETO Processing Service",
            "timestamp": DateTimeUtils.utc_now().isoformat(),
            "statistics": stats,
            "details": {
                "processing_enabled": is_healthy,
                "database_connected": True,  # If we got stats, DB is connected
                "template_service_available": True  # Implied if service is working
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


# ========== Bulk Operations ==========

@router.patch("/runs/bulk/skip", response_model=Dict[str, Any])
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

        eto_service = container.get_eto_processing_service()

        results = []
        errors = []

        for run_id in request.run_ids:
            try:
                updated_run = eto_service.mark_run_as_skipped(run_id)
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


@router.patch("/runs/bulk/reprocess", response_model=Dict[str, Any])
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

        eto_service = container.get_eto_processing_service()

        results = []
        errors = []

        for run_id in request.run_ids:
            try:
                reset_run = eto_service.reset_run_for_reprocessing(run_id)
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