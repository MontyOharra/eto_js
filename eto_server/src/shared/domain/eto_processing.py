"""
ETO Processing Domain Types
Domain objects for ETO processing and config management
"""
from dataclasses import dataclass
from typing import Optional, Dict, Any, List, Literal
from datetime import datetime


# Type definitions for valid string values
EtoRunStatus = Literal["not_started", "processing", "success", "failure", "needs_template", "skipped"]
EtoProcessingStep = Literal["template_matching", "extracting_data", "transforming_data"]
EtoErrorType = Literal["template_matching_error", "data_extraction_error", "transformation_error", "pipeline_error"]

@dataclass
class EtoRun:
    """ETO processing run domain object"""
    id: int
    email_id: int
    pdf_file_id: int
    status: EtoRunStatus
    created_at: datetime
    updated_at: datetime

    # Processing tracking
    processing_step: Optional[EtoProcessingStep] = None

    # Error tracking
    error_type: Optional[EtoErrorType] = None
    error_message: Optional[str] = None
    error_details: Optional[str] = None  # JSON string

    # Template matching results
    matched_template_id: Optional[int] = None
    template_version: Optional[int] = None
    template_match_coverage: Optional[float] = None
    unmatched_object_count: Optional[int] = None

    # Data extraction and transformation results
    extracted_data: Optional[str] = None  # JSON string
    transformation_audit: Optional[str] = None  # JSON string
    target_data: Optional[str] = None  # JSON string

    # Pipeline execution tracking
    failed_step_id: Optional[int] = None
    step_execution_log: Optional[str] = None  # JSON string

    # Processing timeline
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    processing_duration_ms: Optional[int] = None

    # Order integration
    order_id: Optional[int] = None

