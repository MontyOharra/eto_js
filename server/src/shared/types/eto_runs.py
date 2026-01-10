"""
ETO Run Domain Types
Pydantic models representing eto_runs table and related operations
"""
from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict


# =========================
# Status Types
# =========================

EtoSourceType = Literal["email", "manual"]
EtoMasterStatus = Literal["not_started", "processing", "success", "failure", "skipped"]
EtoRunProcessingStep = Literal["template_matching", "sub_runs"]
EtoStepStatus = Literal["processing", "success", "failure"]
EtoOutputStatus = Literal["pending", "processing", "success", "error", "manual_review"]


# =========================
# ETO Run Types
# =========================

class EtoRunCreate(BaseModel):
    """
    Data required to create a new ETO run.
    All other fields are set to defaults by the database.

    source_type: 'email' for email ingestion, 'manual' for manual uploads
    source_email_id: Required if source_type='email', None if source_type='manual'
    """
    model_config = ConfigDict(frozen=True)

    pdf_file_id: int
    source_type: EtoSourceType
    source_email_id: int | None = None


class EtoRunUpdate(BaseModel):
    """
    Data for updating an ETO run.

    Uses Pydantic's model_fields_set to distinguish between:
    - Field not provided: not in model_fields_set (don't update)
    - Field set to None: in model_fields_set with None value (set NULL)
    - Field set to value: in model_fields_set with value (update)
    """
    status: str | None = None
    processing_step: str | None = None
    is_read: bool | None = None
    error_type: str | None = None
    error_message: str | None = None
    error_details: str | None = None
    started_at: datetime | None = None
    completed_at: datetime | None = None
    last_processed_at: datetime | None = None


class EtoRun(BaseModel):
    """
    Complete ETO run record as stored in the database.
    Represents the eto_runs table exactly.
    """
    model_config = ConfigDict(frozen=True)

    id: int
    pdf_file_id: int
    source_type: EtoSourceType
    source_email_id: int | None
    status: EtoMasterStatus
    processing_step: EtoRunProcessingStep | None
    is_read: bool
    error_type: str | None
    error_message: str | None
    error_details: str | None
    started_at: datetime | None
    completed_at: datetime | None
    last_processed_at: datetime | None
    created_at: datetime
    updated_at: datetime


class EtoRunListView(BaseModel):
    """
    ETO run with all joined data for API list view.

    This is a flattened view combining data from:
    - eto_runs table (core fields + source tracking)
    - pdf_files table (PDF info)
    - emails table (source info, if email-sourced)
    - eto_sub_runs table (aggregated sub-run data)

    Used by repository's get_all_with_relations() method.
    Powers the GET /api/eto-runs list endpoint.
    """
    model_config = ConfigDict(frozen=True)

    # Core ETO run fields
    id: int
    source_type: EtoSourceType
    source_email_id: int | None
    status: EtoMasterStatus
    processing_step: EtoRunProcessingStep | None
    is_read: bool
    started_at: datetime | None
    completed_at: datetime | None
    error_type: str | None
    error_message: str | None

    # PDF file info
    pdf_file_id: int
    pdf_original_filename: str
    pdf_file_size: int | None
    pdf_page_count: int

    # Source info (email fields - all None if manual upload)
    email_id: int | None
    email_sender_email: str | None
    email_received_date: datetime | None
    email_subject: str | None
    email_folder_name: str | None

    # Sub-run status counts (aggregated from eto_sub_runs)
    sub_run_success_count: int
    sub_run_failure_count: int
    sub_run_needs_template_count: int
    sub_run_skipped_count: int

    # Page arrays - actual page numbers (aggregated from eto_sub_runs)
    pages_matched: list[int]      # Pages with template matches
    pages_unmatched: list[int]    # Pages with no match (needs_template)
    pages_skipped: list[int]      # Pages manually skipped

    # Timestamps
    created_at: datetime
    updated_at: datetime
    last_processed_at: datetime | None  # Stable timestamp for sorting - only updated on terminal state


# =========================
# Detail View
# =========================

# Import here to avoid circular dependency - eto_sub_runs imports EtoStepStatus from this file
from shared.types.eto_sub_runs import EtoSubRunDetailView  # noqa: E402


class EtoRunDetailView(BaseModel):
    """
    Complete detailed view for a single ETO run with all sub-run data.

    Used by GET /eto-runs/{id} endpoint to return full run details including:
    - Core run data (with source tracking)
    - PDF file info
    - Email source info (if applicable)
    - List of all sub-runs (each with their template, extraction, and pipeline data)

    Composed in service layer by fetching run + all sub-runs with their stages.
    Powers the GET /api/eto-runs/{id} detail endpoint.
    """
    model_config = ConfigDict(frozen=True)

    # Core run data
    id: int
    source_type: EtoSourceType
    source_email_id: int | None
    status: EtoMasterStatus
    processing_step: EtoRunProcessingStep | None
    is_read: bool
    started_at: datetime | None
    completed_at: datetime | None
    error_type: str | None
    error_message: str | None
    error_details: str | None

    # PDF file info (always present)
    pdf_file_id: int
    pdf_original_filename: str
    pdf_file_size: int | None
    pdf_page_count: int | None

    # Source info (email fields - all None if manual upload)
    email_id: int | None
    email_sender_email: str | None
    email_received_date: datetime | None
    email_subject: str | None
    email_folder_name: str | None

    # Sub-runs (list of all sub-runs for this PDF)
    # Will be split into matchedSubRuns, needsTemplateSubRuns, skippedSubRuns by API mapper
    sub_runs: list[EtoSubRunDetailView]

    # Timestamps
    created_at: datetime
    updated_at: datetime
