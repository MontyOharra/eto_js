"""
PDF Template Domain Types
Domain objects for PDF template data extraction and matching / creation
"""
from dataclasses import dataclass
from typing import Optional, List
from datetime import datetime

from .pdf_processing import PdfObject

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
    """PDF template domain object"""
    id: int
    name: str
    customer_name: Optional[str]
    description: Optional[str]
    signature_objects: Optional[str]  # JSON string
    signature_object_count: Optional[int]
    extraction_fields: Optional[str]  # JSON string
    is_complete: bool
    coverage_threshold: float
    usage_count: int
    last_used_at: Optional[datetime]
    version: int
    is_current_version: bool
    created_by: Optional[str]
    created_at: Optional[datetime]
    updated_at: Optional[datetime]
    status: str


@dataclass
class TemplateMatchResult:
    """Result of template matching operation"""
    template_found: bool
    template_id: Optional[int] = None
    template_version: Optional[int] = None
    coverage_percentage: Optional[float] = None
    unmatched_object_count: Optional[int] = None
    match_details: Optional[str] = None  # JSON with detailed matching info


@dataclass
class ExtractionField:
    """Field definition for data extraction from PDFs"""
    label: str
    bounding_box: List[float]  # [x0, y0, x1, y1]
    page: int
    required: bool = False
    validation_regex: Optional[str] = None
    description: Optional[str] = None


@dataclass
class TemplateCreateRequest:
    """Request to create a new PDF template"""
    name: str
    customer_name: Optional[str]
    description: Optional[str]
    pdf_objects: List[PdfObject]  # All objects from the PDF
    signature_objects: List[PdfObject]  # Key objects that define this template
    extraction_fields: List[ExtractionField]  # Fields to extract from PDFs matching this template
    coverage_threshold: float = 0.8  # Minimum coverage percentage for a match


@dataclass
class TemplateVersionRequest:
    """Request to create a new version of an existing template"""
    base_template_id: int
    name: str
    customer_name: Optional[str]
    description: Optional[str]
    pdf_objects: List[PdfObject]
    signature_objects: List[PdfObject]
    extraction_fields: List[ExtractionField]
    coverage_threshold: float = 0.8
    version_notes: Optional[str] = None  # What changed in this version