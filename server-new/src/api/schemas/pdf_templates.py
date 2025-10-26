"""
PDF Templates API Schemas
Pydantic models for PDF template endpoints
"""
from typing import Optional, List, Dict, Any, Literal, Tuple, Union
from pydantic import BaseModel, Field


# Extraction Fields (used across multiple endpoints)
class ExtractionField(BaseModel):
    name: str
    description: Optional[str] = None
    bbox: Tuple[float, float, float, float]  # [x0, y0, x1, y1]
    page: int


# Pipeline State structures
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


# GET /pdf-templates - List Response
class TemplateVersionSummary(BaseModel):
    version_id: int
    version_num: int
    usage_count: int


class TemplateListItem(BaseModel):
    id: int
    name: str
    description: Optional[str] = None
    status: Literal["active", "inactive"]
    source_pdf_id: int
    current_version: TemplateVersionSummary
    total_versions: int


# PdfTemplate - Main template object (mirrors domain PdfTemplate exactly)
class PdfTemplate(BaseModel):
    """Template metadata - mirrors backend domain PdfTemplate"""
    id: int
    name: str
    description: Optional[str] = None
    status: Literal["active", "inactive"]
    source_pdf_id: int
    current_version_id: Optional[int] = None
    created_at: str  # ISO 8601
    updated_at: str  # ISO 8601


# GET /pdf-templates/{id}/versions - Version list item
class VersionListItem(BaseModel):
    """Lightweight version identifier for navigation"""
    version_id: int
    version_number: int


# POST /pdf-templates - Create Request
class CreatePdfTemplateRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = Field(None, max_length=1000)
    source_pdf_id: Optional[int] = None
    signature_objects: Dict[str, List[Dict[str, Any]]]  # Grouped: {"text_words": [...], "graphic_rects": [...]}
    extraction_fields: List[ExtractionField] = Field(..., min_length=1)
    pipeline_state: PipelineState
    visual_state: VisualState


# PUT /pdf-templates/{id} - Update Request
class UpdatePdfTemplateRequest(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = Field(None, max_length=1000)
    signature_objects: Optional[Dict[str, List[Dict[str, Any]]]] = None  # Grouped: {"text_words": [...], "graphic_rects": [...]}
    extraction_fields: Optional[List[ExtractionField]] = None
    pipeline_state: Optional[PipelineState] = None
    visual_state: Optional[VisualState] = None


# GET /pdf-templates/versions/{version_id} - Version Detail Response
class GetTemplateVersionResponse(BaseModel):
    version_id: int
    template_id: int
    version_num: int
    source_pdf_id: int
    is_current: bool
    signature_objects: Dict[str, List[Dict[str, Any]]]  # Grouped: {"text_words": [...], "graphic_rects": [...]}
    extraction_fields: List[ExtractionField]
    pipeline_definition_id: int
    created_at: str  # ISO 8601


# POST /pdf-templates/simulate - Simulate Request/Response
class SimulateTemplateRequestStored(BaseModel):
    pdf_source: Literal["stored"]
    pdf_file_id: int
    extraction_fields: List[ExtractionField]
    pipeline_state: PipelineState


class SimulateTemplateRequestUpload(BaseModel):
    pdf_source: Literal["upload"]
    # pdf_file will be sent as multipart/form-data
    extraction_fields: List[ExtractionField]
    pipeline_state: PipelineState


class ValidationResult(BaseModel):
    field_label: str
    required: bool
    has_value: bool
    regex_valid: Optional[bool] = None  # null if no regex
    error: Optional[str] = None


class DataExtractionSimulation(BaseModel):
    status: Literal["success", "failure"]
    extracted_data: Optional[Dict[str, str]] = None
    error_message: Optional[str] = None
    validation_results: List[ValidationResult]


class PipelineStepSimulation(BaseModel):
    step_number: int
    module_instance_id: str
    module_name: str
    inputs: Dict[str, Dict[str, Any]]  # {node_name: {value, type}}
    outputs: Dict[str, Dict[str, Any]]  # {node_name: {value, type}}
    error: Optional[Dict[str, Any]] = None


class SimulatedAction(BaseModel):
    action_module_name: str
    inputs: Dict[str, Any]
    simulation_note: str


class PipelineExecutionSimulation(BaseModel):
    status: Literal["success", "failure"]
    error_message: Optional[str] = None
    steps: List[PipelineStepSimulation]
    simulated_actions: List[SimulatedAction]


class SimulateTemplateResponse(BaseModel):
    template_matching: Dict[str, str]  # {status: "success", message: "Simulation mode..."}
    data_extraction: DataExtractionSimulation
    pipeline_execution: PipelineExecutionSimulation
