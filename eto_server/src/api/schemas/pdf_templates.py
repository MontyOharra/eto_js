"""
PDF Templates API Schemas
Request/response models for PDF template creation and versioning endpoints
"""
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime
from api.schemas.common import APIResponse
from shared.models import PdfTemplate, PdfTemplateVersion, PdfObject, ExtractionField



# Query parameter schemas removed - FastAPI handles query params automatically!  # All data comes from URL path parameters


class PdfTemplateVersionCreateRequest(BaseModel):
    """Request to create a new template version (excludes pdf_template_id since it comes from URL path)"""
    signature_objects: List[PdfObject] = Field(..., min_length=1, description="Objects for template matching")
    extraction_fields: List[ExtractionField] = Field(default_factory=list, description="Fields to extract")
    signature_object_count: int = Field(..., ge=1, description="Count of signature objects")


class TemplateVersionSummary(BaseModel):
    """Summary information about a template version for navigation"""
    id: int = Field(..., description="Version ID")
    version_num: int = Field(..., description="Version number")
    created_at: datetime = Field(..., description="Creation timestamp")
    usage_count: int = Field(..., description="Number of times used")
    is_current: bool = Field(..., description="Whether this is the current active version")


class TemplateDetailResponse(BaseModel):
    """Enhanced response for template details with optional includes"""
    template: PdfTemplate = Field(..., description="Template basic information")
    pdf_data: Optional[bytes] = Field(None, description="PDF file bytes (if requested)")
    current_version: Optional[PdfTemplateVersion] = Field(None, description="Current version details (if requested)")
    version_list: Optional[List[TemplateVersionSummary]] = Field(None, description="List of all versions (if requested)")
    total_versions: Optional[int] = Field(None, description="Total number of versions (if requested)")

