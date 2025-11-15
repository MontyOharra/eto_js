"""
Pipeline API Router
Endpoints for pipeline definition management (dev/testing)
"""
import logging
from typing import List, Literal
from fastapi import APIRouter, Depends, status

from api.schemas.pipelines import (
    PipelineSummary,
    PipelinesListResponse,
    PipelineDetail,
    CreatePipelineRequest,
    CreatePipelineResponse,
    ValidatePipelineRequest,
    ValidatePipelineResponse,
    ValidationError,
    ExecutePipelineRequest,
    ExecutePipelineResponse,
    ExecutionStepResult,
)

from api.mappers.pipelines import (
    convert_pipeline_summary_list,
    convert_pipeline_detail,
    convert_create_request,
    convert_pipeline_state_to_domain,
    convert_execution_result,
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


@router.get("/{id}", response_model=PipelineDetail)
async def get_pipeline(
    id: int,
    pipeline_service: PipelineService = Depends(
        lambda: ServiceContainer.get_pipeline_service()
    )
) -> PipelineDetail:
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
    # DEBUG: Log what API receives from frontend
    logger.debug("[API DEBUG] Received pipeline from frontend:")
    for module in request.pipeline_state.modules:
        logger.debug(f"[API DEBUG]   Module {module.module_instance_id} ({module.module_ref}):")
        for inp in module.inputs:
            logger.debug(f"[API DEBUG]     Input: node_id={inp.node_id}, name={inp.name}, group_index={inp.group_index}")

    # Convert API request to domain type
    pipeline_create = convert_create_request(request)

    # DEBUG: Log after conversion to domain type
    logger.debug("[API DEBUG] After conversion to domain:")
    for module in pipeline_create.pipeline_state.modules:
        logger.debug(f"[API DEBUG]   Module {module.module_instance_id} ({module.module_ref}):")
        for inp in module.inputs:
            logger.debug(f"[API DEBUG]     Input: node_id={inp.node_id}, name={inp.name}, group_index={inp.group_index}")

    # Create pipeline (service handles validation, compilation, persistence)
    pipeline = pipeline_service.create_pipeline_definition(pipeline_create)

    return CreatePipelineResponse(
        id=pipeline.id,
        compiled_plan_id=pipeline.compiled_plan_id
    )


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
    # Convert API request to domain type
    pipeline_state = convert_pipeline_state_to_domain(request.pipeline_json)

    # Call service - ALL validation happens in PipelineValidator
    validation_result = pipeline_service.validate_pipeline(pipeline_state)

    # Convert service result to API response
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


@router.post("/{id}/execute", response_model=ExecutePipelineResponse)
async def execute_pipeline(
    id: int,
    request: ExecutePipelineRequest,
    pipeline_service: PipelineService = Depends(
        lambda: ServiceContainer.get_pipeline_service()
    )
) -> ExecutePipelineResponse:
    """
    Execute a pipeline with provided entry values (SIMULATION MODE).

    This executes the pipeline without database persistence - used for testing
    and development. Actions are NOT actually executed - only their input data
    is collected to show what would happen.

    **Entry Values**:
    - Must provide values for all entry points defined in the pipeline
    - Values should be keyed by entry point name
    - Missing required entry points will cause validation error

    **Returns**:
    - Execution status (success/failed)
    - Step-by-step execution trace with inputs/outputs
    - Action data (what would be executed in production)
    - Error message if execution failed

    **Example Request**:
    ```json
    {
      "entry_values": {
        "customer_name": "ACME Corp",
        "order_id": "12345"
      }
    }
    ```
    """
    # Get execution service
    from features.pipeline_execution.service import PipelineExecutionService
    execution_service = PipelineExecutionService(
        connection_manager=ServiceContainer.get_connection_manager(),
        services=ServiceContainer
    )

    # Load pipeline definition
    pipeline = pipeline_service.get_pipeline_definition(id)

    if pipeline.compiled_plan_id is None:
        from shared.exceptions import ServiceError
        raise ServiceError(
            f"Pipeline {id} is not compiled. Cannot execute uncompiled pipeline."
        )

    # Load compiled steps
    from shared.database.repositories import PipelineDefinitionStepRepository
    step_repo = PipelineDefinitionStepRepository(
        connection_manager=ServiceContainer.get_connection_manager()
    )
    steps = step_repo.get_steps_by_plan_id(pipeline.compiled_plan_id)

    if not steps:
        from shared.exceptions import ServiceError
        raise ServiceError(
            f"No compiled steps found for pipeline {id} (plan {pipeline.compiled_plan_id})"
        )

    logger.info(f"Simulating pipeline {id} with {len(steps)} steps")

    # Simulate pipeline (testing endpoint - no action execution)
    result = execution_service.simulate_pipeline(
        steps=steps,
        entry_values_by_name=request.entry_values,
        pipeline_state=pipeline.pipeline_state
    )

    # Convert result to API schema
    step_dtos = [
        ExecutionStepResult(
            module_instance_id=step.module_instance_id,
            step_number=step.step_number,
            inputs=step.inputs,
            outputs=step.outputs,
            error=step.error
        )
        for step in result.steps
    ]

    return ExecutePipelineResponse(
        status=result.status,
        steps=step_dtos,
        executed_actions=result.executed_actions,
        error=result.error
    )
