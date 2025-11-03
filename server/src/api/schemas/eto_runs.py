"""
ETO Runs API Schemas
Pydantic models for ETO run endpoints
"""
from typing import Optional, List, Dict, Any, Literal, Union
from pydantic import BaseModel, Field, ConfigDict

from .pdf_templates import ExtractedFieldResult

# =============================================================================
# Nested Models for EtoRunListItem
# =============================================================================

class EtoPdfInfo(BaseModel):
    """PDF file information"""
    id: int
    original_filename: str
    file_size: Optional[int] = None
    page_count: Optional[int] = None


class EtoSourceManual(BaseModel):
    """Manual upload source"""
    type: Literal["manual"]


class EtoSourceEmail(BaseModel):
    """Email ingestion source"""
    type: Literal["email"]
    sender_email: str
    received_date: str  # ISO 8601
    subject: Optional[str] = None
    folder_name: str


# Discriminated union for source
EtoSource = Union[EtoSourceManual, EtoSourceEmail]


class EtoMatchedTemplate(BaseModel):
    """Matched template information"""
    template_id: int
    template_name: str
    version_id: int
    version_num: int


# =============================================================================
# ETO Run List Item (for GET /eto-runs)
# =============================================================================

class EtoRunListItem(BaseModel):
    """
    Single ETO run item for list view.

    Used in GET /eto-runs response (wrapped in pagination).
    Includes core run data plus embedded related data (PDF, source, matched template).
    """
    id: int
    status: str
    processing_step: Optional[str] = None
    started_at: Optional[str] = None  # ISO 8601
    completed_at: Optional[str] = None  # ISO 8601
    error_type: Optional[str] = None
    error_message: Optional[str] = None

    # Embedded related data (not just foreign keys)
    pdf: EtoPdfInfo
    source: EtoSource = Field(..., discriminator="type")
    matched_template: Optional[EtoMatchedTemplate] = None


# =============================================================================
# GET /eto-runs Response (with pagination)
# =============================================================================

class GetEtoRunsResponse(BaseModel):
    """
    Response for GET /eto-runs with pagination metadata.

    Wraps list of EtoRunListItem with total count and pagination params.
    """
    items: List[EtoRunListItem]
    total: int
    limit: int
    offset: int


# =============================================================================
# POST /eto-runs - Create ETO Run
# =============================================================================

class CreateEtoRunRequest(BaseModel):
    """
    Request body for creating a new ETO run from an uploaded PDF.

    The PDF must already be uploaded to /api/pdf-files first.
    """
    pdf_file_id: int = Field(..., gt=0, description="ID of uploaded PDF file")


class CreateEtoRunResponse(BaseModel):
    """
    Response for POST /eto-runs.

    Returns the created run with initial status.
    """
    id: int
    status: str
    pdf_file_id: int
    started_at: Optional[str] = None  # Will be None for not_started runs
    created_at: str  # ISO 8601


# =============================================================================
# Bulk Operation Request Bodies
# =============================================================================

class BulkRunIdsRequest(BaseModel):
    """
    Request body for bulk operations on ETO runs.

    Used by:
    - POST /eto-runs/reprocess
    - POST /eto-runs/skip
    - DELETE /eto-runs
    """
    run_ids: List[int] = Field(..., min_length=1)


# =============================================================================
# GET /eto-runs/{id} - Detailed View with Stage Data
# =============================================================================

class EtoStageTemplateMatching(BaseModel):
    """
    Template matching stage data for detailed run view.
    """
    status: Literal["processing", "success", "failure"]
    matched_template_version_id: Optional[int] = None
    matched_template_name: Optional[str] = None  # Denormalized for convenience
    matched_version_number: Optional[int] = None  # Denormalized for convenience
    started_at: Optional[str] = None  # ISO 8601
    completed_at: Optional[str] = None  # ISO 8601


class EtoStageDataExtraction(BaseModel):
    """
    Data extraction stage data for detailed run view.
    Includes full extraction results with bbox data for visual display.
    """
    status: Literal["processing", "success", "failure"]
    extraction_results: Optional[List[ExtractedFieldResult]] = None  # Fields with bbox/page/value
    started_at: Optional[str] = None  # ISO 8601
    completed_at: Optional[str] = None  # ISO 8601


class EtoPipelineExecutionStep(BaseModel):
    """Individual step in pipeline execution"""
    id: int
    step_number: int
    module_instance_id: str
    inputs: Optional[Dict[str, Dict[str, Any]]] = None
    outputs: Optional[Dict[str, Dict[str, Any]]] = None
    error: Optional[Dict[str, Any]] = None


class EtoStagePipelineExecution(BaseModel):
    """
    Pipeline execution stage data for detailed run view.
    """
    status: Literal["processing", "success", "failure"]
    executed_actions: Optional[Dict[str, Any]] = None  # Parsed JSON
    started_at: Optional[str] = None  # ISO 8601
    completed_at: Optional[str] = None  # ISO 8601
    pipeline_definition_id: Optional[int] = None
    steps: Optional[List[EtoPipelineExecutionStep]] = None


class EtoRunDetail(BaseModel):
    """
    Detailed ETO run view including all stage information.

    Returned by GET /eto-runs/{id}

    Different data shown based on run status:
    - success: All stages with full data
    - failure: Partial stages, error details, which stage failed
    - needs_template: Template matching results only
    - processing: Stages up to current processing_step
    - not_started: No stage data yet
    """
    # Core run data
    id: int
    status: str
    processing_step: Optional[str] = None
    started_at: Optional[str] = None  # ISO 8601
    completed_at: Optional[str] = None  # ISO 8601
    error_type: Optional[str] = None
    error_message: Optional[str] = None
    error_details: Optional[str] = None

    # PDF file info
    pdf: EtoPdfInfo

    # Source (manual or email)
    source: EtoSource = Field(..., discriminator="type")

    # Stage data (optional - depends on run progress)
    stage_template_matching: Optional[EtoStageTemplateMatching] = None
    stage_data_extraction: Optional[EtoStageDataExtraction] = None
    stage_pipeline_execution: Optional[EtoStagePipelineExecution] = None
