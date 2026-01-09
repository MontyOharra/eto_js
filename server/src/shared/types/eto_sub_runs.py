"""
ETO Sub-Run Domain Types
Pydantic models representing eto_sub_runs table and related operations

Sub-runs represent page-set business logic units within a parent ETO run.
Each sub-run handles a specific set of pages that matched a template (or no template).
"""
from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict

# Import stage detail view types from eto_runs for reuse
from shared.types.eto_runs import (
    EtoRunExtractionDetailView,
    EtoRunPipelineExecutionDetailView,
)


# =========================
# Status Types
# =========================

EtoSubRunStatus = Literal[
    "not_started", "matched", "processing", "success", "failure", "needs_template", "skipped"
]


# =========================
# ETO Sub-Run Types
# =========================

class EtoSubRunCreate(BaseModel):
    """
    Data required to create a new ETO sub-run.

    Sub-runs are created during template matching stage when pages are
    matched to templates (or grouped as unmatched).
    """
    model_config = ConfigDict(frozen=True)

    eto_run_id: int
    matched_pages: str  # JSON string like "[1,2,3]"
    template_version_id: int | None = None  # NULL for unmatched pages


class EtoSubRunUpdate(BaseModel):
    """
    Data for updating an ETO sub-run.

    Uses Pydantic's model_fields_set to distinguish between:
    - Field not provided: not in model_fields_set (don't update)
    - Field set to None: in model_fields_set with None value (set NULL)
    - Field set to value: in model_fields_set with value (update)
    """
    status: str | None = None
    error_type: str | None = None
    error_message: str | None = None
    error_details: str | None = None
    started_at: datetime | None = None
    completed_at: datetime | None = None


class EtoSubRun(BaseModel):
    """
    Complete ETO sub-run record as stored in the database.
    Represents the eto_sub_runs table exactly.

    Each sub-run represents a contiguous set of pages that matched a specific
    template (or no template for unmatched groups).
    """
    model_config = ConfigDict(frozen=True)

    id: int
    eto_run_id: int
    matched_pages: str  # JSON string like "[1,2,3]"
    template_version_id: int | None
    status: EtoSubRunStatus
    error_type: str | None
    error_message: str | None
    error_details: str | None
    started_at: datetime | None
    completed_at: datetime | None
    created_at: datetime
    updated_at: datetime


# =========================
# Detail View Types
# =========================

class EtoSubRunDetailView(BaseModel):
    """
    Complete detailed view for a single sub-run with all stage data.

    Used by GET /eto-runs/{id}/sub-runs/{sub_id} endpoint and as part of
    EtoRunDetailView to show all sub-runs.

    This is the new equivalent of the old single-run detailed view,
    but scoped to a specific page set.
    """
    model_config = ConfigDict(frozen=True)

    # Core sub-run data
    id: int
    eto_run_id: int
    matched_pages: list[int]  # Parsed from JSON string
    status: EtoSubRunStatus

    # Template info (None for unmatched groups)
    template_id: int | None
    template_name: str | None
    template_version_id: int | None
    template_version_num: int | None

    # PDF info (for the viewer - inherited from parent run)
    pdf_file_id: int
    pdf_original_filename: str
    pdf_file_size: int | None
    pdf_page_count: int | None

    # Optional fields with defaults (must come after required fields)
    template_customer_id: int | None = None  # Customer ID from pdf_templates (for Access DB lookup)

    # Stage data (optional - depends on sub-run progress)
    # Reuses existing stage detail view types from eto_runs
    extraction: EtoRunExtractionDetailView | None = None
    pipeline_execution: EtoRunPipelineExecutionDetailView | None = None

    # Output channel data from pipeline execution (for successful sub-runs)
    # Dict of channel_name -> value, e.g., {"hawb": "12345", "pickup_address": "123 Main St"}
    output_channel_data: dict[str, Any] | None = None

    # Error tracking (business-level failures)
    error_type: str | None = None
    error_message: str | None = None
    error_details: str | None = None

    # Timestamps
    started_at: datetime | None = None
    completed_at: datetime | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None
