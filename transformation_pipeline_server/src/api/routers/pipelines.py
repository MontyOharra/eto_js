"""
Pipeline Router - API endpoints for pipeline management
Provides endpoints for pipeline upload, retrieval, and listing
"""

import logging
from typing import Dict, Any
from fastapi import APIRouter, HTTPException, Depends

from shared.services.service_container import ServiceContainer
from features.pipeline import PipelineService
from features.pipeline_execution.service import PipelineExecutionService
from shared.types import (
    PipelineDefinition,
    PipelineDefinitionCreate,
    PipelineDefinitionSummary,
    PipelineState,
    PipelineValidationResult,
    PipelineExecutionRun,
)
from shared.exceptions import RepositoryError, ObjectNotFoundError

from api.schemas import (
    PipelineListResponse,
    PipelineSummaryListResponse,
    ValidatePipelineRequest,
    TestUploadResponse,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/pipelines", tags=["Pipelines"])


@router.post("/upload", response_model=PipelineDefinition)
async def upload_pipeline(
    pipeline_create: PipelineDefinitionCreate,
    pipeline_service: PipelineService = Depends(
        lambda: ServiceContainer.get_pipeline_service()
    ),
):
    """
    TEST ENDPOINT: Create and compile pipeline with full compilation flow

    This endpoint implements the complete compilation pipeline:
    1. Validate pipeline structure
    2. Prune dead branches
    3. Calculate ID-agnostic checksum
    4. Check if compiled steps exist (cache)
    5a. If cache hit: Create pipeline record referencing existing steps
    5b. If cache miss: Compile steps, create pipeline, save steps
    6. Return created Pipeline object

    This will eventually replace the main /pipelines endpoint.

    Args:
        pipeline_create: Pipeline creation data

    Returns:
        Created Pipeline object with plan_checksum and compiled_at populated

    Raises:
        400: Validation failed
        500: Internal server error
    """
    logger.info(f"[TEST_UPLOAD_API] Create pipeline requested: {pipeline_create.name}")

    try:
        # Call the full create pipeline method with compilation
        pipeline = pipeline_service.create_pipeline(pipeline_create)

        logger.info(
            f"[TEST_UPLOAD_API] ✅ Pipeline created: {pipeline.id} - {pipeline.name}"
        )
        logger.info(
            f"[TEST_UPLOAD_API]    Checksum: {pipeline.plan_checksum[:12] if pipeline.plan_checksum else 'none'}..."
        )
        logger.info(f"[TEST_UPLOAD_API]    Compiled: {pipeline.compiled_at}")

        return pipeline

    except ValueError as e:
        logger.error(f"[TEST_UPLOAD_API] Invalid pipeline data: {e}")
        raise HTTPException(status_code=400, detail=f"Invalid pipeline data: {str(e)}")
    except Exception as e:
        logger.error(
            f"[TEST_UPLOAD_API] Unexpected error creating pipeline: {e}", exc_info=True
        )
        raise HTTPException(
            status_code=500, detail=f"Failed to create pipeline: {str(e)}"
        )


@router.get("/")
async def list_pipelines(
    include_inactive: bool = False,
    summary_only: bool = False,
    pipeline_service: PipelineService = Depends(
        lambda: ServiceContainer.get_pipeline_service()
    ),
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
    logger.info(
        f"Pipeline list requested (include_inactive={include_inactive}, summary_only={summary_only})"
    )

    try:

        if summary_only:
            summaries = pipeline_service.list_pipeline_summaries(
                include_inactive=include_inactive
            )

            response = PipelineSummaryListResponse(
                pipelines=summaries, total_count=len(summaries)
            )

            logger.info(f"Retrieved {len(summaries)} pipeline summaries")
            return response
        else:
            pipelines = pipeline_service.list_pipelines(
                include_inactive=include_inactive
            )

            response = PipelineListResponse(
                pipelines=pipelines, total_count=len(pipelines)
            )

            logger.info(f"Retrieved {len(pipelines)} pipelines")
            return response

    except RepositoryError as e:
        logger.error(f"Failed to list pipelines: {e}")
        raise HTTPException(status_code=500, detail=str(e))
    except Exception as e:
        logger.error(f"Unexpected error listing pipelines: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve pipelines")


@router.get("/{pipeline_id}", response_model=PipelineDefinition)
async def get_pipeline(
    pipeline_id: int,
    pipeline_service: PipelineService = Depends(
        lambda: ServiceContainer.get_pipeline_service()
    ),
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


@router.post("/validate", response_model=PipelineValidationResult)
async def validate_pipeline(
    request: ValidatePipelineRequest,
    pipeline_service: PipelineService = Depends(
        lambda: ServiceContainer.get_pipeline_service()
    ),
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
            logger.info(
                f"Pipeline validation failed with {len(result.errors)} error(s)"
            )

        return result

    except ValueError as e:
        # Pydantic validation errors for malformed data
        logger.warning(f"Invalid pipeline data: {e}")
        raise HTTPException(status_code=400, detail=f"Invalid pipeline data: {str(e)}")
    except Exception as e:
        logger.error(f"Unexpected error validating pipeline: {e}")
        raise HTTPException(status_code=500, detail="Failed to validate pipeline")


@router.post("/{pipeline_id}/execute", response_model=PipelineExecutionRun)
async def execute_pipeline(
    pipeline_id: int,
    entry_values: Dict[str, Any],
    execution_service: PipelineExecutionService = Depends(
        lambda: ServiceContainer.get_pipeline_execution_service()
    ),
):
    """
    Execute a pipeline with given entry values.

    Args:
        pipeline_id: ID of the pipeline to execute (integer)
        entry_values: Dictionary with entry point NAMES as keys and their values.
            Example: {"Input": "Hello World", "Config": {"setting": "value"}}
        execution_service: Injected pipeline execution service

    Returns:
        PipelineExecutionRun with execution status and entry values

    Raises:
        404: If pipeline not found
        400: If entry values are invalid or entry point names not found
        500: If execution fails
    """
    try:
        logger.info(f"Pipeline execution requested: {pipeline_id}")
        logger.debug(f"Entry values: {entry_values}")

        # Execute the pipeline using the new execution service
        run = execution_service.execute_pipeline(
            pipeline_definition_id=pipeline_id,
            entry_values_by_name=entry_values
        )

        logger.info(f"Pipeline {pipeline_id} executed successfully: run_id={run.id}, status={run.status}")
        return run

    except ObjectNotFoundError as e:
        logger.warning(f"Pipeline not found for execution: {pipeline_id}")
        raise HTTPException(status_code=404, detail=str(e))
    except ValueError as e:
        logger.warning(f"Invalid entry values for pipeline {pipeline_id}: {e}")
        raise HTTPException(status_code=400, detail=f"Invalid entry values: {str(e)}")
    except RuntimeError as e:
        # Handles "Pipeline not compiled" errors
        logger.error(f"Pipeline execution error: {e}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Unexpected error executing pipeline {pipeline_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Pipeline execution failed")
