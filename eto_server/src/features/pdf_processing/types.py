"""
PDF Processing Domain Types
Domain objects for PDF file processing and analysis
"""
from dataclasses import dataclass
from typing import Optional, Dict, Any, List
from datetime import datetime
from ...shared.types.common import ProcessingStatus, OptionalString


@dataclass 
class PdfFile:
    """PDF file domain object"""
    id: Optional[int]
    email_id: int
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


@dataclass
class PdfTemplate:
    """PDF template for pattern matching domain object"""
    id: Optional[int]
    name: str
    signature_objects: List[PdfObject]
    signature_object_count: int
    extraction_fields: List[PdfExtractionBounds]
    created_at: datetime
    updated_at: datetime
    customer_name: Optional[str] = None
    description: Optional[str] = None
    is_complete: bool = False
    coverage_threshold: float = 0.6
    usage_count: int = 0
    last_used_at: Optional[datetime] = None
    version: int = 1
    is_current_version: bool = True
    created_by: Optional[str] = None
    status: str = 'active'


@dataclass
class TemplateMatchResult:
    """Result of template matching against PDF"""
    template_id: int
    template_name: str
    coverage_ratio: float
    matched_objects: int
    unmatched_objects: int
    confidence_score: float