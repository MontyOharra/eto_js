"""
Email Domain Models
Pydantic models for email records (append-only pattern)
"""
from typing import Optional, List, Dict, Any
from datetime import datetime
from pydantic import BaseModel, Field

class EtoRunBase(BaseModel):
    """Base ETO fields used for creation and display"""
    pdf_file_id: int = Field(..., description="Associated PDF file ID")
    
    def model_dump_for_db(self) -> Dict[str, Any]:
        """
        Convert model to dict for database insertion.
        Consistent with other models even though no special handling needed.
        """
        return self.model_dump(exclude_unset=True)

class EtoRunCreate(EtoRunBase):
    """Model for creating new ETO runs"""
    pass  # All fields inherited from EtoRunBase
  
class EtoRun(EtoRunBase):
    """Complete ETO run domain model with database fields"""
    id: int = Field(..., description="Database ID")
    status: str = Field(..., description="ETO run status")
    processing_step: Optional[str] = Field(default=None, description="Current processing step")
    error_type: Optional[str] = Field(default=None, description="Error type")
    error_message: Optional[str] = Field(default=None, description="Error message")
    error_details: Optional[str] = Field(default=None, description="Error details")
    matched_template_id: Optional[int] = Field(default=None, description="Template ID")
    matched_template_version: Optional[int] = Field(default=None, description="Template version")
    extracted_data: Optional[str] = Field(default=None, description="Extracted data JSON")
    transformation_audit: Optional[str] = Field(default=None, description="Transformation audit JSON")
    target_data: Optional[str] = Field(default=None, description="Final target data JSON")
    failed_pipeline_step_id: Optional[int] = Field(default=None, description="Failed pipeline step ID")
    step_execution_log: Optional[str] = Field(default=None, description="Step execution log JSON")
    started_at: Optional[datetime] = Field(default=None, description="When ETO run started")
    completed_at: Optional[datetime] = Field(default=None, description="When ETO run completed")
    processing_duration_ms: Optional[int] = Field(default=None, description="ETO run duration in ms")
    order_id: Optional[int] = Field(default=None, description="Order ID")
    
    class Config:
        from_attributes = True
        
    @classmethod
    def from_db_model(cls, model: Any) -> 'EtoRun':
        """
        Create from database model.
        Used by repository's _convert_to_domain_object method.
        """
        return cls(
            id=model.id,
            pdf_file_id=model.pdf_file_id,
            status=model.status,
            processing_step=model.processing_step,
            error_type=model.error_type,
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
            order_id=model.order_id
        )


class EtoRunSummary(BaseModel):
    """Lightweight ETO run summary for list views"""
    id: int = Field(..., description="Database ID")
    pdf_file_id: int = Field(..., description="PDF file ID")
    status: str = Field(..., description="ETO run status")
    processing_step: Optional[str] = Field(default=None, description="Current processing step")
    started_at: Optional[datetime] = Field(default=None, description="When ETO run started")
    completed_at: Optional[datetime] = Field(default=None, description="When ETO run completed")
    processing_duration_ms: Optional[int] = Field(default=None, description="ETO run duration in ms")
    
    class Config:
        from_attributes = True
    