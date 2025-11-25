"""
ETO Runs API Schemas
Pydantic models for ETO run endpoints
"""
from typing import Optional, List, Dict, Any, Literal, Union
from pydantic import BaseModel, Field, ConfigDict

from .pdf_templates import ExtractedFieldResult

# =============================================================================
# Nested Models for ETO Runs
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


# =============================================================================
# Sub-Run Detail Models (for detail view)
# =============================================================================

class EtoSubRunExtraction(BaseModel):
    """
    Extraction stage data for a sub-run.
    """
    id: int
    status: Literal["processing", "success", "failure"]
    extraction_results: Optional[List[ExtractedFieldResult]] = None
    error_message: Optional[str] = None
    started_at: Optional[str] = None  # ISO 8601
    completed_at: Optional[str] = None  # ISO 8601


class EtoSubRunPipelineExecutionStep(BaseModel):
    """Individual step in pipeline execution"""
    id: int
    step_number: int
    module_instance_id: str
    inputs: Optional[Dict[str, Any]] = None
    outputs: Optional[Dict[str, Any]] = None
    error: Optional[str] = None


class EtoSubRunPipelineExecution(BaseModel):
    """
    Pipeline execution stage data for a sub-run.
    """
    id: int
    status: Literal["processing", "success", "failure"]
    executed_actions: Optional[List[Dict[str, Any]]] = None
    error_message: Optional[str] = None
    started_at: Optional[str] = None  # ISO 8601
    completed_at: Optional[str] = None  # ISO 8601
    steps: Optional[List[EtoSubRunPipelineExecutionStep]] = None


class EtoSubRunDetail(BaseModel):
    """
    Full detail for a single sub-run.

    Each sub-run represents a set of pages matched to a template (or unmatched).
    """
    id: int
    sequence: Optional[int] = None
    status: str
    matched_pages: List[int]  # Page numbers this sub-run covers
    is_unmatched_group: bool

    # Error tracking
    error_type: Optional[str] = None
    error_message: Optional[str] = None

    # Timestamps
    started_at: Optional[str] = None  # ISO 8601
    completed_at: Optional[str] = None  # ISO 8601

    # Template info (None for unmatched groups)
    template: Optional[EtoMatchedTemplate] = None

    # Stage data (optional - depends on sub-run progress)
    extraction: Optional[EtoSubRunExtraction] = None
    pipeline_execution: Optional[EtoSubRunPipelineExecution] = None


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
    is_unmatched_group: bool
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
    started_at: Optional[str] = None  # ISO 8601
    completed_at: Optional[str] = None  # ISO 8601
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
    error_details: Optional[str] = None

    # PDF file info
    pdf: EtoPdfInfo

    # Source (manual or email)
    source: EtoSource = Field(..., discriminator="type")

    # Sub-runs with full detail
    sub_runs: List[EtoSubRunDetail]
