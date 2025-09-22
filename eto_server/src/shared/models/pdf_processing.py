"""
PDF Processing Pydantic Models
Core models for PDF file processing and object extraction
"""

from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime


class PdfObject(BaseModel):
    """Individual PDF object for template matching"""
    type: str = Field(..., description="Type of PDF object (text, image, line, etc.)")
    page: int = Field(..., ge=1, description="Page number (1-based)")
    text: str = Field("", description="Object text content")
    x: float = Field(0, description="X coordinate")
    y: float = Field(0, description="Y coordinate")
    width: float = Field(0, description="Object width")
    height: float = Field(0, description="Object height")
    bbox: Optional[List[float]] = Field(None, description="Bounding box coordinates")
    font_name: Optional[str] = Field(None, description="Font name (for text objects)")
    font_size: Optional[float] = Field(None, description="Font size (for text objects)")
    char_count: Optional[int] = Field(None, description="Character count (for text objects)")
    
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