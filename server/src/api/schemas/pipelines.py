"""
Pipelines API Schemas
Pydantic models for pipeline definition endpoints
"""
from typing import List, Dict, Any, Optional, Literal, TypeAlias
from pydantic import BaseModel, Field

# ============================================================================
# Pipeline State Types (logical structure)
# ============================================================================

class Node(BaseModel):
    """Node (pin) in a module instance"""
    node_id: str
    type: str  # "str", "int", "float", "bool", "datetime", etc.
    name: str
    position_index: int
    group_index: int


class EntryPoint(BaseModel):
    """Entry point for pipeline - structured like a module with outputs"""
    entry_point_id: str  # Format: E01, E02, etc.
    name: str
    outputs: List[Node] = []  # Array with single output pin containing the type


class ModuleInstance(BaseModel):
    """Module instance placed on the canvas"""
    module_instance_id: str
    module_ref: str  # e.g., "text_cleaner:1.0.0"
    config: Dict[str, Any]  # Module-specific configuration
    inputs: List[Node] = []
    outputs: List[Node] = []


class NodeConnection(BaseModel):
    """Connection between two nodes"""
    from_node_id: str
    to_node_id: str


class PipelineState(BaseModel):
    """Pipeline execution structure"""
    entry_points: List[EntryPoint] = []
    modules: List[ModuleInstance] = []
    connections: List[NodeConnection] = []


# ============================================================================
# Visual State Types (UI layout)
# ============================================================================

class Position(BaseModel):
    """2D position for visual layout"""
    x: float
    y: float


# Flat visual state structure - all node positions in one dictionary
# Key: node_id (for both modules and entry points)
# Value: Position {x, y}
VisualState: TypeAlias = Dict[str, Position]


# ============================================================================
# Pipeline Definition Types
# ============================================================================

class PipelineSummary(BaseModel):
    """Lightweight pipeline summary for list views (GET /pipelines)"""
    id: int
    compiled_plan_id: Optional[int] = None  # null if not yet compiled


class PipelinesListResponse(BaseModel):
    """Response for GET /pipelines"""
    items: List[PipelineSummary]
    total: int
    limit: int
    offset: int


class PipelineDetail(BaseModel):
    """Full pipeline definition details (GET /pipelines/{id})"""
    id: int
    compiled_plan_id: Optional[int] = None
    pipeline_state: PipelineState
    visual_state: VisualState


# ============================================================================
# Create/Update Requests
# ============================================================================

class CreatePipelineRequest(BaseModel):
    """Request body for POST /pipelines"""
    pipeline_state: PipelineState
    visual_state: VisualState


class CreatePipelineResponse(BaseModel):
    """Response for POST /pipelines"""
    id: int  # Created pipeline ID
    compiled_plan_id: Optional[int] = None  # null initially, set on first compilation


# ============================================================================
# Validation
# ============================================================================

class ValidationError(BaseModel):
    """Single validation error"""
    code: str  # Error code (e.g., "type_mismatch", "cycle_detected")
    message: str  # Human-readable error message
    where: Optional[Dict[str, Any]] = None  # Additional context (connection, module, etc.)


class ValidatePipelineRequest(BaseModel):
    """Request body for POST /pipelines/validate"""
    pipeline_json: PipelineState = Field(..., alias="pipeline_json")


class ValidatePipelineResponse(BaseModel):
    """Response for POST /pipelines/validate"""
    valid: bool
    error: Optional[ValidationError] = None


# ============================================================================
# Execution
# ============================================================================

class ExecutePipelineRequest(BaseModel):
    """Request body for POST /pipelines/{id}/execute"""
    entry_values: Dict[str, Any] = Field(
        ...,
        description="Entry point values keyed by entry point name",
    )


class ExecutionStepResult(BaseModel):
    """Result of a single module execution"""
    module_instance_id: str
    step_number: int
    inputs: Dict[str, Dict[str, Any]]  # {pin_name: {value, type}}
    outputs: Dict[str, Dict[str, Any]]  # {pin_name: {value, type}}
    error: Optional[str] = None


class ExecutePipelineResponse(BaseModel):
    """Response for POST /pipelines/{id}/execute"""
    status: str  # "success" | "failed"
    steps: List[ExecutionStepResult]
    executed_actions: Dict[str, Dict[str, Any]]  # {module_instance_id: {input_name: value}}
    error: Optional[str] = None
