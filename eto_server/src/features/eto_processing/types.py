"""
ETO Processing Domain Types
Domain objects for Email-to-Order processing workflow
"""
from dataclasses import dataclass
from typing import Optional, Dict, Any, List
from datetime import datetime


@dataclass
class EtoRun:
    """ETO processing run domain object"""
    id: int
    email_id: int
    pdf_file_id: int
    status: str  # 'not_started', 'processing', 'success', 'failure', 'needs_template', 'skipped'
    created_at: datetime
    updated_at: datetime

    # Processing tracking
    processing_step: Optional[str] = None  # 'template_matching', 'extracting_data', 'transforming_data'

    # Error tracking
    error_type: Optional[str] = None  # 'template_matching_error', 'data_extraction_error', 'transformation_error'
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

