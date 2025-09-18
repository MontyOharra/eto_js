"""
ETO Processing API Schemas
Request/response models for ETO processing endpoints
"""
from pydantic import BaseModel, Field
from typing import Optional, Dict, Any, List, Literal
from datetime import datetime
from api.schemas.common import APIResponse

# === Core Domain Types ===

EtoRunStatus = Literal["not_started", "processing", "success", "failure", "needs_template", "skipped"]
EtoProcessingStep = Literal["template_matching", "extracting_data", "transforming_data"]
EtoErrorType = Literal["template_matching_error", "data_extraction_error", "transformation_error", "pipeline_error"]

# === ETO Run Management Schemas ===

class EtoRunListRequest(BaseModel):
    """Request parameters for listing ETO runs"""
    status: Optional[EtoRunStatus] = None
    email_id: Optional[int] = None
    template_id: Optional[int] = None
    has_errors: Optional[bool] = None
    date_from: Optional[datetime] = None
    date_to: Optional[datetime] = None
    page: int = Field(1, ge=1, description="Page number")
    limit: int = Field(20, ge=1, le=100, description="Items per page")
    order_by: str = Field("created_at", description="Sort field")
    desc: bool = Field(True, description="Sort descending")


class EtoRunSummary(BaseModel):
    """Summary information for an ETO run"""
    id: int
    email_id: int
    pdf_file_id: int
    status: EtoRunStatus
    processing_step: Optional[EtoProcessingStep] = None

    # Basic metadata
    pdf_filename: str
    email_subject: str
    sender_email: str
    file_size: int

    # Processing info
    matched_template_id: Optional[int] = None
    template_name: Optional[str] = None
    processing_duration_ms: Optional[int] = None
    error_message: Optional[str] = None

    # Timestamps
    created_at: datetime
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None


class EtoRunListResponse(APIResponse):
    """Response for ETO runs listing"""
    data: List[EtoRunSummary] = Field(default_factory=list)
    total: int = 0
    page: int = 1
    limit: int = 20
    total_pages: int = 0


class EtoRunDetail(BaseModel):
    """Detailed information for a specific ETO run"""
    id: int
    email_id: int
    pdf_file_id: int
    status: EtoRunStatus
    processing_step: Optional[EtoProcessingStep] = None

    # Error information
    error_type: Optional[EtoErrorType] = None
    error_message: Optional[str] = None
    error_details: Optional[Dict[str, Any]] = None

    # Template matching results
    matched_template_id: Optional[int] = None
    template_name: Optional[str] = None
    template_version: Optional[int] = None
    template_match_coverage: Optional[float] = Field(None, ge=0.0, le=100.0)

    # Processing results indicators
    has_extracted_data: bool = False
    has_transformation_audit: bool = False
    has_target_data: bool = False

    # Pipeline execution tracking
    failed_step_id: Optional[int] = None
    step_execution_log: Optional[Dict[str, Any]] = None

    # Timestamps
    created_at: datetime
    updated_at: datetime
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    processing_duration_ms: Optional[int] = None

    # Order integration
    order_id: Optional[int] = None


class EtoRunDetailResponse(APIResponse):
    """Response for detailed ETO run information"""
    data: Optional[EtoRunDetail] = None


class ReprocessEtoRunRequest(BaseModel):
    """Request to reprocess an ETO run"""
    force: bool = Field(False, description="Force reprocessing even if successful")
    template_id: Optional[int] = Field(None, description="Assign specific template")
    reset_template: bool = Field(False, description="Clear template assignment")
    reason: Optional[str] = Field(None, description="Reason for reprocessing")


class ReprocessEtoRunResponse(APIResponse):
    """Response for ETO run reprocessing"""
    run_id: int = 0
    old_status: EtoRunStatus = "not_started"
    new_status: EtoRunStatus = "not_started"


class SkipEtoRunRequest(BaseModel):
    """Request to skip an ETO run"""
    reason: str = Field(..., min_length=1, max_length=500, description="Reason for skipping")
    permanent: bool = Field(False, description="Permanently skip or allow future reprocessing")


class SkipEtoRunResponse(APIResponse):
    """Response for skipping an ETO run"""
    run_id: int = 0
    status: EtoRunStatus = "skipped"
    reason: str = ""


class DeleteEtoRunResponse(APIResponse):
    """Response for deleting an ETO run"""
    run_id: int = 0


# === Processing Results & Data Schemas ===

class ExtractionField(BaseModel):
    """Extracted field data"""
    field_id: str
    label: str
    value: Any
    confidence: Optional[float] = Field(None, ge=0.0, le=1.0)
    bounding_box: Optional[List[float]] = None
    page: Optional[int] = None


class EtoRunResults(BaseModel):
    """Extraction and transformation results for an ETO run"""
    run_id: int
    status: EtoRunStatus

    # Template information
    template_id: Optional[int] = None
    template_name: Optional[str] = None

    # Extracted data
    extracted_fields: List[ExtractionField] = []
    raw_extracted_data: Optional[Dict[str, Any]] = None

    # Transformed data
    target_data: Optional[Dict[str, Any]] = None
    transformation_audit: Optional[Dict[str, Any]] = None

    # Processing metadata
    extraction_timestamp: Optional[datetime] = None
    transformation_timestamp: Optional[datetime] = None


class EtoRunResultsResponse(APIResponse):
    """Response for ETO run processing results"""
    data: Optional[EtoRunResults] = None


class PdfObject(BaseModel):
    """PDF object information"""
    type: str
    page: int
    text: str
    x: float
    y: float
    width: float
    height: float
    font_name: Optional[str] = None
    font_size: Optional[float] = None
    bbox: Optional[List[float]] = None


class EtoRunPdfData(BaseModel):
    """PDF file and objects data for an ETO run"""
    run_id: int
    pdf_id: int
    filename: str
    original_filename: str
    file_size: int
    page_count: int
    object_count: int
    sha256_hash: str

    # PDF objects
    pdf_objects: List[PdfObject] = []

    # Email context
    email_subject: str
    sender_email: str
    received_date: datetime


class EtoRunPdfDataResponse(APIResponse):
    """Response for ETO run PDF data"""
    data: Optional[EtoRunPdfData] = None


class ProcessingAuditStep(BaseModel):
    """Individual processing step audit"""
    step: EtoProcessingStep
    status: Literal["started", "completed", "failed"]
    started_at: datetime
    completed_at: Optional[datetime] = None
    duration_ms: Optional[int] = None
    error_message: Optional[str] = None
    details: Optional[Dict[str, Any]] = None


class EtoRunAudit(BaseModel):
    """Processing audit trail for an ETO run"""
    run_id: int
    status: EtoRunStatus

    # Overall processing timeline
    processing_started: Optional[datetime] = None
    processing_completed: Optional[datetime] = None
    total_duration_ms: Optional[int] = None

    # Step-by-step audit
    processing_steps: List[ProcessingAuditStep] = []

    # Error information
    error_type: Optional[EtoErrorType] = None
    error_message: Optional[str] = None
    error_details: Optional[Dict[str, Any]] = None

    # System information
    worker_id: Optional[str] = None
    system_info: Optional[Dict[str, Any]] = None


class EtoRunAuditResponse(APIResponse):
    """Response for ETO run audit trail"""
    data: Optional[EtoRunAudit] = None


# === Template Integration Schemas ===

class TemplateSuggestion(BaseModel):
    """Template suggestion for a failed run"""
    template_id: int
    template_name: str
    customer_name: Optional[str] = None
    match_score: float = Field(..., ge=0.0, le=1.0)
    match_reason: str
    usage_count: int
    success_rate: Optional[float] = Field(None, ge=0.0, le=1.0)


class TemplateSuggestionsResponse(APIResponse):
    """Response for template suggestions"""
    run_id: int = 0
    suggestions: List[TemplateSuggestion] = Field(default_factory=list)


class AssignTemplateRequest(BaseModel):
    """Request to assign template to ETO run"""
    template_id: int
    auto_reprocess: bool = Field(True, description="Automatically reprocess after assignment")
    reason: Optional[str] = Field(None, description="Reason for manual assignment")


class AssignTemplateResponse(APIResponse):
    """Response for template assignment"""
    run_id: int = 0
    template_id: int = 0
    template_name: str = ""
    reprocessing: bool = False


# === Batch Operations Schemas ===

class BulkReprocessRequest(BaseModel):
    """Request for bulk reprocessing of ETO runs"""
    run_ids: List[int] = Field(..., min_items=1, max_items=100)
    force: bool = Field(False, description="Force reprocessing successful runs")
    template_id: Optional[int] = Field(None, description="Assign template to all runs")
    reason: Optional[str] = Field(None, description="Reason for bulk reprocessing")


class BulkReprocessResult(BaseModel):
    """Result for a single run in bulk operation"""
    run_id: int
    success: bool
    old_status: EtoRunStatus
    new_status: Optional[EtoRunStatus] = None
    error: Optional[str] = None


class BulkReprocessResponse(APIResponse):
    """Response for bulk reprocessing"""
    total_requested: int = 0
    successful: int = 0
    failed: int = 0
    results: List[BulkReprocessResult] = Field(default_factory=list)


class StatusCount(BaseModel):
    """Count for a specific status"""
    status: EtoRunStatus
    count: int


class EtoRunsSummary(BaseModel):
    """Summary of ETO runs by status"""
    total_runs: int
    status_counts: List[StatusCount]

    # Recent activity
    last_24h_runs: int
    last_successful_run: Optional[datetime] = None
    last_failed_run: Optional[datetime] = None

    # Performance metrics
    average_processing_time_ms: Optional[int] = None
    success_rate: float = Field(..., ge=0.0, le=1.0)


class EtoRunsSummaryResponse(APIResponse):
    """Response for ETO runs summary"""
    data: Optional[EtoRunsSummary] = None


# === Statistics Schemas ===

class ProcessingStatistics(BaseModel):
    """Detailed processing statistics"""
    total_runs: int
    successful_runs: int
    failed_runs: int
    skipped_runs: int
    processing_runs: int
    needs_template_runs: int

    # Performance metrics
    success_rate: float = Field(..., ge=0.0, le=1.0)
    avg_processing_time_ms: Optional[int] = None
    median_processing_time_ms: Optional[int] = None

    # Time-based metrics
    last_24h_runs: int
    last_7d_runs: int
    last_30d_runs: int

    # Error analysis
    most_common_errors: List[Dict[str, Any]] = []
    template_coverage: float = Field(..., ge=0.0, le=1.0)

    # Recent activity
    last_successful_run: Optional[datetime] = None
    last_failed_run: Optional[datetime] = None
    last_processed_run: Optional[datetime] = None


class EtoStatisticsResponse(APIResponse):
    """Response for ETO processing statistics"""
    data: Optional[ProcessingStatistics] = None