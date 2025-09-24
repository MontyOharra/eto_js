"""
ETO Processing Domain Models
Comprehensive models for the ETO (Extract, Transform, Order) processing pipeline
"""
from typing import Optional, List, Dict, Any, Union
from datetime import datetime
from enum import Enum
from pydantic import BaseModel, Field, field_validator
import json

from shared.utils import DateTimeUtils


# ========== Enums for Type Safety ==========

class EtoRunStatus(str, Enum):
    """ETO run status states"""
    NOT_STARTED = "not_started"      # Initial state - no processing has begun
    PROCESSING = "processing"        # Currently being processed
    SUCCESS = "success"              # Successfully completed end-to-end
    FAILURE = "failure"              # Failed at some point - see error fields
    NEEDS_TEMPLATE = "needs_template" # Template matching failed - needs new template
    SKIPPED = "skipped"              # Intentionally skipped (e.g., duplicate, filtered out)


class EtoProcessingStep(str, Enum):
    """Current step when status=processing"""
    TEMPLATE_MATCHING = "template_matching"    # Finding matching template
    EXTRACTING_DATA = "extracting_data"        # Extracting field values
    TRANSFORMING_DATA = "transforming_data"    # Running transformation pipeline


class EtoErrorType(str, Enum):
    """Error categorization for failures"""
    TEMPLATE_MATCHING_ERROR = "template_matching_error"    # No template found/matched
    DATA_EXTRACTION_ERROR = "data_extraction_error"       # Field extraction failed
    TRANSFORMATION_ERROR = "transformation_error"         # Pipeline transformation failed
    VALIDATION_ERROR = "validation_error"                 # Data validation failed
    SYSTEM_ERROR = "system_error"                        # Infrastructure/unexpected errors


# ========== Base Models ==========

class EtoRunBase(BaseModel):
    """Base ETO fields required for creation"""
    pdf_file_id: int = Field(..., description="Associated PDF file ID (required)")

    def model_dump_for_db(self) -> Dict[str, Any]:
        """Convert model to dict for database insertion"""
        return self.model_dump(exclude_unset=True)


class EtoRunCreate(EtoRunBase):
    """Model for creating new ETO runs - only requires pdf_file_id"""
    # All database fields have defaults, so no additional fields needed
    pass


# ========== Processing State Models ==========

class EtoProcessingState(BaseModel):
    """Current processing state information"""
    status: EtoRunStatus = Field(..., description="Current processing status")
    processing_step: Optional[EtoProcessingStep] = Field(None, description="Current step when processing")

    # Timeline tracking
    started_at: Optional[datetime] = Field(None, description="When processing started")
    completed_at: Optional[datetime] = Field(None, description="When processing completed")
    processing_duration_ms: Optional[int] = Field(None, description="Total processing duration in milliseconds")

    @field_validator('started_at', 'completed_at', mode='before')
    @classmethod
    def ensure_timezone_aware(cls, v):
        """Ensure datetime fields are timezone-aware"""
        return DateTimeUtils.ensure_utc_aware(v)


class EtoErrorInfo(BaseModel):
    """Error information for failed runs"""
    error_type: Optional[EtoErrorType] = Field(None, description="Category of error")
    error_message: Optional[str] = Field(None, description="Human-readable error message")
    error_details: Optional[Dict[str, Any]] = Field(None, description="Detailed error information")
    failed_pipeline_step_id: Optional[int] = Field(None, description="ID of pipeline step that failed")

    class Config:
        # Allow arbitrary types for error_details
        arbitrary_types_allowed = True


class EtoTemplateMatchingResult(BaseModel):
    """Template matching results"""
    matched_template_id: Optional[int] = Field(None, description="ID of matched template")
    matched_template_version: Optional[int] = Field(None, description="Version of matched template")

    def has_match(self) -> bool:
        """Check if template matching was successful"""
        return self.matched_template_id is not None and self.matched_template_version is not None


class EtoDataExtractionResult(BaseModel):
    """Data extraction results from template"""
    extracted_data: Optional[Dict[str, Any]] = Field(None, description="Raw extracted field values")

    def has_extracted_data(self) -> bool:
        """Check if data extraction was successful"""
        return self.extracted_data is not None and len(self.extracted_data) > 0

    class Config:
        arbitrary_types_allowed = True


class EtoTransformationResult(BaseModel):
    """Data transformation pipeline results"""
    transformation_audit: Optional[Dict[str, Any]] = Field(None, description="Step-by-step transformation audit trail")
    target_data: Optional[Dict[str, Any]] = Field(None, description="Final transformed data ready for order creation")
    step_execution_log: Optional[Dict[str, Any]] = Field(None, description="Detailed pipeline execution log")

    def has_transformed_data(self) -> bool:
        """Check if transformation was successful"""
        return self.target_data is not None and len(self.target_data) > 0

    class Config:
        arbitrary_types_allowed = True


class EtoOrderIntegration(BaseModel):
    """Order integration information"""
    order_id: Optional[int] = Field(None, description="Created order ID after successful processing")

    def has_order(self) -> bool:
        """Check if order was created"""
        return self.order_id is not None


# ========== Complete Domain Model ==========

class EtoRun(EtoRunBase):
    """Complete ETO run domain model with all database fields"""

    # ========== Core Identity ==========
    id: int = Field(..., description="Database ID")

    # ========== Processing State ==========
    status: EtoRunStatus = Field(EtoRunStatus.NOT_STARTED, description="Current processing status")
    processing_step: Optional[EtoProcessingStep] = Field(None, description="Current step when status=processing")

    # ========== Error Tracking ==========
    error_type: Optional[EtoErrorType] = Field(None, description="Error category for failed runs")
    error_message: Optional[str] = Field(None, description="Human-readable error message")
    error_details: Optional[str] = Field(None, description="JSON-encoded detailed error information")

    # ========== Template Matching ==========
    matched_template_id: Optional[int] = Field(None, description="ID of matched template")
    matched_template_version: Optional[int] = Field(None, description="Version of matched template")

    # ========== Data Processing ==========
    extracted_data: Optional[str] = Field(None, description="JSON-encoded extracted field values")
    transformation_audit: Optional[str] = Field(None, description="JSON-encoded transformation audit trail")
    target_data: Optional[str] = Field(None, description="JSON-encoded final transformed data")

    # ========== Pipeline Execution ==========
    failed_pipeline_step_id: Optional[int] = Field(None, description="ID of failed pipeline step")
    step_execution_log: Optional[str] = Field(None, description="JSON-encoded step execution details")

    # ========== Timeline ==========
    started_at: Optional[datetime] = Field(None, description="When processing started")
    completed_at: Optional[datetime] = Field(None, description="When processing completed")
    processing_duration_ms: Optional[int] = Field(None, description="Total processing duration in milliseconds")

    # ========== Order Integration ==========
    order_id: Optional[int] = Field(None, description="Created order ID after successful processing")

    # ========== Audit ==========
    created_at: datetime = Field(..., description="Record creation timestamp")
    updated_at: datetime = Field(..., description="Record last update timestamp")

    @field_validator('started_at', 'completed_at', 'created_at', 'updated_at', mode='before')
    @classmethod
    def ensure_timezone_aware_eto_run(cls, v):
        """Ensure datetime fields are timezone-aware"""
        return DateTimeUtils.ensure_utc_aware(v)

    class Config:
        from_attributes = True
        use_enum_values = True

    # ========== Helper Methods ==========

    def get_processing_state(self) -> EtoProcessingState:
        """Get current processing state information"""
        return EtoProcessingState(
            status=self.status,
            processing_step=self.processing_step,
            started_at=self.started_at,
            completed_at=self.completed_at,
            processing_duration_ms=self.processing_duration_ms
        )

    def get_error_info(self) -> EtoErrorInfo:
        """Get error information (if any)"""
        error_details_dict = None
        if self.error_details:
            try:
                error_details_dict = json.loads(self.error_details)
            except (json.JSONDecodeError, TypeError):
                error_details_dict = {"raw_error_details": self.error_details}

        return EtoErrorInfo(
            error_type=self.error_type,
            error_message=self.error_message,
            error_details=error_details_dict,
            failed_pipeline_step_id=self.failed_pipeline_step_id
        )

    def get_template_matching_result(self) -> EtoTemplateMatchingResult:
        """Get template matching results"""
        return EtoTemplateMatchingResult(
            matched_template_id=self.matched_template_id,
            matched_template_version=self.matched_template_version
        )

    def get_data_extraction_result(self) -> EtoDataExtractionResult:
        """Get data extraction results"""
        extracted_data_dict = None
        if self.extracted_data:
            try:
                extracted_data_dict = json.loads(self.extracted_data)
            except (json.JSONDecodeError, TypeError):
                extracted_data_dict = {"raw_extracted_data": self.extracted_data}

        return EtoDataExtractionResult(extracted_data=extracted_data_dict)

    def get_transformation_result(self) -> EtoTransformationResult:
        """Get transformation results"""
        transformation_audit_dict = None
        target_data_dict = None
        step_execution_log_dict = None

        if self.transformation_audit:
            try:
                transformation_audit_dict = json.loads(self.transformation_audit)
            except (json.JSONDecodeError, TypeError):
                transformation_audit_dict = {"raw_audit": self.transformation_audit}

        if self.target_data:
            try:
                target_data_dict = json.loads(self.target_data)
            except (json.JSONDecodeError, TypeError):
                target_data_dict = {"raw_target_data": self.target_data}

        if self.step_execution_log:
            try:
                step_execution_log_dict = json.loads(self.step_execution_log)
            except (json.JSONDecodeError, TypeError):
                step_execution_log_dict = {"raw_log": self.step_execution_log}

        return EtoTransformationResult(
            transformation_audit=transformation_audit_dict,
            target_data=target_data_dict,
            step_execution_log=step_execution_log_dict
        )

    def get_order_integration(self) -> EtoOrderIntegration:
        """Get order integration information"""
        return EtoOrderIntegration(order_id=self.order_id)

    def is_processing(self) -> bool:
        """Check if run is currently being processed"""
        return self.status == EtoRunStatus.PROCESSING

    def is_completed(self) -> bool:
        """Check if run is completed (success, failure, needs_template, or skipped)"""
        return self.status in [
            EtoRunStatus.SUCCESS,
            EtoRunStatus.FAILURE,
            EtoRunStatus.NEEDS_TEMPLATE,
            EtoRunStatus.SKIPPED
        ]

    def is_successful(self) -> bool:
        """Check if run completed successfully"""
        return self.status == EtoRunStatus.SUCCESS

    def has_error(self) -> bool:
        """Check if run has error information"""
        return self.error_message is not None or self.error_type is not None

    def can_be_reprocessed(self) -> bool:
        """Check if run can be reset for reprocessing"""
        return self.status in [EtoRunStatus.FAILURE, EtoRunStatus.NEEDS_TEMPLATE, EtoRunStatus.SKIPPED]

    @classmethod
    def from_db_model(cls, model: Any) -> 'EtoRun':
        """Create domain object from database model"""
        return cls(
            id=model.id,
            pdf_file_id=model.pdf_file_id,
            status=EtoRunStatus(model.status),
            processing_step=EtoProcessingStep(model.processing_step) if model.processing_step else None,
            error_type=EtoErrorType(model.error_type) if model.error_type else None,
            error_message=model.error_message,
            error_details=model.error_details,
            matched_template_id=model.matched_template_id,
            matched_template_version=model.matched_template_version,
            extracted_data=model.extracted_data,
            transformation_audit=model.transformation_audit,
            target_data=model.target_data,
            failed_pipeline_step_id=model.failed_pipeline_step_id,
            step_execution_log=model.step_execution_log,
            started_at=model.started_at,
            completed_at=model.completed_at,
            processing_duration_ms=model.processing_duration_ms,
            order_id=model.order_id,
            created_at=model.created_at,
            updated_at=model.updated_at
        )


# ========== Summary Models ==========

class EtoEmailInfo(BaseModel):
    """Email information when PDF originated from email ingestion"""
    email_id: int = Field(..., description="Email record ID")
    subject: Optional[str] = Field(None, description="Email subject")
    sender_email: Optional[str] = Field(None, description="Sender email address")
    sender_name: Optional[str] = Field(None, description="Sender display name")
    received_date: datetime = Field(..., description="When email was received")
    config_name: Optional[str] = Field(None, description="Email config name that ingested this email")

    @field_validator('received_date', mode='before')
    @classmethod
    def ensure_timezone_aware_email_info(cls, v):
        """Ensure datetime fields are timezone-aware"""
        return DateTimeUtils.ensure_utc_aware(v)

    class Config:
        from_attributes = True


class EtoRunSummary(BaseModel):
    """Lightweight ETO run summary for list views and API responses"""
    id: int = Field(..., description="Database ID")
    pdf_file_id: int = Field(..., description="Associated PDF file ID")
    status: EtoRunStatus = Field(..., description="Current processing status")
    processing_step: Optional[EtoProcessingStep] = Field(None, description="Current processing step")

    # Key timestamps for sorting/filtering
    started_at: Optional[datetime] = Field(None, description="When processing started")
    completed_at: Optional[datetime] = Field(None, description="When processing completed")
    processing_duration_ms: Optional[int] = Field(None, description="Processing duration")
    created_at: datetime = Field(..., description="Record creation timestamp")

    @field_validator('started_at', 'completed_at', 'created_at', mode='before')
    @classmethod
    def ensure_timezone_aware_summary(cls, v):
        """Ensure datetime fields are timezone-aware"""
        return DateTimeUtils.ensure_utc_aware(v)

    # Error summary
    has_error: bool = Field(False, description="Whether run has error information")
    error_type: Optional[EtoErrorType] = Field(None, description="Error category")

    # Results summary
    has_template_match: bool = Field(False, description="Whether template was matched")
    has_extracted_data: bool = Field(False, description="Whether data was extracted")
    has_transformed_data: bool = Field(False, description="Whether data was transformed")
    has_order: bool = Field(False, description="Whether order was created")

    # PDF file information
    file_size: Optional[int] = Field(None, description="PDF file size in bytes")
    filename: Optional[str] = Field(None, description="PDF filename")

    # Email information (when PDF originated from email)
    email: Optional[EtoEmailInfo] = Field(None, description="Email information if PDF came from email ingestion")

    class Config:
        from_attributes = True
        use_enum_values = True

    @classmethod
    def from_eto_run(cls, eto_run: EtoRun) -> 'EtoRunSummary':
        """Create summary from full EtoRun object"""
        return cls(
            id=eto_run.id,
            pdf_file_id=eto_run.pdf_file_id,
            status=eto_run.status,
            processing_step=eto_run.processing_step,
            started_at=eto_run.started_at,
            completed_at=eto_run.completed_at,
            processing_duration_ms=eto_run.processing_duration_ms,
            created_at=eto_run.created_at,
            has_error=eto_run.has_error(),
            error_type=eto_run.error_type,
            has_template_match=eto_run.get_template_matching_result().has_match(),
            has_extracted_data=eto_run.get_data_extraction_result().has_extracted_data(),
            has_transformed_data=eto_run.get_transformation_result().has_transformed_data(),
            has_order=eto_run.get_order_integration().has_order(),
            email=None  # Will be populated by repository when available
        )


# ========== Update Models ==========

class EtoRunStatusUpdate(BaseModel):
    """Model for updating ETO run status"""
    status: EtoRunStatus = Field(..., description="New status")
    processing_step: Optional[EtoProcessingStep] = Field(None, description="New processing step")

    # Optional fields that may be updated with status
    error_type: Optional[EtoErrorType] = Field(None, description="Error type for failure status")
    error_message: Optional[str] = Field(None, description="Error message for failure status")
    error_details: Optional[Dict[str, Any]] = Field(None, description="Detailed error information")
    failed_pipeline_step_id: Optional[int] = Field(None, description="Failed pipeline step ID")

    class Config:
        use_enum_values = True


class EtoRunTemplateMatchUpdate(BaseModel):
    """Model for updating template matching results"""
    matched_template_id: int = Field(..., description="Matched template ID")
    matched_template_version: int = Field(..., description="Matched template version")


class EtoRunDataExtractionUpdate(BaseModel):
    """Model for updating data extraction results"""
    extracted_data: Dict[str, Any] = Field(..., description="Extracted field values")

    class Config:
        arbitrary_types_allowed = True


class EtoRunTransformationUpdate(BaseModel):
    """Model for updating transformation results"""
    transformation_audit: Optional[Dict[str, Any]] = Field(None, description="Transformation audit trail")
    target_data: Dict[str, Any] = Field(..., description="Final transformed data")
    step_execution_log: Optional[Dict[str, Any]] = Field(None, description="Pipeline execution log")

    class Config:
        arbitrary_types_allowed = True


class EtoRunOrderUpdate(BaseModel):
    """Model for updating order integration"""
    order_id: int = Field(..., description="Created order ID")


# ========== Statistics and Reporting Models ==========

class EtoProcessingStatistics(BaseModel):
    """ETO processing statistics for monitoring and reporting"""
    total_runs: int = Field(0, description="Total number of ETO runs")
    status_counts: List[Dict[str, Union[str, int]]] = Field(default_factory=list, description="Counts by status")
    success_rate: float = Field(0.0, description="Success rate (0.0 to 1.0)")
    average_processing_time_ms: Optional[int] = Field(None, description="Average processing time")
    last_24h_runs: int = Field(0, description="Runs in last 24 hours")
    last_successful_run: Optional[datetime] = Field(None, description="Last successful run timestamp")
    last_failed_run: Optional[datetime] = Field(None, description="Last failed run timestamp")

    @field_validator('last_successful_run', 'last_failed_run', mode='before')
    @classmethod
    def ensure_timezone_aware_stats(cls, v):
        """Ensure datetime fields are timezone-aware"""
        return DateTimeUtils.ensure_utc_aware(v)

    class Config:
        arbitrary_types_allowed = True


class EtoRunResetResult(BaseModel):
    """Result of resetting failed runs for reprocessing"""
    failure_count: int = Field(0, description="Number of failure status runs reset")
    needs_template_count: int = Field(0, description="Number of needs_template status runs reset")
    skipped_count: int = Field(0, description="Number of skipped status runs reset")
    total_reset: int = Field(0, description="Total number of runs reset")

    def get_summary_message(self) -> str:
        """Get human-readable summary of reset operation"""
        if self.total_reset == 0:
            return "No runs were eligible for reset"

        details = []
        if self.failure_count > 0:
            details.append(f"{self.failure_count} failed runs")
        if self.needs_template_count > 0:
            details.append(f"{self.needs_template_count} needs-template runs")
        if self.skipped_count > 0:
            details.append(f"{self.skipped_count} skipped runs")

        return f"Reset {self.total_reset} runs for reprocessing ({', '.join(details)})"