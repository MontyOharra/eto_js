"""
PDF Templates API Schemas
Request/response models for PDF template creation and versioning endpoints
"""
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime
from api.schemas.common import APIResponse
from shared.models import PdfTemplate, PdfTemplateVersion, PdfObject, ExtractionField



# Request/Response schemas for PDF template operations

class PdfObjectRequest(BaseModel):
    """Request schema for PDF object data"""
    object_type: str = Field(..., description="Type of PDF object")
    bbox: List[float] = Field(..., description="Bounding box coordinates [x1, y1, x2, y2]")
    page_number: int = Field(..., ge=1, description="Page number (1-indexed)")
    text_content: Optional[str] = Field(None, description="Text content if applicable")


class ExtractionFieldRequest(BaseModel):
    """Request schema for extraction field definition"""
    field_name: str = Field(..., description="Name of the field to extract")
    field_type: str = Field(..., description="Type of data to extract")
    bbox: List[float] = Field(..., description="Bounding box for extraction area")
    page_number: int = Field(..., ge=1, description="Page number for extraction")


class PdfTemplateCreateResponse(BaseModel):
    """Response after creating a PDF template"""
    template_id: int = Field(..., description="ID of the created template")
    message: str = Field(..., description="Success message")


class PdfTemplateVersionCreateResponse(BaseModel):
    """Response after creating a template version"""
    version_id: int = Field(..., description="ID of the created version")
    version_num: int = Field(..., description="Version number")
    message: str = Field(..., description="Success message")


class TemplateUpdateRequest(BaseModel):
    """Request to update template basic information"""
    name: Optional[str] = Field(None, description="Template name")
    description: Optional[str] = Field(None, description="Template description")


class TemplateSetCurrentVersionRequest(BaseModel):
    """Request to set current active version"""
    version_id: int = Field(..., description="Version ID to make current")


class TemplateListResponse(BaseModel):
    """Response with list of templates"""
    templates: List[Dict[str, Any]] = Field(..., description="List of template summaries")
    total_count: int = Field(..., description="Total number of templates")


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

