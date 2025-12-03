"""
PDF Templates API Schemas
Pydantic models for PDF template endpoints
"""
from typing import Optional, List, Dict, Any, Literal, Tuple, Union
from pydantic import BaseModel, Field

# Import canonical pipeline types (single source of truth)
from api.schemas.pipelines import PipelineState, VisualState, ExecutionStepResult
from api.schemas.pdf_files import PdfObjects


# Extraction Fields (used across multiple endpoints)
class ExtractionField(BaseModel):
    name: str
    description: Optional[str] = None
    bbox: Tuple[float, float, float, float]  # [x0, y0, x1, y1]
    page: int


# GET /pdf-templates - List Response
class TemplateVersionSummary(BaseModel):
    version_id: int
    version_num: int
    usage_count: int


class TemplateListItem(BaseModel):
    id: int
    name: str
    description: Optional[str] = None
    status: str
    source_pdf_id: int
    current_version: TemplateVersionSummary
    total_versions: int


# Version list item (used in template responses)
class VersionListItem(BaseModel):
    """Lightweight version identifier for navigation"""
    version_id: int
    version_number: int


# PdfTemplate - Main template object (API version without audit timestamps)
class PdfTemplate(BaseModel):
    """Template metadata for API responses with version navigation (excludes audit timestamps)"""
    id: int
    name: str
    description: Optional[str] = None
    status: str
    source_pdf_id: int
    current_version_id: Optional[int] = None
    versions: List[VersionListItem]  # All versions for navigation


# POST /pdf-templates - Create Request
class CreatePdfTemplateRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = Field(None, max_length=1000)
    source_pdf_id: int  # Required - PDF must be uploaded first via POST /pdf-files
    signature_objects: PdfObjects
    extraction_fields: List[ExtractionField] = Field(..., min_length=1)
    pipeline_state: PipelineState
    visual_state: VisualState


# PUT /pdf-templates/{id} - Update Request
class UpdatePdfTemplateRequest(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = Field(None, max_length=1000)
    signature_objects: Optional[PdfObjects] = None
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
    signature_objects: PdfObjects
    extraction_fields: List[ExtractionField]
    pipeline_definition_id: int


# POST /pdf-templates/simulate - Simulate Request
class SimulateTemplateRequest(BaseModel):
    """Request for template simulation (testing/preview only)"""
    pdf_objects: PdfObjects
    extraction_fields: List[ExtractionField] = Field(..., min_length=1)
    pipeline_state: PipelineState


# POST /pdf-templates/simulate - Simulate Response
class ExtractedFieldResult(BaseModel):
    """Single extraction field result with bbox for visual display"""
    name: str
    description: Optional[str] = None
    bbox: Tuple[float, float, float, float]  # [x0, y0, x1, y1]
    page: int
    extracted_value: str  # The actual extracted text


class SimulateTemplateResponse(BaseModel):
    """
    Response for POST /pdf-templates/simulate
    Matches the format from POST /pipelines/{id}/execute for consistency
    """
    extraction_results: List[ExtractedFieldResult]  # Fields with extracted values and bbox info
    pipeline_status: str  # "success" | "failed"
    pipeline_steps: List[ExecutionStepResult]  # Reuse from pipelines
    output_module_id: Optional[str] = None  # Output module to execute (if any)
    output_module_inputs: Dict[str, Any] = {}  # {input_name: value} collected for output module
    pipeline_error: Optional[str] = None


# ========== Test Multi-Template Matching Schemas ==========

class TemplateMatchResult(BaseModel):
    """Single template match for a consecutive page range"""
    template_id: int
    template_name: str
    version_id: int
    version_number: int
    matched_pages: List[int]  # Consecutive pages, 1-indexed


class TestMultiTemplateMatchingResponse(BaseModel):
    """
    Response for POST /pdf-templates/test-multi-match
    Temporary endpoint for e2e testing multi-template matching
    """
    pdf_id: int
    pdf_filename: str
    total_pages: int
    matches: List[TemplateMatchResult]
    unmatched_pages: List[int]  # Can be non-consecutive, 1-indexed
