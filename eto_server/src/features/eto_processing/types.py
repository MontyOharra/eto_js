"""
ETO Processing Domain Types
Domain objects for Email-to-Order processing workflow
"""
from dataclasses import dataclass
from typing import Optional, Dict, Any, List
from datetime import datetime


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