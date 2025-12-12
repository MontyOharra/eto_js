"""
ETO Sub-Run Domain Types
Dataclasses representing eto_sub_runs table and related operations

Sub-runs represent page-set business logic units within a parent ETO run.
Each sub-run handles a specific set of pages that matched a template (or no template).
"""
from dataclasses import dataclass
from datetime import datetime
from typing import Literal, Optional, Dict, Any, TypedDict

# Import stage detail view types from eto_runs for reuse
from shared.types.eto_runs import (
    EtoRunExtractionDetailView,
    EtoRunPipelineExecutionDetailView,
)

# =========================
# ETO Sub-Run Types
# =========================

@dataclass
class EtoSubRunCreate:
    """
    Data required to create a new ETO sub-run.

    Sub-runs are created during template matching stage when pages are
    matched to templates (or grouped as unmatched).
    """
    eto_run_id: int
    matched_pages: str  # JSON string like "[1,2,3]"
    template_version_id: Optional[int] = None  # NULL for unmatched pages


class EtoSubRunUpdate(TypedDict, total=False):
    """
    Dict for updating an ETO sub-run.
    All fields are optional - only provided fields will be updated.

    Uses dict keys to distinguish between:
    - Field not provided (key absent) - field will not be updated
    - Field set to None (key present, value None) - field will be cleared/nulled in database
    - Field set to value (key present, value set) - field will be updated to that value

    Example:
        {"status": "success"}  # Only update status
        {"error_type": None}  # Clear error_type
        {"status": "failure", "error_message": "Extraction failed"}  # Update multiple
    """
    status: str
    error_type: str | None
    error_message: str | None
    error_details: str | None
    started_at: datetime | None
    completed_at: datetime | None


@dataclass
class EtoSubRun:
    """
    Complete ETO sub-run record as stored in the database.
    Represents the eto_sub_runs table exactly.

    Each sub-run represents a contiguous set of pages that matched a specific
    template (or no template for unmatched groups).
    """
    id: int
    eto_run_id: int
    matched_pages: str  # JSON string like "[1,2,3]"
    template_version_id: Optional[int]
    status: str
    error_type: Optional[str]
    error_message: Optional[str]
    error_details: Optional[str]
    started_at: Optional[datetime]
    completed_at: Optional[datetime]
    created_at: datetime
    updated_at: datetime


# =========================
# Detail View Types
# =========================

@dataclass
class EtoSubRunDetailView:
    """
    Complete detailed view for a single sub-run with all stage data.

    Used by GET /eto-runs/{id}/sub-runs/{sub_id} endpoint and as part of
    EtoRunDetailView to show all sub-runs.

    This is the new equivalent of the old single-run detailed view,
    but scoped to a specific page set.
    """
    # Core sub-run data
    id: int
    eto_run_id: int
    matched_pages: list[int]  # Parsed from JSON string
    status: str

    # Template info (None for unmatched groups)
    template_id: Optional[int]
    template_name: Optional[str]
    template_version_id: Optional[int]
    template_version_num: Optional[int]

    # PDF info (for the viewer - inherited from parent run)
    pdf_file_id: int
    pdf_original_filename: str
    pdf_file_size: Optional[int]
    pdf_page_count: Optional[int]

    # Optional fields with defaults (must come after required fields)
    template_customer_id: Optional[int] = None  # Customer ID from pdf_templates (for Access DB lookup)

    # Stage data (optional - depends on sub-run progress)
    # Reuses existing stage detail view types from eto_runs
    extraction: Optional[EtoRunExtractionDetailView] = None
    pipeline_execution: Optional[EtoRunPipelineExecutionDetailView] = None

    # Output channel data from pipeline execution (for successful sub-runs)
    # Dict of channel_name -> value, e.g., {"hawb": "12345", "pickup_address": "123 Main St"}
    output_channel_data: Optional[Dict[str, Any]] = None

    # Error tracking (business-level failures)
    error_type: Optional[str] = None
    error_message: Optional[str] = None
    error_details: Optional[str] = None

    # Timestamps
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
