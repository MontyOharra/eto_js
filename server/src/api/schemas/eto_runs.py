"""
ETO Runs API Schemas
Pydantic models for ETO run endpoints

This module defines API request/response schemas for ETO runs.
Where possible, we reuse domain types from shared/types/ to avoid duplication.
"""
from typing import Any, Literal

from pydantic import BaseModel, Field

# =============================================================================
# Import Domain Types for Reuse
# =============================================================================
# These domain types are used directly in API responses where the structure matches

from shared.types.eto_runs import (
    EtoRunListView,
    EtoRunDetailView,
    EtoMasterStatus,
    EtoRunProcessingStep,
    EtoStepStatus,
)
from shared.types.eto_sub_runs import (
    EtoSubRunDetailView,
    EtoSubRunStatus,
    EtoRunExtractionDetailView,
    EtoRunPipelineExecutionDetailView,
    EtoRunPipelineExecutionStepDetailView,
)
from shared.types.pdf_files import ExtractedFieldData


# =============================================================================
# Nested Models for ETO Runs (API-specific transformations)
# =============================================================================

class EtoPdfInfo(BaseModel):
    """PDF file information for API responses"""
    id: int
    original_filename: str
    file_size: int | None = None
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
    subject: str | None = None
    folder_name: str


# Discriminated union for source
EtoSource = EtoSourceManual | EtoSourceEmail


class EtoMatchedTemplate(BaseModel):
    """Matched template information (for list view)"""
    template_id: int
    template_name: str
    customer_name: str | None = None  # Customer name from Access DB (if available)
    version_id: int
    version_num: int


class EtoSubRunTemplate(BaseModel):
    """Simplified template info (for detail view)"""
    id: int
    name: str
    customer_name: str | None = None  # Customer name from Access DB (if available)


# =============================================================================
# Sub-Run Summary (for list view)
# =============================================================================

class EtoSubRunsSummary(BaseModel):
    """
    Summary of sub-runs for list view.
    Provides counts by status for quick overview without full sub-run details.

    status_counts is a dict mapping status string to count, e.g.:
    {"success": 2, "failure": 1, "needs_template": 3, "skipped": 0}
    """
    status_counts: dict[str, int]


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
    status: EtoSubRunStatus
    matched_pages: list[int]  # Page numbers this sub-run covers
    template: EtoSubRunTemplate | None = None  # None for needs_template sub-runs
    transform_results: list[TransformResult] = []  # Empty for now
    error_message: str | None = None


# =============================================================================
# Sub-Run Full Detail (for GET /eto-runs/sub-runs/{id})
# =============================================================================
# Note: ExtractionResult is equivalent to ExtractedFieldData from shared/types/pdf_files
# We re-export it here for backwards compatibility

ExtractionResult = ExtractedFieldData


class EtoSubRunExtractionDetail(BaseModel):
    """
    Extraction stage detail for a sub-run.

    Note: This is an API-specific version that converts datetime to ISO strings.
    The domain type EtoRunExtractionDetailView uses datetime objects.
    """
    status: EtoStepStatus
    started_at: str | None = None  # ISO 8601
    completed_at: str | None = None  # ISO 8601
    extraction_results: list[ExtractionResult] = []


class PipelineExecutionStepError(BaseModel):
    """Error info for a failed pipeline step"""
    type: str
    message: str
    details: Any | None = None


class PipelineExecutionStep(BaseModel):
    """Individual step execution result"""
    id: int
    step_number: int
    module_instance_id: str
    inputs: dict[str, Any] | None = None
    outputs: dict[str, Any] | None = None
    error: PipelineExecutionStepError | None = None


class EtoSubRunPipelineExecutionDetail(BaseModel):
    """
    Pipeline execution stage detail for a sub-run.

    Note: This is an API-specific version that converts datetime to ISO strings.
    The domain type EtoRunPipelineExecutionDetailView uses datetime objects.
    """
    status: EtoStepStatus
    started_at: str | None = None  # ISO 8601
    completed_at: str | None = None  # ISO 8601
    pipeline_definition_id: int | None = None
    steps: list[PipelineExecutionStep] = []


class EtoSubRunFullDetail(BaseModel):
    """
    Full detail for a single sub-run including extraction and pipeline data.

    Used by GET /eto-runs/sub-runs/{id} for the sub-run detail modal.
    Mirrors the old EtoRunDetail structure but at the sub-run level.
    """
    id: int
    eto_run_id: int
    status: EtoSubRunStatus
    matched_pages: list[int]
    template: EtoSubRunTemplate | None = None
    template_version_id: int | None = None
    error_type: str | None = None
    error_message: str | None = None
    error_details: str | None = None
    started_at: str | None = None
    completed_at: str | None = None

    # PDF info (from parent run)
    pdf: EtoPdfInfo

    # Stage details (optional, only present if processing reached that stage)
    stage_data_extraction: EtoSubRunExtractionDetail | None = None
    stage_pipeline_execution: EtoSubRunPipelineExecutionDetail | None = None


class EtoRunOverview(BaseModel):
    """Computed overview stats for detail view"""
    templates_matched_count: int
    processing_time_ms: int | None = None


class PageStatus(BaseModel):
    """Page breakdown entry showing status per page"""
    page_number: int
    status: EtoSubRunStatus
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
    sequence: int | None = None
    status: EtoSubRunStatus
    matched_pages: list[int]
    template: EtoMatchedTemplate | None = None


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
    status: EtoMasterStatus
    processing_step: EtoRunProcessingStep | None = None
    is_read: bool
    started_at: str | None = None  # ISO 8601
    completed_at: str | None = None  # ISO 8601
    updated_at: str | None = None  # ISO 8601
    last_processed_at: str | None = None  # ISO 8601 - Max sub-run timestamp
    error_type: str | None = None
    error_message: str | None = None

    # Embedded related data
    pdf: EtoPdfInfo
    source: EtoSource = Field(..., discriminator="type")

    # Sub-runs summary (replaces single matched_template)
    sub_runs_summary: EtoSubRunsSummary

    # Optional: include basic sub-run list for expandable rows
    sub_runs: list[EtoSubRunListItem] | None = None


# =============================================================================
# GET /eto-runs Response (with pagination)
# =============================================================================

class GetEtoRunsResponse(BaseModel):
    """
    Response for GET /eto-runs with pagination metadata.

    Wraps list of EtoRunListItem with total count and pagination params.
    """
    items: list[EtoRunListItem]
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
    status: EtoMasterStatus
    pdf_file_id: int
    started_at: str | None = None
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
    is_read: bool | None = Field(None, description="Mark run as read (True) or unread (False)")


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
    run_ids: list[int] = Field(..., min_length=1)


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
    new_sub_run_id: int | None = Field(None, description="ID of the newly created sub-run (None if no eligible sub-runs)")
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
    status: EtoMasterStatus
    processing_step: EtoRunProcessingStep | None = None
    started_at: str | None = None  # ISO 8601
    completed_at: str | None = None  # ISO 8601
    error_type: str | None = None
    error_message: str | None = None

    # PDF file info
    pdf: EtoPdfInfo

    # Source (manual or email)
    source: EtoSource = Field(..., discriminator="type")

    # Computed overview stats
    overview: EtoRunOverview

    # Sub-runs with detail (UI filters by status)
    sub_runs: list[EtoSubRunDetail]

    # Page breakdown
    page_statuses: list[PageStatus]
