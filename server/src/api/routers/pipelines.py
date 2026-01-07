"""
Pipeline API Router
Endpoints for pipeline definition management (dev/testing)
"""
import logging
from typing import Literal

from fastapi import APIRouter, Depends, status

from api.schemas.pipelines import (
    PipelineListResponse,
    PipelineDetailResponse,
    CreatePipelineRequest,
    CreatePipelineResponse,
    ValidatePipelineRequest,
    ValidatePipelineResponse,
    ValidationError,
    ExecutePipelineRequest,
    ExecutePipelineResponse,
)

from shared.services.service_container import ServiceContainer
from features.pipelines.service import PipelineService

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/pipelines",
    tags=["Pipelines (Dev/Testing)"]
)


@router.get("", response_model=PipelineListResponse)
async def list_pipelines(
    sort_by: Literal["id", "created_at"] = "created_at",
    sort_order: Literal["asc", "desc"] = "desc",
    limit: int = 50,
    offset: int = 0,
    pipeline_service: PipelineService = Depends(
        lambda: ServiceContainer.get_pipeline_service()
    )
) -> PipelineListResponse:
    """
    List all pipeline definitions with pagination and sorting.

    **Dev/Testing only** - This endpoint is for standalone pipeline testing.
    Will be removed when standalone pipeline page is removed from production.
    """
    if limit > 200:
        limit = 200

    all_pipelines = pipeline_service.list_pipeline_definitions(
        sort_by=sort_by,
        sort_order=sort_order
    )

    # Apply pagination
    start = offset
    end = start + limit
    items = all_pipelines[start:end]

    return PipelineListResponse(
        items=items,
        total=len(all_pipelines),
        limit=limit,
        offset=offset
    )


@router.get("/{id}", response_model=PipelineDetailResponse)
async def get_pipeline(
    id: int,
    pipeline_service: PipelineService = Depends(
        lambda: ServiceContainer.get_pipeline_service()
    )
) -> PipelineDetailResponse:
    """
    Get complete pipeline definition including pipeline_state and visual_state.

    Returns full pipeline data for visualization/editing.
    """
    return pipeline_service.get_pipeline_definition(id)


@router.post("", response_model=CreatePipelineResponse, status_code=status.HTTP_201_CREATED)
async def create_pipeline(
    request: CreatePipelineRequest,
    pipeline_service: PipelineService = Depends(
        lambda: ServiceContainer.get_pipeline_service()
    )
) -> CreatePipelineResponse:
    """
    Create new standalone pipeline for testing.

    **Dev/Testing only** - Creates pipeline without template association.
    Will be removed once pipeline system testing is complete.

    Pipeline compilation happens during creation (validation and optimization).
    """
    # DEBUG: Log what API receives from frontend
    logger.debug("[API DEBUG] Received pipeline from frontend:")
    for module in request.pipeline_state.modules:
        logger.debug(f"[API DEBUG]   Module {module.module_instance_id} ({module.module_id}):")
        for inp in module.inputs:
            logger.debug(f"[API DEBUG]     Input: node_id={inp.node_id}, name={inp.name}, group_index={inp.group_index}")

    # Create pipeline (service handles validation, compilation, persistence)
    # Request is already the domain type (PipelineDefinitionCreate)
    pipeline = pipeline_service.create_pipeline_definition(request)

    return CreatePipelineResponse(id=pipeline.id)


@router.post("/validate", response_model=ValidatePipelineResponse)
async def validate_pipeline(
    request: ValidatePipelineRequest,
    pipeline_service: PipelineService = Depends(
        lambda: ServiceContainer.get_pipeline_service()
    )
) -> ValidatePipelineResponse:
    """
    Validate pipeline structure and module configurations without saving.

    Checks:
    - All module references exist in module catalog
    - All connections reference valid pins
    - Connection type compatibility
    - No duplicate connections
    - No cycles (DAG requirement)
    - All module inputs are connected
    - Module configurations are valid (required fields, correct types, etc.)

    Returns validation results with detailed error messages if validation fails.
    """
    # Request pipeline_json is already the domain PipelineState type
    validation_result = pipeline_service.validate_pipeline(request.pipeline_json)

    if validation_result["valid"]:
        return ValidatePipelineResponse(valid=True, error=None)
    else:
        return ValidatePipelineResponse(
            valid=False,
            error=ValidationError(
                code=validation_result["error"]["code"],
                message=validation_result["error"]["message"],
                where=validation_result["error"].get("where")
            )
        )