"""
Pipeline Router - API endpoints for pipeline management
Provides endpoints for pipeline upload, retrieval, and listing
"""
import logging
from typing import List
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel

from src.features.pipeline import PipelineService
from src.shared.database import get_connection_manager
from src.shared.models.pipeline import Pipeline, PipelineCreate, PipelineSummary, PipelineState
from src.shared.exceptions import RepositoryError, ObjectNotFoundError
from src.features.pipeline.validation.errors import ValidationResult

logger = logging.getLogger(__name__)

router = APIRouter()


class PipelineListResponse(BaseModel):
    """Response model for pipeline listing"""
    pipelines: List[Pipeline]
    total_count: int


class PipelineSummaryListResponse(BaseModel):
    """Response model for pipeline summary listing"""
    pipelines: List[PipelineSummary]
    total_count: int


class ValidatePipelineRequest(BaseModel):
    """Request model for pipeline validation"""
    pipeline_json: PipelineState


def get_pipeline_service() -> PipelineService:
    """Dependency injection for pipeline service"""
    connection_manager = get_connection_manager()
    if not connection_manager:
        raise HTTPException(
            status_code=500,
            detail="Database connection not available"
        )
    return PipelineService(connection_manager)


@router.post("/pipelines", response_model=Pipeline)
async def upload_pipeline(
    pipeline_create: PipelineCreate,
    pipeline_service: PipelineService = Depends(get_pipeline_service)
):
    """
    Upload/create a new pipeline

    Creates a new pipeline with the provided configuration.
    Pipelines are immutable once created.

    Args:
        pipeline_create: Pipeline creation data

    Returns:
        Created Pipeline object

    Raises:
        400: Invalid pipeline data
        500: Internal server error
    """
    logger.info(f"Pipeline upload requested: {pipeline_create.name}")

    try:
        pipeline = pipeline_service.upload_pipeline(pipeline_create)

        logger.info(f"Pipeline uploaded successfully: {pipeline.id} - {pipeline.name}")
        return pipeline

    except RepositoryError as e:
        logger.error(f"Failed to upload pipeline: {e}")
        raise HTTPException(status_code=500, detail=str(e))
    except Exception as e:
        logger.error(f"Unexpected error uploading pipeline: {e}")
        raise HTTPException(status_code=500, detail="Failed to upload pipeline")


@router.get("/pipelines")
async def list_pipelines(
    include_inactive: bool = False,
    summary_only: bool = False,
    pipeline_service: PipelineService = Depends(get_pipeline_service)
):
    """
    Get all pipelines

    Retrieves all pipelines with optional filtering.

    Args:
        include_inactive: Include inactive pipelines in results
        summary_only: Return lightweight summaries instead of full pipelines

    Returns:
        List of Pipeline or PipelineSummary objects

    Raises:
        500: Internal server error
    """
    logger.info(f"Pipeline list requested (include_inactive={include_inactive}, summary_only={summary_only})")

    try:
        if summary_only:
            summaries = pipeline_service.list_pipeline_summaries(include_inactive=include_inactive)

            response = PipelineSummaryListResponse(
                pipelines=summaries,
                total_count=len(summaries)
            )

            logger.info(f"Retrieved {len(summaries)} pipeline summaries")
            return response
        else:
            pipelines = pipeline_service.list_pipelines(include_inactive=include_inactive)

            response = PipelineListResponse(
                pipelines=pipelines,
                total_count=len(pipelines)
            )

            logger.info(f"Retrieved {len(pipelines)} pipelines")
            return response

    except RepositoryError as e:
        logger.error(f"Failed to list pipelines: {e}")
        raise HTTPException(status_code=500, detail=str(e))
    except Exception as e:
        logger.error(f"Unexpected error listing pipelines: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve pipelines")


@router.get("/pipelines/{pipeline_id}", response_model=Pipeline)
async def get_pipeline(
    pipeline_id: str,
    pipeline_service: PipelineService = Depends(get_pipeline_service)
):
    """
    Get a specific pipeline by ID

    Retrieves a single pipeline by its unique identifier.

    Args:
        pipeline_id: Pipeline ID to retrieve

    Returns:
        Pipeline object

    Raises:
        404: Pipeline not found
        500: Internal server error
    """
    logger.info(f"Pipeline retrieval requested: {pipeline_id}")

    try:
        pipeline = pipeline_service.get_pipeline(pipeline_id)

        logger.info(f"Retrieved pipeline: {pipeline.id} - {pipeline.name}")
        return pipeline

    except ObjectNotFoundError as e:
        logger.warning(f"Pipeline not found: {pipeline_id}")
        raise HTTPException(status_code=404, detail=str(e))
    except RepositoryError as e:
        logger.error(f"Failed to get pipeline {pipeline_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))
    except Exception as e:
        logger.error(f"Unexpected error getting pipeline {pipeline_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve pipeline")


@router.post("/pipelines/validate", response_model=ValidationResult)
async def validate_pipeline(
    request: ValidatePipelineRequest,
    pipeline_service: PipelineService = Depends(get_pipeline_service)
):
    """
    Validate a pipeline state

    Validates pipeline structure, connections, types, and reachability
    without saving to database.

    Args:
        request: Pipeline validation request with pipeline_json

    Returns:
        ValidationResult with valid flag and any errors

    Raises:
        400: Invalid request body or malformed pipeline JSON
        500: Internal server error
    """
    logger.info("Pipeline validation requested")

    try:
        # Validate the pipeline state
        result = pipeline_service.validate_pipeline(request.pipeline_json)

        if result.valid:
            logger.info("Pipeline validation passed")
        else:
            logger.info(f"Pipeline validation failed with {len(result.errors)} error(s)")

        return result

    except ValueError as e:
        # Pydantic validation errors for malformed data
        logger.warning(f"Invalid pipeline data: {e}")
        raise HTTPException(status_code=400, detail=f"Invalid pipeline data: {str(e)}")
    except Exception as e:
        logger.error(f"Unexpected error validating pipeline: {e}")
        raise HTTPException(status_code=500, detail="Failed to validate pipeline")