"""
PDF Templates API Schemas

Pydantic models for PDF template endpoints.
Reuses domain types from shared/types where possible.
"""
from typing import Any

from pydantic import BaseModel, Field, model_validator

# Import domain types
from shared.types.pipelines import PipelineState, VisualState
from shared.types.pdf_files import PdfObjects
from shared.types.pdf_templates import (
    ExtractionField,
    PdfTemplateStatus,
    PdfTemplateVersionSummary,
)
from shared.types.pipeline_execution import PipelineExecutionStatus, PipelineExecutionStepResult


# ========== List Response ==========

class TemplateVersionSummary(BaseModel):
    """Version summary for list items"""
    version_id: int
    version_num: int
    usage_count: int


class TemplateListItem(BaseModel):
    """Template list item with version info"""
    id: int
    name: str
    description: str | None = None
    customer_id: int | None = None
    customer_name: str | None = None  # Enriched from Access DB
    status: PdfTemplateStatus
    is_autoskip: bool = False
    source_pdf_id: int
    page_count: int | None = None  # From source PDF file
    current_version: TemplateVersionSummary
    total_versions: int


class PaginatedTemplateListResponse(BaseModel):
    """Paginated response for template list"""
    items: list[TemplateListItem]
    total: int
    limit: int
    offset: int


# ========== Version Navigation ==========

class VersionListItem(BaseModel):
    """Lightweight version identifier for navigation"""
    version_id: int
    version_number: int


# ========== Template Detail ==========

class PdfTemplateResponse(BaseModel):
    """Template metadata for API responses (excludes audit timestamps)"""
    id: int
    name: str
    description: str | None = None
    customer_id: int | None = None
    customer_name: str | None = None  # Enriched from Access DB
    status: PdfTemplateStatus
    is_autoskip: bool = False
    source_pdf_id: int
    current_version_id: int | None = None
    versions: list[VersionListItem]


# ========== Create Request ==========

class CreatePdfTemplateRequest(BaseModel):
    """Request for POST /pdf-templates"""
    name: str = Field(..., min_length=1, max_length=255)
    description: str | None = Field(None, max_length=1000)
    customer_id: int | None = None
    is_autoskip: bool = False
    source_pdf_id: int
    signature_objects: PdfObjects
    extraction_fields: list[ExtractionField] = Field(default_factory=list)
    pipeline_state: PipelineState
    visual_state: VisualState

    @model_validator(mode='after')
    def validate_extraction_fields(self):
        """Autoskip templates can have empty extraction fields"""
        if not self.is_autoskip and len(self.extraction_fields) == 0:
            raise ValueError('extraction_fields must have at least 1 item for non-autoskip templates')
        return self


# ========== Update Request ==========

class UpdatePdfTemplateRequest(BaseModel):
    """Request for PUT /pdf-templates/{id}"""
    name: str | None = Field(None, min_length=1, max_length=255)
    description: str | None = Field(None, max_length=1000)
    customer_id: int | None = None
    is_autoskip: bool | None = None
    signature_objects: PdfObjects | None = None
    extraction_fields: list[ExtractionField] | None = None
    pipeline_state: PipelineState | None = None
    visual_state: VisualState | None = None


# ========== Version Detail ==========

class GetTemplateVersionResponse(BaseModel):
    """Response for GET /pdf-templates/versions/{version_id}"""
    version_id: int
    template_id: int
    version_num: int
    source_pdf_id: int
    is_current: bool
    signature_objects: PdfObjects
    extraction_fields: list[ExtractionField]
    pipeline_definition_id: int | None = None


# ========== Simulation ==========

class SimulateTemplateRequest(BaseModel):
    """Request for POST /pdf-templates/simulate"""
    pdf_objects: PdfObjects
    extraction_fields: list[ExtractionField] = Field(..., min_length=1)
    pipeline_state: PipelineState


class ExtractedFieldResult(BaseModel):
    """Single extraction field result with bbox for visual display"""
    name: str
    description: str | None = None
    bbox: tuple[float, float, float, float]
    page: int
    extracted_value: str


class SimulateTemplateResponse(BaseModel):
    """Response for POST /pdf-templates/simulate"""
    extraction_results: list[ExtractedFieldResult]
    pipeline_status: PipelineExecutionStatus
    pipeline_steps: list[PipelineExecutionStepResult]
    output_channel_values: dict[str, Any] = Field(default_factory=dict)
    pipeline_error: str | None = None


# ========== Multi-Template Matching ==========

class TemplateMatchResult(BaseModel):
    """Single template match for a consecutive page range"""
    template_id: int
    template_name: str
    version_id: int
    version_number: int
    matched_pages: list[int]


class TestMultiTemplateMatchingResponse(BaseModel):
    """Response for POST /pdf-templates/test-multi-match"""
    pdf_id: int
    pdf_filename: str
    total_pages: int
    matches: list[TemplateMatchResult]
    unmatched_pages: list[int]


# ========== Customers ==========

class Customer(BaseModel):
    """Customer entry for dropdown lists"""
    id: int
    name: str


class GetCustomersResponse(BaseModel):
    """Response for GET /pdf-templates/customers"""
    customers: list[Customer]
