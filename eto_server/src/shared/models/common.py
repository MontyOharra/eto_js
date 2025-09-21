"""
Common Shared Models
Base classes and common models used across features
"""

from pydantic import BaseModel, Field
from typing import Optional
import json


class TemplateMatchResult(BaseModel):
    """Result of template matching operation"""
    template_found: bool
    template_id: Optional[int] = None
    template_version: Optional[int] = None
    coverage_percentage: Optional[float] = None
    unmatched_object_count: Optional[int] = None
    match_details: Optional[str] = None
    
    class Config:
        from_attributes = True