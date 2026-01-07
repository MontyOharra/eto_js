"""
Pipelines API Schemas

Pydantic models for pipeline API requests and responses.
Reuses domain types from shared/types where possible.
"""
from typing import Any

from pydantic import BaseModel, Field

from shared.types.pipelines import (
    PipelineState,
    VisualState,
)
from shared.types.pipeline_definition import (
    PipelineDefinition,
    PipelineDefinitionSummary,
    PipelineDefinitionCreate,
)
from shared.types.pipeline_execution import (
    PipelineExecutionStepResult,
    PipelineExecutionResult,
)


# ============================================================================
# List Response
# ============================================================================

class PipelineListResponse(BaseModel):
    """Response for GET /pipelines"""
    items: list[PipelineDefinitionSummary]
    total: int
    limit: int
    offset: int


# ============================================================================
# Create/Update
# ============================================================================

# Reuse domain type for create request
CreatePipelineRequest = PipelineDefinitionCreate


class CreatePipelineResponse(BaseModel):
    """Response for POST /pipelines"""
    id: int


# ============================================================================
# Detail Response
# ============================================================================

# Reuse domain type directly for detail response
PipelineDetailResponse = PipelineDefinition


# ============================================================================
# Validation
# ============================================================================

class ValidationError(BaseModel):
    """Single validation error"""
    code: str  # Error code (e.g., "type_mismatch", "cycle_detected")
    message: str  # Human-readable error message
    where: dict[str, Any] | None = None  # Additional context


class ValidatePipelineRequest(BaseModel):
    """Request body for POST /pipelines/validate"""
    pipeline_json: PipelineState = Field(..., alias="pipeline_json")


class ValidatePipelineResponse(BaseModel):
    """Response for POST /pipelines/validate"""
    valid: bool
    error: ValidationError | None = None


# ============================================================================
# Execution
# ============================================================================

class ExecutePipelineRequest(BaseModel):
    """Request body for POST /pipelines/{id}/execute"""
    entry_values: dict[str, Any] = Field(
        ...,
        description="Entry point values keyed by entry point name",
    )


# Reuse domain type for execution step result
ExecutionStepResultResponse = PipelineExecutionStepResult


class ExecutePipelineResponse(BaseModel):
    """Response for POST /pipelines/{id}/execute"""
    status: str  # "success" | "failed" | "partial"
    steps: list[PipelineExecutionStepResult]
    output_channel_values: dict[str, Any] = Field(
        default_factory=dict,
        description="Collected output channel values {channel_type: value}"
    )
    error: str | None = None
