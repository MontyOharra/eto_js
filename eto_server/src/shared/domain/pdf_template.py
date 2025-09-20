from dataclasses import dataclass
from typing import Optional, List
from datetime import datetime

@dataclass
class PdfTemplate:
    """PDF template domain object"""
    id: int
    name: str
    description: Optional[str]
    pdf_id: int
    status: str
    current_version_id: Optional[int]
    created_at: datetime
    updated_at: datetime
    
@dataclass
class PdfTemplateVersion:
    "PDF template version domain object"
    id: int
    pdf_template_id: int
    version: int
    signature_objects: str  # JSON string
    signature_object_count: int
    extraction_fields: str  # JSON string
    usage_count: int
    last_used_at: Optional[datetime]
    created_at: Optional[datetime]

@dataclass
class ExtractionField:
    """Field definition for data extraction from PDFs"""
    label: str
    bounding_box: List[float]  # [x0, y0, x1, y1]
    page: int
    required: bool = False
    validation_regex: Optional[str] = None
    description: Optional[str] = None