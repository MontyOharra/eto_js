"""
PDF Processing Domain Types
Domain objects for PDF file processing and analysis
"""
from dataclasses import dataclass
from typing import Optional, Dict, Any, List
from datetime import datetime
from ...shared.types.common import ProcessingStatus, OptionalString


@dataclass
class PdfStoreRequest:
    """Domain object for storing any PDF (email, manual, API)"""
    original_filename: str
    email_id: Optional[int] = None  # None for manual/API uploads
    filename: Optional[str] = None  # Auto-generated if None
    mime_type: str = 'application/pdf'


@dataclass
class PdfExtractionResult:
    """Domain object for extraction results"""
    success: bool
    pdf_id: int
    object_count: int
    page_count: int
    objects_json: Optional[str] = None
    error_message: Optional[str] = None
    extraction_time_ms: int = 0


@dataclass 
class PdfFile:
    """PDF file domain object"""
    id: Optional[int]
    email_id: Optional[int]  # Made optional for manual uploads
    filename: str
    original_filename: str
    file_path: str
    file_size: int
    sha256_hash: str
    created_at: datetime
    updated_at: datetime
    mime_type: str = 'application/pdf'
    page_count: Optional[int] = None
    object_count: Optional[int] = None
    objects_json: Optional[str] = None


@dataclass
class PdfObject:
    """Individual PDF object for template matching"""
    object_type: str  # 'text', 'image', 'line', etc.
    content: str
    x: float
    y: float  
    width: float
    height: float
    font_size: Optional[float] = None
    font_name: Optional[str] = None


@dataclass
class PdfExtractionBounds:
    """Spatial bounding box for data extraction"""
    field_name: str
    x: float
    y: float
    width: float
    height: float
    page_number: int = 1