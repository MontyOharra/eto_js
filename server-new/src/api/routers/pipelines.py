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
    ValidatePipelineRequest,
    ValidatePipelineResponse,
    ValidationErrorDTO,
    ExecutePipelineRequest,
    ExecutePipelineResponse,
    ExecutionStepResultDTO,
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
    from api.mappers.pipelines import convert_dto_to_pipeline_state
    pipeline_state = convert_dto_to_pipeline_state(request.pipeline_json)

    # Validate pipeline structure
    validation_result = pipeline_service.validate_pipeline(pipeline_state)

    # Convert error to DTO list (single error or empty)
    error_dtos = []
    if not validation_result["valid"] and "error" in validation_result:
        error_dtos = [
            ValidationErrorDTO(
                code=validation_result["error"]["code"],
                message=validation_result["error"]["message"],
                where=validation_result["error"].get("where")
            )
        ]

    # Validate module configurations (even if structure validation failed)
    from shared.utils.registry import get_registry
    from pydantic import ValidationError

    module_registry = get_registry()

    for module_instance in pipeline_state.modules:
        # Extract module_id from module_ref (format: "module_id:version")
        module_id = module_instance.module_ref.split(":")[0] if ":" in module_instance.module_ref else module_instance.module_ref

        # Get module handler from registry
        handler = module_registry.get(module_id)
        if not handler:
            error_dtos.append(
                ValidationErrorDTO(
                    code="module_not_found",
                    message=f"Module '{module_id}' not found in registry",
                    where={"module_instance_id": module_instance.module_instance_id}
                )
            )
            continue

        # Validate config against module's Pydantic schema
        try:
            ConfigModel = handler.config_class()
            # This will raise ValidationError if config is invalid
            ConfigModel(**module_instance.config)
        except ValidationError as e:
            # Pydantic validation failed - extract errors
            for error in e.errors():
                field_path = " -> ".join(str(loc) for loc in error["loc"])
                error_dtos.append(
                    ValidationErrorDTO(
                        code="invalid_config",
                        message=f"Module {module_instance.module_instance_id}: {field_path}: {error['msg']}",
                        where={
                            "module_instance_id": module_instance.module_instance_id,
                            "field": field_path,
                            "type": error["type"]
                        }
                    )
                )
        except Exception as e:
            # Unexpected error during config validation
            error_dtos.append(
                ValidationErrorDTO(
                    code="config_validation_error",
                    message=f"Module {module_instance.module_instance_id}: {str(e)}",
                    where={"module_instance_id": module_instance.module_instance_id}
                )
            )

    # Overall validation is only valid if no errors were found
    is_valid = len(error_dtos) == 0

    return ValidatePipelineResponse(
        valid=is_valid,
        errors=error_dtos
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
    from features.pipelines.service_execution import PipelineExecutionService
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

    logger.info(f"Executing pipeline {id} with {len(steps)} steps")

    # Execute pipeline
    result = execution_service.execute_pipeline(
        steps=steps,
        entry_values_by_name=request.entry_values,
        pipeline_state=pipeline.pipeline_state
    )

    # Convert result to API schema
    step_dtos = [
        ExecutionStepResultDTO(
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
