"""
ETO Runs API Schemas
Pydantic models for ETO run endpoints
"""
from typing import Optional, List, Dict, Any, Literal, Union
from pydantic import BaseModel, Field, ConfigDict

# =============================================================================
# Nested Models for ETO Runs
# =============================================================================

class EtoPdfInfo(BaseModel):
    """PDF file information"""
    id: int
    original_filename: str
    file_size: Optional[int] = None
    page_count: int  # Required for detail view


class EtoSourceManual(BaseModel):
    """Manual upload source"""
    type: Literal["manual"]
    created_at: str  # ISO 8601


class EtoSourceEmail(BaseModel):
    """Email ingestion source"""
    type: Literal["email"]
    sender_email: str
    received_at: str  # ISO 8601
    subject: Optional[str] = None
    folder_name: str


# Discriminated union for source
EtoSource = Union[EtoSourceManual, EtoSourceEmail]


class EtoMatchedTemplate(BaseModel):
    """Matched template information (for list view)"""
    template_id: int
    template_name: str
    version_id: int
    version_num: int


class EtoSubRunTemplate(BaseModel):
    """Simplified template info (for detail view)"""
    id: int
    name: str


# =============================================================================
# Sub-Run Summary (for list view)
# =============================================================================

class EtoSubRunsSummary(BaseModel):
    """
    Summary of sub-runs for list view.
    Provides counts by status for quick overview without full sub-run details.
    """
    total_count: int
    matched_count: int  # Sub-runs with a matched template
    needs_template_count: int  # Sub-runs without template match (unmatched group)
    success_count: int
    failure_count: int
    processing_count: int
    not_started_count: int

    # Page counts for display
    pages_matched_count: int  # Total pages across matched sub-runs
    pages_unmatched_count: int  # Total pages in unmatched groups (needs_template)


# =============================================================================
# Sub-Run Detail Models (for detail view)
# =============================================================================

class TransformResult(BaseModel):
    """
    Pipeline transform result for a sub-run.
    Placeholder for future transform output display.
    """
    field_name: str
    value: str


class EtoSubRunDetail(BaseModel):
    """
    Simplified detail for a single sub-run.

    Each sub-run represents a set of pages matched to a template (or unmatched).
    UI will filter sub-runs by status to display in appropriate sections.
    """
    id: int
    status: str
    matched_pages: List[int]  # Page numbers this sub-run covers
    template: Optional[EtoSubRunTemplate] = None  # None for needs_template sub-runs
    transform_results: List[TransformResult] = []  # Empty for now
    error_message: Optional[str] = None


# =============================================================================
# Sub-Run Full Detail (for GET /eto-runs/sub-runs/{id})
# =============================================================================

class ExtractionResult(BaseModel):
    """Single extraction result from a template field"""
    name: str
    description: Optional[str] = None
    bbox: List[float]  # [x0, y0, x1, y1]
    page: int
    extracted_value: str


class EtoSubRunExtractionDetail(BaseModel):
    """Extraction stage detail for a sub-run"""
    status: str  # 'processing' | 'success' | 'failure'
    started_at: Optional[str] = None  # ISO 8601
    completed_at: Optional[str] = None  # ISO 8601
    extraction_results: List[ExtractionResult] = []


class PipelineExecutionStepError(BaseModel):
    """Error info for a failed pipeline step"""
    type: str
    message: str
    details: Optional[Any] = None


class PipelineExecutionStep(BaseModel):
    """Individual step execution result"""
    id: int
    step_number: int
    module_instance_id: str
    inputs: Optional[Dict[str, Any]] = None
    outputs: Optional[Dict[str, Any]] = None
    error: Optional[PipelineExecutionStepError] = None


class EtoSubRunPipelineExecutionDetail(BaseModel):
    """Pipeline execution stage detail for a sub-run"""
    status: str  # 'processing' | 'success' | 'failure'
    started_at: Optional[str] = None  # ISO 8601
    completed_at: Optional[str] = None  # ISO 8601
    executed_actions: Optional[Dict[str, Any]] = None
    pipeline_definition_id: Optional[int] = None
    steps: List[PipelineExecutionStep] = []


class EtoSubRunFullDetail(BaseModel):
    """
    Full detail for a single sub-run including extraction and pipeline data.

    Used by GET /eto-runs/sub-runs/{id} for the sub-run detail modal.
    Mirrors the old EtoRunDetail structure but at the sub-run level.
    """
    id: int
    eto_run_id: int
    status: str
    matched_pages: List[int]
    template: Optional[EtoSubRunTemplate] = None
    template_version_id: Optional[int] = None
    error_type: Optional[str] = None
    error_message: Optional[str] = None
    error_details: Optional[str] = None
    started_at: Optional[str] = None
    completed_at: Optional[str] = None

    # PDF info (from parent run)
    pdf: EtoPdfInfo

    # Stage details (optional, only present if processing reached that stage)
    stage_data_extraction: Optional[EtoSubRunExtractionDetail] = None
    stage_pipeline_execution: Optional[EtoSubRunPipelineExecutionDetail] = None


class EtoRunOverview(BaseModel):
    """Computed overview stats for detail view"""
    templates_matched_count: int
    processing_time_ms: Optional[int] = None


class PageStatus(BaseModel):
    """Page breakdown entry showing status per page"""
    page_number: int
    status: str  # Uses EtoSubRunStatus values directly
    sub_run_id: int


# =============================================================================
# Sub-Run List Item (for list view with basic info)
# =============================================================================

class EtoSubRunListItem(BaseModel):
    """
    Basic sub-run info for list view.
    Less detail than EtoSubRunDetail - just enough for display in a list.
    """
    id: int
    sequence: Optional[int] = None
    status: str
    matched_pages: List[int]
    template: Optional[EtoMatchedTemplate] = None


# =============================================================================
# ETO Run List Item (for GET /eto-runs)
# =============================================================================

class EtoRunListItem(BaseModel):
    """
    Single ETO run item for list view.

    Used in GET /eto-runs response (wrapped in pagination).
    Includes core run data plus embedded related data (PDF, source, sub-runs summary).
    """
    id: int
    status: str
    processing_step: Optional[str] = None
    is_read: bool
    started_at: Optional[str] = None  # ISO 8601
    completed_at: Optional[str] = None  # ISO 8601
    updated_at: Optional[str] = None  # ISO 8601
    last_processed_at: Optional[str] = None  # ISO 8601 - Max sub-run timestamp
    error_type: Optional[str] = None
    error_message: Optional[str] = None

    # Embedded related data
    pdf: EtoPdfInfo
    source: EtoSource = Field(..., discriminator="type")

    # Sub-runs summary (replaces single matched_template)
    sub_runs_summary: EtoSubRunsSummary

    # Optional: include basic sub-run list for expandable rows
    sub_runs: Optional[List[EtoSubRunListItem]] = None


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
    started_at: Optional[str] = None
    created_at: str  # ISO 8601


# =============================================================================
# PATCH /eto-runs/{id} - Update ETO Run
# =============================================================================

class UpdateEtoRunRequest(BaseModel):
    """
    Request body for updating an ETO run.

    Currently only supports marking runs as read/unread.
    All fields are optional - only provided fields will be updated.
    """
    is_read: Optional[bool] = Field(None, description="Mark run as read (True) or unread (False)")


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
# Sub-Run Level Operations
# =============================================================================

class SubRunOperationResponse(BaseModel):
    """
    Response for sub-run level operations (reprocess, skip).

    Returns the new sub-run ID since the original sub-run is deleted
    and a new one is created with the same pages.
    """
    new_sub_run_id: int = Field(..., description="ID of the newly created sub-run")
    eto_run_id: int = Field(..., description="Parent ETO run ID")


class RunOperationResponse(BaseModel):
    """
    Response for run-level aggregated operations (reprocess_run, skip_run).

    These operations aggregate all failed/needs_template sub-runs into a single
    new sub-run. Returns None for new_sub_run_id if no eligible sub-runs found.
    """
    run_id: int = Field(..., description="ETO run ID that was operated on")
    new_sub_run_id: Optional[int] = Field(None, description="ID of the newly created sub-run (None if no eligible sub-runs)")
    message: str = Field(..., description="Description of what was done")


# =============================================================================
# GET /eto-runs/{id} - Detailed View with Sub-Runs
# =============================================================================

class EtoRunDetail(BaseModel):
    """
    Detailed ETO run view including all sub-run information.

    Returned by GET /eto-runs/{id}

    The parent run orchestrates multiple sub-runs, each representing
    a set of pages matched to a template (or an unmatched group).

    Status meanings:
    - processing: Has sub-runs still being processed
    - success: All sub-runs completed (may have individual failures)
    - failure: Critical system error (not sub-run level failure)
    - needs_template: Has unmatched pages requiring user action
    - skipped: User chose to skip this run
    """
    # Core run data
    id: int
    status: str
    processing_step: Optional[str] = None
    started_at: Optional[str] = None  # ISO 8601
    completed_at: Optional[str] = None  # ISO 8601
    error_type: Optional[str] = None
    error_message: Optional[str] = None

    # PDF file info
    pdf: EtoPdfInfo

    # Source (manual or email)
    source: EtoSource = Field(..., discriminator="type")

    # Computed overview stats
    overview: EtoRunOverview

    # Sub-runs with detail (UI filters by status)
    sub_runs: List[EtoSubRunDetail]

    # Page breakdown
    page_statuses: List[PageStatus]
