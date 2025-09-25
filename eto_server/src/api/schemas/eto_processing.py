"""
ETO Processing API Schemas
Request/response models for ETO processing endpoints - minimal set for actual API usage
"""
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime
from api.schemas.common import APIResponse

# Import the nested PDF object structure
from shared.models import PdfObjectsByType


class EtoRunPdfData(BaseModel):
    """PDF file and objects data for an ETO run - used by template builder"""
    run_id: int
    pdf_id: int
    filename: str
    original_filename: str
    file_size: int
    page_count: int
    object_count: int
    sha256_hash: str

    # PDF objects organized by type
    pdf_objects: PdfObjectsByType = Field(default_factory=PdfObjectsByType)

    # Email context (flat structure)
    email_subject: str
    sender_email: str
    received_date: datetime

    # ETO run status and processing info
    status: str = Field(..., description="ETO run status")
    processing_step: Optional[str] = Field(None, description="Current processing step")
    matched_template_id: Optional[int] = Field(None, description="Matched template ID")

    # Processing data
    extracted_data: Optional[Dict[str, Any]] = Field(None, description="Extracted data")
    transformation_audit: Optional[Dict[str, Any]] = Field(None, description="Transformation audit")
    target_data: Optional[Dict[str, Any]] = Field(None, description="Target data")

    # Timestamps
    created_at: Optional[datetime] = Field(None, description="Created timestamp")
    started_at: Optional[datetime] = Field(None, description="Started timestamp")
    completed_at: Optional[datetime] = Field(None, description="Completed timestamp")

    # Error info
    error_type: Optional[str] = Field(None, description="Error type")
    error_message: Optional[str] = Field(None, description="Error message")


class EtoRunPdfDataResponse(APIResponse):
    """Response for ETO run PDF data - used by template builder"""
    data: Optional[EtoRunPdfData] = None