"""
PDF Templates API Schemas
Pydantic models for PDF template endpoints
"""
from typing import Optional, List, Dict, Any, Literal, Tuple, Union
from pydantic import BaseModel, Field


# Signature Objects (used across multiple endpoints)
class SignatureObjectBase(BaseModel):
    object_type: Literal["text_word", "text_line", "graphic_rect", "graphic_line", "graphic_curve", "image", "table"]
    page: int
    bbox: Tuple[float, float, float, float]  # [x0, y0, x1, y1]


# Extraction Fields (used across multiple endpoints)
class ExtractionField(BaseModel):
    field_id: str
    label: str
    description: Optional[str] = None
    page: int
    bbox: Tuple[float, float, float, float]  # [x0, y0, x1, y1]
    required: bool
    validation_regex: Optional[str] = None


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


class ListPdfTemplatesResponse(BaseModel):
    items: List[TemplateListItem]
    total: int
    limit: int
    offset: int


# GET /pdf-templates/{id} - Detail Response
class TemplateVersionDetail(BaseModel):
    version_id: int
    version_num: int
    usage_count: int
    last_used_at: Optional[str] = None  # ISO 8601
    signature_objects: List[Dict[str, Any]]  # Varies by object_type
    extraction_fields: List[ExtractionField]
    pipeline_definition_id: int


class PdfTemplateDetail(BaseModel):
    id: int
    name: str
    description: Optional[str] = None
    source_pdf_id: int
    status: Literal["active", "inactive"]
    current_version_id: int
    current_version: TemplateVersionDetail
    total_versions: int


# POST /pdf-templates - Create Request/Response
class CreatePdfTemplateRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = Field(None, max_length=1000)
    source_pdf_id: Optional[int] = None
    signature_objects: List[Dict[str, Any]] = Field(..., min_items=1)
    extraction_fields: List[ExtractionField] = Field(..., min_items=1)
    pipeline_state: PipelineState
    visual_state: VisualState


class CreatePdfTemplateResponse(BaseModel):
    id: int
    name: str
    status: Literal["inactive"]
    current_version_id: int
    current_version_num: int  # 1
    pipeline_definition_id: int


# PUT /pdf-templates/{id} - Update Request/Response
class UpdatePdfTemplateRequest(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = Field(None, max_length=1000)
    signature_objects: List[Dict[str, Any]] = Field(..., min_length=1)
    extraction_fields: List[ExtractionField] = Field(..., min_length=1)
    pipeline_state: PipelineState
    visual_state: VisualState


class UpdatePdfTemplateResponse(BaseModel):
    id: int
    name: str
    status: Literal["active", "inactive"]
    current_version_id: int
    current_version_num: int
    pipeline_definition_id: int


# POST /pdf-templates/{id}/activate - Activate Response
class ActivatePdfTemplateResponse(BaseModel):
    id: int
    status: Literal["active"]
    current_version_id: int


# POST /pdf-templates/{id}/deactivate - Deactivate Response
class DeactivatePdfTemplateResponse(BaseModel):
    id: int
    status: Literal["inactive"]
    current_version_id: int


# GET /pdf-templates/{id}/versions - List Versions Response
class TemplateVersionListItem(BaseModel):
    version_id: int
    version_num: int
    usage_count: int
    last_used_at: Optional[str] = None  # ISO 8601
    is_current: bool


class ListTemplateVersionsResponse(BaseModel):
    __root__: List[TemplateVersionListItem]


# GET /pdf-templates/{id}/versions/{version_id} - Version Detail Response
class GetTemplateVersionResponse(BaseModel):
    version_id: int
    template_id: int
    version_num: int
    usage_count: int
    last_used_at: Optional[str] = None  # ISO 8601
    is_current: bool
    signature_objects: List[Dict[str, Any]]
    extraction_fields: List[ExtractionField]
    pipeline_definition_id: int


# POST /pdf-templates/simulate - Simulate Request/Response
class SimulateTemplateRequestStored(BaseModel):
    pdf_source: Literal["stored"]
    pdf_file_id: int
    signature_objects: List[Dict[str, Any]]
    extraction_fields: List[ExtractionField]
    pipeline_state: PipelineState


class SimulateTemplateRequestUpload(BaseModel):
    pdf_source: Literal["upload"]
    signature_objects: List[Dict[str, Any]]
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
