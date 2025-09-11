"""
PDF Processing API Schemas
Request/response models for PDF processing endpoints
"""
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime
from .common import APIResponse


class PdfObjectResponse(BaseModel):
    """PDF object response"""
    object_type: str = Field(description="Type of PDF object (text, image, line, etc.)")
    content: str = Field(description="Object content")
    x: float = Field(description="X coordinate")
    y: float = Field(description="Y coordinate")
    width: float = Field(description="Object width")
    height: float = Field(description="Object height")
    font_size: Optional[float] = Field(None, description="Font size (for text objects)")
    font_name: Optional[str] = Field(None, description="Font name (for text objects)")


class PdfExtractionBoundsResponse(BaseModel):
    """PDF extraction bounds response"""
    field_name: str = Field(description="Name of the field to extract")
    x: float = Field(description="X coordinate of extraction area")
    y: float = Field(description="Y coordinate of extraction area")
    width: float = Field(description="Width of extraction area")
    height: float = Field(description="Height of extraction area")
    page_number: int = Field(1, ge=1, description="Page number")


class PdfFileResponse(BaseModel):
    """PDF file response"""
    id: int
    email_id: int
    filename: str
    original_filename: str
    file_path: str
    file_size: int = Field(ge=0)
    sha256_hash: str
    mime_type: str = "application/pdf"
    page_count: Optional[int] = Field(None, ge=1)
    object_count: Optional[int] = Field(None, ge=0)
    created_at: datetime
    updated_at: datetime


class PdfTemplateResponse(BaseModel):
    """PDF template response"""
    id: int
    name: str
    customer_name: Optional[str] = None
    description: Optional[str] = None
    signature_objects: List[PdfObjectResponse]
    signature_object_count: int = Field(ge=0)
    extraction_fields: List[PdfExtractionBoundsResponse]
    is_complete: bool = False
    coverage_threshold: float = Field(0.6, ge=0.0, le=1.0)
    usage_count: int = Field(0, ge=0)
    last_used_at: Optional[datetime] = None
    version: int = Field(1, ge=1)
    is_current_version: bool = True
    created_by: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    status: str = "active"


class CreatePdfTemplateRequest(BaseModel):
    """Request to create PDF template"""
    name: str = Field(..., min_length=1, max_length=255)
    customer_name: Optional[str] = Field(None, max_length=255)
    description: Optional[str] = Field(None, max_length=1000)
    signature_objects: List[PdfObjectResponse] = Field(..., min_items=1)
    extraction_fields: List[PdfExtractionBoundsResponse] = Field(default_factory=list)
    coverage_threshold: float = Field(0.6, ge=0.0, le=1.0)
    created_by: str = Field(..., description="User creating the template")


class UpdatePdfTemplateRequest(BaseModel):
    """Request to update PDF template"""
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    customer_name: Optional[str] = Field(None, max_length=255)
    description: Optional[str] = Field(None, max_length=1000)
    signature_objects: Optional[List[PdfObjectResponse]] = Field(None, min_items=1)
    extraction_fields: Optional[List[PdfExtractionBoundsResponse]] = None
    coverage_threshold: Optional[float] = Field(None, ge=0.0, le=1.0)
    is_complete: Optional[bool] = None
    status: Optional[str] = Field(None, regex="^(active|archived|draft)$")


class TemplateMatchResultResponse(BaseModel):
    """Template matching result response"""
    template_id: int
    template_name: str
    coverage_ratio: float = Field(ge=0.0, le=1.0)
    matched_objects: int = Field(ge=0)
    unmatched_objects: int = Field(ge=0)
    confidence_score: float = Field(ge=0.0, le=1.0)


class PdfAnalysisRequest(BaseModel):
    """Request to analyze PDF for template matching"""
    pdf_file_id: int = Field(..., description="PDF file ID to analyze")
    template_ids: Optional[List[int]] = Field(None, description="Specific templates to test (None for all active)")
    min_coverage: float = Field(0.3, ge=0.0, le=1.0, description="Minimum coverage threshold")


class PdfAnalysisResponse(BaseModel):
    """PDF analysis response"""
    pdf_file_id: int
    pdf_filename: str
    object_count: int = Field(ge=0)
    template_matches: List[TemplateMatchResultResponse]
    best_match: Optional[TemplateMatchResultResponse] = None
    suggested_new_template: bool = False
    analysis_duration_ms: int = Field(ge=0)


class PdfTemplateStatsResponse(BaseModel):
    """PDF template statistics response"""
    template_id: int
    template_name: str
    total_matches: int = Field(ge=0)
    successful_extractions: int = Field(ge=0)
    failed_extractions: int = Field(ge=0)
    avg_coverage_ratio: float = Field(ge=0.0, le=1.0)
    avg_processing_time_ms: int = Field(ge=0)
    last_used_at: Optional[datetime] = None
    created_at: datetime