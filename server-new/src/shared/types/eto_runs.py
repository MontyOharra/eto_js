"""
ETO Run Domain Types
Dataclasses representing eto_runs table and related operations
"""
from dataclasses import dataclass
from datetime import datetime
from typing import Literal, Optional

# =========================
# Type Aliases for Enums
# =========================

# Corresponds to EtoRunStatus enum in models.py
EtoRunStatus = Literal["not_started", "processing", "success", "failure", "needs_template", "skipped"]

# Corresponds to EtoRunProcessingStep enum in models.py
EtoProcessingStep = Literal["template_matching", "data_extraction", "data_transformation"]


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


@dataclass
class EtoRunUpdate:
    """
    Data for updating an ETO run.
    All fields are optional - only provided fields will be updated.
    """
    status: Optional[EtoRunStatus] = None
    processing_step: Optional[EtoProcessingStep] = None
    error_type: Optional[str] = None
    error_message: Optional[str] = None
    error_details: Optional[str] = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None


@dataclass
class EtoRun:
    """
    Complete ETO run record as stored in the database.
    Represents the eto_runs table exactly.
    """
    id: int
    pdf_file_id: int
    status: EtoRunStatus
    processing_step: Optional[EtoProcessingStep]
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
    status: EtoRunStatus
    processing_step: Optional[EtoProcessingStep]
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
    run: EtoRun

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
    # Import at runtime to avoid circular imports
    template_matching: Optional[Any] = None  # EtoRunTemplateMatching
    extraction: Optional[Any] = None  # EtoRunExtraction
    pipeline_execution: Optional[Any] = None  # EtoRunPipelineExecution

    # Matched template info (denormalized from template_matching for convenience)
    matched_template_id: Optional[int] = None
    matched_template_name: Optional[str] = None
    matched_template_version_id: Optional[int] = None
    matched_template_version_num: Optional[int] = None
