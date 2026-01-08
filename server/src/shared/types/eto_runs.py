"""
ETO Run Domain Types
Pydantic models representing eto_runs table and related operations
"""
from datetime import datetime
from typing import TYPE_CHECKING, Any, Literal

from pydantic import BaseModel, ConfigDict

if TYPE_CHECKING:
    from shared.types.eto_sub_runs import EtoSubRunDetailView


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
    source_type: Literal['email', 'manual']
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
    source_type: str
    source_email_id: int | None
    status: str
    processing_step: str | None
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
    source_type: str
    source_email_id: int | None
    status: str
    processing_step: str | None
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
# Detail View Stage Types
# =========================
# NOTE: These stage types are now used within EtoSubRunDetailView
# rather than directly in EtoRunDetailView

class EtoRunExtractionDetailView(BaseModel):
    """
    Data extraction stage with parsed extracted_data JSON.

    Used in EtoSubRunDetailView to provide extracted field values.

    extracted_data format:
    [
        {
            "name": "field_name",
            "description": "field description",
            "bbox": [x1, y1, x2, y2],
            "page": 1,
            "extracted_value": "the extracted text"
        },
        ...
    ]
    """
    model_config = ConfigDict(frozen=True)

    # From EtoRunExtraction
    status: Literal["processing", "success", "failure"]
    started_at: datetime | None
    completed_at: datetime | None

    # Parsed from extracted_data JSON string field (repository handles deserialization)
    extracted_data: list[dict[str, Any]] | None = None


class EtoRunPipelineExecutionStepDetailView(BaseModel):
    """Individual step in pipeline execution with inputs/outputs"""
    model_config = ConfigDict(frozen=True)

    id: int
    step_number: int
    module_instance_id: str
    inputs: dict[str, dict[str, Any]] | None
    outputs: dict[str, dict[str, Any]] | None
    error: dict[str, Any] | None


class EtoRunPipelineExecutionDetailView(BaseModel):
    """
    Pipeline execution stage with execution steps.

    Used in EtoRunDetailView to provide pipeline execution results and visualization data.
    """
    model_config = ConfigDict(frozen=True)

    # From EtoRunPipelineExecution
    status: Literal["processing", "success", "failure"]
    started_at: datetime | None
    completed_at: datetime | None

    # Pipeline definition ID from matched template version
    pipeline_definition_id: int | None = None

    # Execution steps for pipeline visualization
    steps: list[EtoRunPipelineExecutionStepDetailView] | None = None


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
    source_type: str
    source_email_id: int | None
    status: str
    processing_step: str | None
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
    sub_runs: list['EtoSubRunDetailView']

    # Timestamps
    created_at: datetime
    updated_at: datetime
