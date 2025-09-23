"""
PDF Processing Pydantic Models
Core models for PDF file processing and object extraction
"""

from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime


class PdfObject(BaseModel):
    """Individual PDF object for template matching"""
    type: str = Field(..., description="Type of PDF object (text, image, line, etc.)")
    page: int = Field(..., ge=1, description="Page number (1-based)")
    text: str = Field("", description="Object text content")
    bbox: List[float] = Field(..., min_length=4, max_length=4, description="Bounding box coordinates [x0, y0, x1, y1]")
    confidence: float = Field(1.0, ge=0, le=1, description="Extraction confidence score")
    metadata: Optional[Dict[str, Any]] = Field(None, description="Additional object metadata (font, size, etc.)")

    class Config:
        from_attributes = True


class ExtractionField(BaseModel):
    """Field definition for data extraction from PDFs"""
    label: str = Field(..., min_length=1, description="Field label/name")
    bounding_box: List[float] = Field(..., min_length=4, max_length=4, description="Bounding box [x0, y0, x1, y1]")
    page: int = Field(..., ge=1, description="Page number (1-based)")
    required: bool = Field(False, description="Whether this field is required")
    validation_regex: Optional[str] = Field(None, description="Regex pattern for validation")
    description: Optional[str] = Field(None, description="Field description")
    
    class Config:
        from_attributes = True


class PdfObjectExtractionResult(BaseModel):
    """Service-level result for PDF object extraction"""
    success: bool
    objects: List[PdfObject]
    signature_hash: Optional[str] = None
    page_count: int = Field(..., ge=0)
    object_count: int = Field(..., ge=0)
    error_message: Optional[str] = None
    
    class Config:
        from_attributes = True