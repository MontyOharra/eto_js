"""
ETO Run Domain Types
Dataclasses representing eto_runs table and related operations
"""
from dataclasses import dataclass
from datetime import datetime
from typing import Literal, Optional, Dict, Any, TypedDict

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
    - eto_run_template_matchings (template matching result)
    - pdf_template_versions (matched template version)
    - pdf_templates (template details)

    Used by repository's get_all_with_relations() method.
    """
    # Core ETO run fields
    id: int
    status: str
    processing_step: Optional[str]
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

    # Matched template info (all None if no successful match)
    template_id: Optional[int]
    template_name: Optional[str]
    template_version_id: Optional[int]
    template_version_num: Optional[int]


# =========================
# Detail View Stage Types
# =========================

@dataclass
class EtoRunTemplateMatchingDetailView:
    """
    Template matching stage with denormalized template info.
    Combines EtoRunTemplateMatching with template name/version data.

    Used in EtoRunDetailView to provide full template matching context.
    """
    # From EtoRunTemplateMatching
    status: Literal["processing", "success", "failure"]
    matched_template_version_id: Optional[int]
    started_at: Optional[datetime]
    completed_at: Optional[datetime]

    # Denormalized from joined template data
    matched_template_name: Optional[str] = None
    matched_version_number: Optional[int] = None


@dataclass
class EtoRunExtractionDetailView:
    """
    Data extraction stage with parsed extracted_data JSON.
    Extends EtoRunExtraction by parsing JSON string to dict.

    Used in EtoRunDetailView to provide extracted field values.
    """
    # From EtoRunExtraction
    status: Literal["processing", "success", "failure"]
    started_at: Optional[datetime]
    completed_at: Optional[datetime]

    # Parsed from extracted_data JSON string field
    extracted_data: Optional[Dict[str, Any]] = None


@dataclass
class EtoRunPipelineExecutionDetailView:
    """
    Pipeline execution stage with parsed executed_actions JSON.

    Used in EtoRunDetailView to provide pipeline execution results.
    Note: Step-by-step trace can be fetched separately if needed.
    """
    # From EtoRunPipelineExecution
    status: Literal["processing", "success", "failure"]
    started_at: Optional[datetime]
    completed_at: Optional[datetime]

    # Parsed from executed_actions JSON string field
    executed_actions: Optional[Dict[str, Any]] = None


@dataclass
class EtoRunDetailView:
    """
    Complete detailed view for a single ETO run with all stage data.

    Used by GET /eto-runs/{id} endpoint to return full run details including:
    - Core run data
    - PDF file info
    - Email source info (if applicable)
    - Stage 1: Template matching data
    - Stage 2: Data extraction data
    - Stage 3: Pipeline execution data

    Composed in service layer by fetching run + all related records.
    """
    # Core run data
    id: int
    status: str
    processing_step: Optional[str]
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

    # Stage data (optional - depends on run progress)
    template_matching: Optional[EtoRunTemplateMatchingDetailView] = None
    extraction: Optional[EtoRunExtractionDetailView] = None
    pipeline_execution: Optional[EtoRunPipelineExecutionDetailView] = None

    # Matched template info (denormalized from template_matching for convenience)
    matched_template_id: Optional[int] = None
    matched_template_name: Optional[str] = None
    matched_template_version_id: Optional[int] = None
    matched_template_version_num: Optional[int] = None
