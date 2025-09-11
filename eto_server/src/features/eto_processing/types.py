"""
ETO Processing Domain Types  
Domain objects for Email-to-Order processing workflow
"""
from dataclasses import dataclass
from typing import Optional, Dict, Any, List
from datetime import datetime
from ...shared.types.common import ProcessingStatus, OptionalString


@dataclass
class ExtractionStep:
    """Individual step within extraction rules"""
    id: Optional[int]
    step_number: int
    step_name: str
    step_type: str  # 'raw_extract', 'sql_lookup', 'llm_parse'
    step_config: Dict[str, Any]
    input_fields: List[str]
    output_field: str
    error_handling: str = 'fail_rule'
    default_value: Optional[str] = None
    avg_execution_time_ms: int = 0
    execution_count: int = 0
    last_executed_at: Optional[datetime] = None


@dataclass
class ExtractionRule:
    """Extraction rules for templates (multi-step data transformation)"""
    id: Optional[int]
    template_id: int
    rule_name: str
    final_target_field: str
    is_required: bool = True
    extraction_steps: List[ExtractionStep]
    created_at: datetime


@dataclass
class EtoRun:
    """ETO processing run domain object"""
    id: Optional[int]
    email_id: int
    pdf_file_id: int
    
    # Overall processing status
    status: ProcessingStatus
    
    # Current processing step (only when status=PROCESSING)
    processing_step: Optional[str] = None
    
    # Error tracking (for status=FAILURE)
    error_type: Optional[str] = None
    error_message: Optional[str] = None
    error_details: Optional[Dict[str, Any]] = None
    
    # Template matching results
    matched_template_id: Optional[int] = None
    template_version: Optional[int] = None
    template_match_coverage: Optional[float] = None
    unmatched_object_count: Optional[int] = None
    suggested_new_template: bool = False
    
    # Data extraction results
    extracted_data: Optional[Dict[str, Any]] = None
    
    # Data transformation audit trail
    transformation_audit: Optional[Dict[str, Any]] = None
    
    # Final transformed data
    target_data: Optional[Dict[str, Any]] = None
    
    # Pipeline execution tracking
    failed_step_id: Optional[int] = None
    step_execution_log: Optional[Dict[str, Any]] = None
    
    # Processing timeline
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    processing_duration_ms: Optional[int] = None
    
    # Order integration
    order_id: Optional[int] = None
    
    # Audit
    created_at: datetime
    updated_at: datetime


@dataclass
class ProcessingStepResult:
    """Result of a single processing step"""
    step_name: str
    success: bool
    execution_time_ms: int
    input_data: Dict[str, Any]
    output_data: Optional[Dict[str, Any]] = None
    error_message: Optional[str] = None
    error_details: Optional[Dict[str, Any]] = None


@dataclass
class EtoRunSummary:
    """Summary information for ETO runs"""
    id: int
    email_id: int
    pdf_filename: str
    status: ProcessingStatus
    template_name: Optional[str]
    processing_duration_ms: Optional[int]
    created_at: datetime
    completed_at: Optional[datetime]
    error_message: Optional[str]