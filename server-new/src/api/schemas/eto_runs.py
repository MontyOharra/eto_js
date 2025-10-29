"""
ETO Runs API Schemas
Pydantic models for ETO run endpoints
"""
from typing import Optional, List, Dict, Any, Literal, Union
from pydantic import BaseModel, Field, ConfigDict

# =============================================================================
# Type Aliases
# =============================================================================

EtoRunStatus = Literal["not_started", "processing", "success", "failure", "needs_template", "skipped"]
EtoProcessingStep = Literal["template_matching", "data_extraction", "data_transformation"]

# =============================================================================
# Nested Models for EtoRunListItem
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
# ETO Run List Item (for GET /eto-runs)
# =============================================================================

class EtoRunListItem(BaseModel):
    """
    Single ETO run item for list view.

    Used in GET /eto-runs response (wrapped in pagination).
    Includes core run data plus embedded related data (PDF, source, matched template).
    """
    id: int
    status: EtoRunStatus
    processing_step: Optional[EtoProcessingStep] = None
    started_at: Optional[str] = None  # ISO 8601
    completed_at: Optional[str] = None  # ISO 8601
    error_type: Optional[str] = None
    error_message: Optional[str] = None

    # Embedded related data (not just foreign keys)
    pdf: EtoPdfInfo
    source: EtoSource = Field(..., discriminator="type")
    matched_template: Optional[EtoMatchedTemplate] = None


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
    status: EtoRunStatus
    pdf_file_id: int
    started_at: Optional[str] = None  # Will be None for not_started runs
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
# TODO: Additional schemas to be defined
# =============================================================================
# - EtoRunDetail (GET /eto-runs/{id} response)
# - PostEtoRunUploadResponse (POST /eto-runs response)
#
# Stage types:
# - EtoStageTemplateMatching
# - EtoStageDataExtraction
# - EtoStagePipelineExecution
# - EtoPipelineExecutionStep
#
