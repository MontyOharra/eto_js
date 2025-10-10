"""
ETO Processing Domain Models
Comprehensive models for the ETO (Extract, Transform, Order) processing pipeline
"""
from typing import Optional, Dict, Any
from datetime import datetime
from pydantic import BaseModel, Field, field_validator
import json

from shared.utils import DateTimeUtils
from ..pdf_processing import PdfObjects
from ..enums import EtoRunStatus, EtoProcessingStep, EtoErrorType

from shared.database.models import EtoRunModel



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


# ========== Complete Domain Model ==========

class EtoRun(EtoRunBase):
    """Complete ETO run domain model with all database fields"""

    # ========== Core Identity ==========
    id: int = Field(..., description="Database ID")

    # ========== Processing State ==========
    status: EtoRunStatus = Field(..., description="Current processing status")
    processing_step: Optional[EtoProcessingStep] = Field(..., description="Current step when status=processing")

    # ========== Error Tracking ==========
    error_type: Optional[EtoErrorType] = Field(..., description="Error category for failed runs")
    error_message: Optional[str] = Field(..., description="Human-readable error message")
    error_details: Optional[str] = Field(..., description="JSON-encoded detailed error information")

    # ========== Template Matching ==========
    matched_template_id: Optional[int] = Field(..., description="ID of matched template")
    matched_template_version: Optional[int] = Field(..., description="Version of matched template")

    # ========== Data Processing ==========
    extracted_data: Optional[str] = Field(..., description="JSON-encoded extracted field values")
    transformation_audit: Optional[str] = Field(..., description="JSON-encoded transformation audit trail")
    target_data: Optional[str] = Field(..., description="JSON-encoded final transformed data")

    # ========== Pipeline Execution ==========
    failed_pipeline_step_id: Optional[int] = Field(..., description="ID of failed pipeline step")
    step_execution_log: Optional[str] = Field(..., description="JSON-encoded step execution details")

    # ========== Timeline ==========
    started_at: Optional[datetime] = Field(..., description="When processing started")
    completed_at: Optional[datetime] = Field(..., description="When processing completed")
    processing_duration_ms: Optional[int] = Field(..., description="Total processing duration in milliseconds")

    # ========== Order Integration ==========
    order_id: Optional[int] = Field(..., description="Created order ID after successful processing")

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

    def can_be_reprocessed(self) -> bool:
        """Check if run can be reset for reprocessing"""
        return self.status in ['failure', 'needs_template', 'skipped']

    @classmethod
    def from_db_model(cls, model: EtoRunModel) -> 'EtoRun':
        """Create domain object from database model"""
        return cls(
            id=model.id,
            pdf_file_id=model.pdf_file_id,
            status=model.status if model.status else None,
            processing_step=model.processing_step if model.processing_step else None,
            error_type=model.error_type if model.error_type else None,
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
    def from_get_runs_with_filters(cls, result) -> 'EtoRunSummary':
        """
        Create summary directly from repository SQL result for better performance.
        Avoids creating full EtoRun domain object.

        Args:
            result: SQLAlchemy result row with EtoRunModel and joined data

        Returns:
            EtoRunSummary with all fields populated from SQL result
        """
        # Extract the EtoRunModel (first item in result tuple)
        eto_run_model: EtoRunModel = result[0]

        # Create email info if available from JOIN
        email_info = None
        if len(result) > 1 and result.email_id:
            email_info = EtoEmailInfo(
                email_id=result.email_id,
                subject=result.email_subject,
                sender_email=result.email_sender_email,
                sender_name=result.email_sender_name,
                received_date=result.email_received_date,
            )

        # Create summary with all required fields
        return cls(
            id=eto_run_model.id,
            pdf_file_id=eto_run_model.pdf_file_id,
            status=eto_run_model.status if eto_run_model.status else None,
            processing_step=eto_run_model.processing_step if eto_run_model.processing_step else None,
            started_at=eto_run_model.started_at,
            completed_at=eto_run_model.completed_at,
            processing_duration_ms=eto_run_model.processing_duration_ms,
            created_at=eto_run_model.created_at,
            has_error=eto_run_model.error_message is not None or eto_run_model.error_type is not None,
            error_type=eto_run_model.error_type if eto_run_model.error_type else None,
            has_template_match=eto_run_model.matched_template_id is not None,
            has_extracted_data=eto_run_model.extracted_data is not None,
            has_transformed_data=eto_run_model.target_data is not None,
            has_order=eto_run_model.order_id is not None,
            file_size=getattr(result, 'file_size', None),
            filename=getattr(result, 'filename', None),
            email=email_info
        )


class EtoRunWithPdfData(BaseModel):
    """ETO run with complete PDF and email data"""

    # ETO run data
    run_id: int
    status: str
    processing_step: Optional[str] = None
    matched_template_id: Optional[int] = None
    extracted_data: Optional[Dict[str, Any]] = None
    transformation_audit: Optional[Dict[str, Any]] = None
    target_data: Optional[Dict[str, Any]] = None
    error_type: Optional[str] = None
    error_message: Optional[str] = None
    created_at: datetime
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None

    # PDF file data
    pdf_id: int
    filename: str
    original_filename: str
    file_size: int
    page_count: int
    object_count: int
    sha256_hash: str
    pdf_objects: PdfObjects = Field(default_factory=PdfObjects)

    # Email context (nullable for manual uploads)
    email_subject: Optional[str] = None
    sender_email: Optional[str] = None
    received_date: Optional[datetime] = None

    class Config:
        from_attributes = True

    @classmethod
    def from_get_eto_run_with_pdf_data(cls, result) -> 'EtoRunWithPdfData':
        """
        Create EtoRunWithPdfData from repository SQL result

        Args:
            result: SQLAlchemy result row with EtoRunModel and joined data

        Returns:
            EtoRunWithPdfData with all fields populated from SQL result
        """
        # Extract the EtoRunModel (first item in result tuple)
        eto_run_model: EtoRunModel = result[0]

        # Parse PDF objects to nested structure
        pdf_objects = PdfObjects()
        if result.pdf_objects_json:
            try:
                pdf_objects = PdfObjects.from_json(result.pdf_objects_json)
            except Exception as e:
                import logging
                logger = logging.getLogger(__name__)
                logger.warning(f"Failed to parse PDF objects for ETO run {eto_run_model.id}: {e}")

        return cls(
            # ETO run data
            run_id=eto_run_model.id,
            status=eto_run_model.status,
            processing_step=eto_run_model.processing_step,
            matched_template_id=eto_run_model.matched_template_id,
            extracted_data=json.loads(eto_run_model.extracted_data) if eto_run_model.extracted_data else None,
            transformation_audit=json.loads(eto_run_model.transformation_audit) if eto_run_model.transformation_audit else None,
            target_data=json.loads(eto_run_model.target_data) if eto_run_model.target_data else None,
            error_type=eto_run_model.error_type,
            error_message=eto_run_model.error_message,
            created_at=eto_run_model.created_at,
            started_at=eto_run_model.started_at,
            completed_at=eto_run_model.completed_at,

            # PDF file data
            pdf_id=result.pdf_id,
            filename=result.pdf_filename,
            original_filename=result.pdf_original_filename,
            file_size=result.pdf_file_size,
            page_count=result.pdf_page_count,
            object_count=pdf_objects.get_total_count(),
            sha256_hash=result.pdf_file_hash,
            pdf_objects=pdf_objects,

            # Email context (nullable)
            email_subject=result.email_subject,
            sender_email=result.email_sender_email,
            received_date=result.email_received_date
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