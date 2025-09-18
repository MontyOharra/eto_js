"""
ETO Processing API Schemas
Request/response models for ETO processing endpoints
"""
from pydantic import BaseModel, Field
from typing import Optional, Dict, Any, List
from datetime import datetime
from api.schemas.common import APIResponse


class EtoRunSummaryResponse(BaseModel):
    """ETO run summary response"""
    id: int
    email_id: int
    pdf_filename: str
    status: str = Field(description="Processing status")
    template_name: Optional[str] = None
    processing_duration_ms: Optional[int] = Field(None, ge=0, description="Processing time in milliseconds")
    created_at: datetime
    completed_at: Optional[datetime] = None
    error_message: Optional[str] = None


class EtoRunDetailResponse(BaseModel):
    """Detailed ETO run response"""
    id: int
    email_id: int
    pdf_file_id: int
    status: str
    processing_step: Optional[str] = None
    
    # Error information
    error_type: Optional[str] = None
    error_message: Optional[str] = None
    error_details: Optional[Dict[str, Any]] = None
    
    # Template matching
    matched_template_id: Optional[int] = None
    template_name: Optional[str] = None
    template_version: Optional[int] = None
    template_match_coverage: Optional[float] = Field(None, ge=0.0, le=1.0)
    unmatched_object_count: Optional[int] = Field(None, ge=0)
    suggested_new_template: bool = False
    
    # Data processing
    extracted_data: Optional[Dict[str, Any]] = None
    transformation_audit: Optional[Dict[str, Any]] = None
    target_data: Optional[Dict[str, Any]] = None
    
    # Execution tracking
    failed_step_id: Optional[int] = None
    step_execution_log: Optional[Dict[str, Any]] = None
    
    # Timing
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    processing_duration_ms: Optional[int] = Field(None, ge=0)
    
    # Order integration
    order_id: Optional[int] = None
    
    # Audit
    created_at: datetime
    updated_at: datetime


class ProcessingStepResultResponse(BaseModel):
    """Processing step result response"""
    step_name: str
    success: bool
    execution_time_ms: int = Field(ge=0)
    input_data: Dict[str, Any]
    output_data: Optional[Dict[str, Any]] = None
    error_message: Optional[str] = None
    error_details: Optional[Dict[str, Any]] = None


class ReprocessEtoRunRequest(BaseModel):
    """Request to reprocess an ETO run"""
    force: bool = Field(False, description="Force reprocessing even if already successful")
    template_id: Optional[int] = Field(None, description="Specific template to use for processing")


class SkipEtoRunRequest(BaseModel):
    """Request to skip an ETO run"""
    reason: str = Field(..., description="Reason for skipping")


class EtoRunStatsResponse(BaseModel):
    """ETO run statistics response"""
    total_runs: int = Field(ge=0)
    successful_runs: int = Field(ge=0)
    failed_runs: int = Field(ge=0)
    skipped_runs: int = Field(ge=0)
    processing_runs: int = Field(ge=0)
    needs_template_runs: int = Field(ge=0)
    success_rate: float = Field(ge=0.0, le=1.0)
    avg_processing_time_ms: int = Field(ge=0)
    last_24h_runs: int = Field(ge=0)
    last_successful_run: Optional[datetime] = None
    last_failed_run: Optional[datetime] = None


class EtoRunListRequest(BaseModel):
    """Request parameters for listing ETO runs"""
    status: Optional[str] = Field(None, description="Filter by status")
    email_id: Optional[int] = Field(None, description="Filter by email ID")
    template_id: Optional[int] = Field(None, description="Filter by template ID")
    date_from: Optional[datetime] = Field(None, description="Filter runs from date")
    date_to: Optional[datetime] = Field(None, description="Filter runs to date")
    has_errors: Optional[bool] = Field(None, description="Filter runs with/without errors")
    page: int = Field(1, ge=1)
    limit: int = Field(20, ge=1, le=100)
    order_by: Optional[str] = Field('created_at', description="Field to order by")
    desc: bool = Field(True, description="Descending order")