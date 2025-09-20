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
EtoErrorType = Literal["template_matching_error", "data_extraction_error", "transformation_error", "critical_error"]

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
    processing_step: Optional[EtoProcessingStep]

    # Error tracking
    error_type: Optional[EtoErrorType]
    error_message: Optional[str]
    error_details: Optional[str]  # JSON string

    # Template matching results
    matched_template_id: Optional[int]
    matched_template_version: Optional[int]

    # Data extraction and transformation results
    extracted_data: Optional[str]  # JSON string
    transformation_audit: Optional[str]  # JSON string
    target_data: Optional[str]  # JSON string

    # Pipeline execution tracking
    failed_pipeline_step_id: Optional[int]
    step_execution_log: Optional[str]  # JSON string

    # Processing timeline
    started_at: Optional[datetime]
    completed_at: Optional[datetime]
    processing_duration_ms: Optional[int]

    # Order integration
    order_id: Optional[int]