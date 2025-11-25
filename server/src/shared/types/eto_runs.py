"""
ETO Run Domain Types
Dataclasses representing eto_runs table and related operations
"""
from dataclasses import dataclass
from datetime import datetime
from typing import Literal, Optional, Dict, List, Any, TypedDict, TYPE_CHECKING

if TYPE_CHECKING:
    from shared.types.eto_sub_runs import EtoSubRunDetailView

# =========================
# Type Aliases for Enums
# =========================

# =========================
# ETO Run Types
# =========================

@dataclass
class EtoRunCreate:
    """
    Data required to create a new ETO run.
    All other fields are set to defaults by the database.
    """
    pdf_file_id: int


class EtoRunUpdate(TypedDict, total=False):
    """
    Dict for updating an ETO run.
    All fields are optional - only provided fields will be updated.

    Uses dict keys to distinguish between:
    - Field not provided (key absent) - field will not be updated
    - Field set to None (key present, value None) - field will be cleared/nulled in database
    - Field set to value (key present, value set) - field will be updated to that value

    Example:
        {"status": "success"}  # Only update status
        {"processing_step": None}  # Clear processing_step
        {"status": "failure", "error_type": "ValidationError"}  # Update multiple
    """
    status: str
    processing_step: str | None
    is_read: bool
    error_type: str | None
    error_message: str | None
    error_details: str | None
    started_at: datetime | None
    completed_at: datetime | None


@dataclass
class EtoRun:
    """
    Complete ETO run record as stored in the database.
    Represents the eto_runs table exactly.
    """
    id: int
    pdf_file_id: int
    status: str
    processing_step: Optional[str]
    is_read: bool
    error_type: Optional[str]
    error_message: Optional[str]
    error_details: Optional[str]
    started_at: Optional[datetime]
    completed_at: Optional[datetime]
    created_at: datetime
    updated_at: datetime


@dataclass
class EtoRunListView:
    """
    ETO run with all joined data for API list view.

    This is a flattened view combining data from:
    - eto_runs table (core fields)
    - pdf_files table (PDF info)
    - emails table (source info, if email-sourced)
    - eto_sub_runs table (aggregated sub-run data)

    Used by repository's get_all_with_relations() method.
    Powers the GET /api/eto-runs list endpoint.
    """
    # Core ETO run fields
    id: int
    status: str
    processing_step: Optional[str]
    is_read: bool
    started_at: Optional[datetime]
    completed_at: Optional[datetime]
    error_type: Optional[str]
    error_message: Optional[str]

    # PDF file info
    pdf_file_id: int
    pdf_original_filename: str
    pdf_file_size: Optional[int]
    pdf_page_count: Optional[int]

    # Source info (email fields - all None if manual upload)
    email_id: Optional[int]
    email_sender_email: Optional[str]
    email_received_date: Optional[datetime]
    email_subject: Optional[str]
    email_folder_name: Optional[str]

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


# =========================
# Detail View Stage Types
# =========================
# NOTE: These stage types are now used within EtoSubRunDetailView
# rather than directly in EtoRunDetailView

@dataclass
class EtoRunExtractionDetailView:
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
    # From EtoRunExtraction
    status: Literal["processing", "success", "failure"]
    started_at: Optional[datetime]
    completed_at: Optional[datetime]

    # Parsed from extracted_data JSON string field (repository handles deserialization)
    extracted_data: Optional[List[Dict[str, Any]]] = None


@dataclass
class EtoRunPipelineExecutionStepDetailView:
    """Individual step in pipeline execution with inputs/outputs"""
    id: int
    step_number: int
    module_instance_id: str
    inputs: Optional[Dict[str, Dict[str, Any]]]
    outputs: Optional[Dict[str, Dict[str, Any]]]
    error: Optional[Dict[str, Any]]


@dataclass
class EtoRunPipelineExecutionDetailView:
    """
    Pipeline execution stage with parsed executed_actions JSON and execution steps.

    Used in EtoRunDetailView to provide pipeline execution results and visualization data.
    """
    # From EtoRunPipelineExecution
    status: Literal["processing", "success", "failure"]
    started_at: Optional[datetime]
    completed_at: Optional[datetime]

    # Parsed from executed_actions JSON string field
    executed_actions: Optional[Dict[str, Any]] = None

    # Pipeline definition ID from matched template version
    pipeline_definition_id: Optional[int] = None

    # Execution steps for pipeline visualization
    steps: Optional[list[EtoRunPipelineExecutionStepDetailView]] = None


@dataclass
class EtoRunDetailView:
    """
    Complete detailed view for a single ETO run with all sub-run data.

    Used by GET /eto-runs/{id} endpoint to return full run details including:
    - Core run data
    - PDF file info
    - Email source info (if applicable)
    - List of all sub-runs (each with their template, extraction, and pipeline data)

    Composed in service layer by fetching run + all sub-runs with their stages.
    Powers the GET /api/eto-runs/{id} detail endpoint.
    """
    # Core run data
    id: int
    status: str
    processing_step: Optional[str]
    is_read: bool
    started_at: Optional[datetime]
    completed_at: Optional[datetime]
    error_type: Optional[str]
    error_message: Optional[str]
    error_details: Optional[str]

    # PDF file info (always present)
    pdf_file_id: int
    pdf_original_filename: str
    pdf_file_size: Optional[int]
    pdf_page_count: Optional[int]

    # Source info (email fields - all None if manual upload)
    email_id: Optional[int]
    email_sender_email: Optional[str]
    email_received_date: Optional[datetime]
    email_subject: Optional[str]
    email_folder_name: Optional[str]

    # Sub-runs (list of all sub-runs for this PDF)
    # Will be split into matchedSubRuns, needsTemplateSubRuns, skippedSubRuns by API mapper
    sub_runs: list['EtoSubRunDetailView']

    # Timestamps
    created_at: datetime
    updated_at: datetime
