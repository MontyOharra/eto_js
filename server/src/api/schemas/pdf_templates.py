"""
PDF Templates API Schemas
Request/response models for PDF template creation - minimal set for actual API usage
"""
from pydantic import BaseModel, Field
from typing import List
from shared.types import PdfObjects, ExtractionField


class PdfTemplateVersionCreateRequest(BaseModel):
    """Request to create a new template version (excludes pdf_template_id since it comes from URL path)"""
    signature_objects: PdfObjects = Field(..., min_length=1, description="Objects for template matching")
    extraction_fields: List[ExtractionField] = Field(default_factory=list, description="Fields to extract")
    signature_object_count: int = Field(..., ge=1, description="Count of signature objects")