"""
Pipelines API Schemas
Pydantic models for pipeline management endpoints
"""
from typing import List, Dict, Any, Optional
from pydantic import BaseModel


# Pipeline State structures (repeated from pdf_templates - will be refactored later)
class PipelineEntryPoint(BaseModel):
    id: str
    label: str
    field_reference: str


class PipelineNodePin(BaseModel):
    node_id: str
    name: str
    type: List[str]


class PipelineModuleInstance(BaseModel):
    instance_id: str
    module_id: str
    config: Dict[str, Any]
    inputs: List[PipelineNodePin]
    outputs: List[PipelineNodePin]


class PipelineConnection(BaseModel):
    from_node_id: str
    to_node_id: str


class PipelineState(BaseModel):
    entry_points: List[PipelineEntryPoint]
    modules: List[PipelineModuleInstance]
    connections: List[PipelineConnection]


class VisualState(BaseModel):
    positions: Dict[str, Dict[str, float]]  # {id: {x: float, y: float}}


# GET /pipelines - List Response
class PipelineListItem(BaseModel):
    id: int
    compiled_plan_id: Optional[int] = None  # null if not yet compiled
    created_at: str  # ISO 8601 (included for dev convenience)
    updated_at: str  # ISO 8601 (included for dev convenience)


class ListPipelinesResponse(BaseModel):
    items: List[PipelineListItem]
    total: int
    limit: int
    offset: int


# GET /pipelines/{id} - Detail Response
class GetPipelineResponse(BaseModel):
    id: int
    compiled_plan_id: Optional[int] = None  # Reference to compiled execution plan (if compiled)
    pipeline_state: PipelineState
    visual_state: VisualState


# POST /pipelines - Create Request/Response
class CreatePipelineRequest(BaseModel):
    pipeline_state: PipelineState
    visual_state: VisualState


class CreatePipelineResponse(BaseModel):
    id: int
    compiled_plan_id: Optional[int] = None  # null initially, set on first compilation


# PUT /pipelines/{id} - Update Request/Response
class UpdatePipelineRequest(BaseModel):
    pipeline_state: PipelineState
    visual_state: VisualState


class UpdatePipelineResponse(BaseModel):
    id: int
    compiled_plan_id: Optional[int] = None  # May change if pipeline logic changed
