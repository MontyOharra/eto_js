"""
Pipeline API Router
Endpoints for pipeline definition management (dev/testing)
"""
import logging
from typing import List, Literal
from fastapi import APIRouter, Depends, status

from api.schemas.pipelines import (
    PipelineSummaryDTO,
    PipelinesListResponse,
    PipelineDetailDTO,
    CreatePipelineRequest,
    CreatePipelineResponse,
)

from api.mappers.pipelines import (
    convert_pipeline_summary_list,
    convert_pipeline_detail,
    convert_create_request,
)

from shared.services.service_container import ServiceContainer
from features.pipelines.service import PipelineService

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/pipelines",
    tags=["Pipelines (Dev/Testing)"]
)


@router.get("", response_model=PipelinesListResponse)
async def list_pipelines(
    sort_by: Literal["id", "created_at"] = "created_at",
    sort_order: Literal["asc", "desc"] = "desc",
    limit: int = 50,
    offset: int = 0,
    pipeline_service: PipelineService = Depends(
        lambda: ServiceContainer.get_pipeline_service()
    )
) -> PipelinesListResponse:
    """
    List all pipeline definitions with pagination and sorting.

    **Dev/Testing only** - This endpoint is for standalone pipeline testing.
    Will be removed when standalone pipeline page is removed from production.
    """
    # Validate limit
    if limit > 200:
        limit = 200

    # Get all pipelines (service layer handles sorting)
    all_pipelines = pipeline_service.list_pipeline_definitions(
        sort_by=sort_by,
        sort_order=sort_order
    )

    # Apply pagination
    start = offset
    end = start + limit
    items = all_pipelines[start:end]

    # Convert to API schema
    pipeline_dtos = convert_pipeline_summary_list(items)

    return PipelinesListResponse(
        items=pipeline_dtos,
        total=len(all_pipelines),
        limit=limit,
        offset=offset
    )


@router.get("/{id}", response_model=PipelineDetailDTO)
async def get_pipeline(
    id: int,
    pipeline_service: PipelineService = Depends(
        lambda: ServiceContainer.get_pipeline_service()
    )
) -> PipelineDetailDTO:
    """
    Get complete pipeline definition including pipeline_state and visual_state.

    Returns full pipeline data for visualization/editing.
    """
    pipeline = pipeline_service.get_pipeline_definition(id)

    return convert_pipeline_detail(pipeline)


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
    # Convert API request to domain type
    pipeline_create = convert_create_request(request)

    # Create pipeline (service handles validation, compilation, persistence)
    pipeline = pipeline_service.create_pipeline_definition(pipeline_create)

    return CreatePipelineResponse(
        id=pipeline.id,
        compiled_plan_id=pipeline.compiled_plan_id
    )
