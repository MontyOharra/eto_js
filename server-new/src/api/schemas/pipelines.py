"""
Pipelines API Schemas
Pydantic models for pipeline definition endpoints
"""
from typing import List, Dict, Any, Optional, Literal
from pydantic import BaseModel, Field

# ============================================================================
# Pipeline State Types (logical structure)
# ============================================================================

class NodeDTO(BaseModel):
    """Node (pin) in a module instance"""
    node_id: str
    type: str  # "str", "int", "float", "bool", "datetime", etc.
    name: str
    position_index: int
    group_index: int


class EntryPointDTO(BaseModel):
    """Entry point for pipeline input"""
    node_id: str
    name: str


class ModuleInstanceDTO(BaseModel):
    """Module instance placed on the canvas"""
    module_instance_id: str
    module_ref: str  # e.g., "text_cleaner:1.0.0"
    config: Dict[str, Any]  # Module-specific configuration
    inputs: List[NodeDTO] = []
    outputs: List[NodeDTO] = []


class NodeConnectionDTO(BaseModel):
    """Connection between two nodes"""
    from_node_id: str
    to_node_id: str


class PipelineStateDTO(BaseModel):
    """Pipeline execution structure"""
    entry_points: List[EntryPointDTO] = []
    modules: List[ModuleInstanceDTO] = []
    connections: List[NodeConnectionDTO] = []


# ============================================================================
# Visual State Types (UI layout)
# ============================================================================

class PositionDTO(BaseModel):
    """2D position for visual layout"""
    x: float
    y: float


class VisualStateDTO(BaseModel):
    """Visual positioning data for the UI"""
    modules: Dict[str, PositionDTO] = {}  # module_instance_id -> position
    entry_points: Dict[str, PositionDTO] = {}  # entry_point node_id -> position


# ============================================================================
# Pipeline Definition Types
# ============================================================================

class PipelineSummaryDTO(BaseModel):
    """Lightweight pipeline summary for list views (GET /pipelines)"""
    id: int
    compiled_plan_id: Optional[int] = None  # null if not yet compiled
    created_at: str  # ISO 8601 (dev/testing convenience)
    updated_at: str  # ISO 8601 (dev/testing convenience)


class PipelinesListResponse(BaseModel):
    """Response for GET /pipelines"""
    items: List[PipelineSummaryDTO]
    total: int
    limit: int
    offset: int


class PipelineDetailDTO(BaseModel):
    """Full pipeline definition details (GET /pipelines/{id})"""
    id: int
    compiled_plan_id: Optional[int] = None
    pipeline_state: PipelineStateDTO
    visual_state: VisualStateDTO


# ============================================================================
# Create/Update Requests
# ============================================================================

class CreatePipelineRequest(BaseModel):
    """Request body for POST /pipelines"""
    pipeline_state: PipelineStateDTO
    visual_state: VisualStateDTO


class CreatePipelineResponse(BaseModel):
    """Response for POST /pipelines"""
    id: int  # Created pipeline ID
    compiled_plan_id: Optional[int] = None  # null initially, set on first compilation


class UpdatePipelineRequest(BaseModel):
    """Request body for PUT /pipelines/{id}"""
    pipeline_state: PipelineStateDTO
    visual_state: VisualStateDTO


class UpdatePipelineResponse(BaseModel):
    """Response for PUT /pipelines/{id}"""
    id: int
    compiled_plan_id: Optional[int] = None  # May change if pipeline logic changed


# ============================================================================
# Validation
# ============================================================================

class ValidationErrorDTO(BaseModel):
    """Single validation error"""
    code: str  # Error code (e.g., "type_mismatch", "cycle_detected")
    message: str  # Human-readable error message
    where: Optional[Dict[str, Any]] = None  # Additional context (connection, module, etc.)


class ValidatePipelineRequest(BaseModel):
    """Request body for POST /pipelines/validate"""
    pipeline_json: PipelineStateDTO = Field(..., alias="pipeline_json")


class ValidatePipelineResponse(BaseModel):
    """Response for POST /pipelines/validate"""
    valid: bool
    errors: List[ValidationErrorDTO] = []


# ============================================================================
# Execution
# ============================================================================

class ExecutePipelineRequest(BaseModel):
    """Request body for POST /pipelines/{id}/execute"""
    entry_values: Dict[str, Any] = Field(
        ...,
        description="Entry point values keyed by entry point name",
        example={"customer_name": "ACME Corp", "order_id": "12345"}
    )


class ExecutionStepResultDTO(BaseModel):
    """Result of a single module execution"""
    module_instance_id: str
    step_number: int
    inputs: Dict[str, Dict[str, Any]]  # {pin_name: {value, type}}
    outputs: Dict[str, Dict[str, Any]]  # {pin_name: {value, type}}
    error: Optional[str] = None


class ExecutePipelineResponse(BaseModel):
    """Response for POST /pipelines/{id}/execute"""
    status: str  # "success" | "failed"
    steps: List[ExecutionStepResultDTO]
    executed_actions: Dict[str, Dict[str, Any]]  # {module_instance_id: {input_name: value}}
    error: Optional[str] = None
