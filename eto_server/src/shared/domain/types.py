"""
Shared Domain Types
Central location for all domain objects used across the application
"""
from dataclasses import dataclass
from typing import Optional, Dict, Any, List
from datetime import datetime


# === ETO Processing Domain Types ===

@dataclass
class EtoRun:
    """ETO processing run domain object"""
    id: int
    email_id: int
    pdf_file_id: int
    status: str  # 'not_started', 'processing', 'success', 'failure', 'needs_template', 'skipped'
    created_at: datetime
    updated_at: datetime

    # Processing tracking
    processing_step: Optional[str] = None  # 'template_matching', 'extracting_data', 'transforming_data'

    # Error tracking
    error_type: Optional[str] = None  # 'template_matching_error', 'data_extraction_error', 'transformation_error'
    error_message: Optional[str] = None
    error_details: Optional[str] = None  # JSON string

    # Template matching results
    matched_template_id: Optional[int] = None
    template_version: Optional[int] = None
    template_match_coverage: Optional[float] = None
    unmatched_object_count: Optional[int] = None

    # Data extraction and transformation results
    extracted_data: Optional[str] = None  # JSON string
    transformation_audit: Optional[str] = None  # JSON string
    target_data: Optional[str] = None  # JSON string

    # Pipeline execution tracking
    failed_step_id: Optional[int] = None
    step_execution_log: Optional[str] = None  # JSON string

    # Processing timeline
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    processing_duration_ms: Optional[int] = None

    # Order integration
    order_id: Optional[int] = None


# === PDF Template Domain Types ===

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
class PdfObject:
    """PDF object for template matching"""
    object_type: str  # 'text', 'image', 'line', etc.
    content: Optional[str]  # Text content if applicable
    x: float
    y: float
    width: float
    height: float
    page_number: int
    properties: Optional[dict] = None  # Additional properties like font, color, etc.


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