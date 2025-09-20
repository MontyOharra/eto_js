"""
PDF Templates API Schemas
Request/response models for PDF template creation and versioning endpoints
"""
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime
from api.schemas.common import APIResponse


class PdfObjectRequest(BaseModel):
    """PDF object data for template creation"""
    type: str = Field(..., description="Type of PDF object (text, image, line, etc.)")
    page: int = Field(..., ge=1, description="Page number (1-based)")
    text: str = Field("", description="Object text content")
    x: float = Field(0, description="X coordinate")
    y: float = Field(0, description="Y coordinate")
    width: float = Field(0, description="Object width")
    height: float = Field(0, description="Object height")
    bbox: List[float] = Field(default_factory=list, description="Bounding box coordinates")
    font_name: Optional[str] = Field(None, description="Font name (for text objects)")
    font_size: Optional[float] = Field(None, description="Font size (for text objects)")
    char_count: Optional[int] = Field(None, description="Character count (for text objects)")


class ExtractionFieldRequest(BaseModel):
    """Extraction field data for template creation"""
    label: str = Field(..., min_length=1, description="Field label/name")
    boundingBox: List[float] = Field(..., min_length=4, max_length=4, description="Bounding box [x0, y0, x1, y1]")
    page: int = Field(..., ge=1, description="Page number (1-based)")
    required: bool = Field(False, description="Whether this field is required")
    validationRegex: Optional[str] = Field(None, description="Regex pattern for validation")
    description: Optional[str] = Field(None, description="Field description")


class PdfTemplateCreateRequest(BaseModel):
    """Request to create a new PDF template"""
    name: str = Field(..., min_length=1, max_length=255, description="Template name")
    description: Optional[str] = Field(None, max_length=1000, description="Template description")
    source_pdf_id: int = Field(..., description="ID of the source PDF file")
    selected_objects: List[PdfObjectRequest] = Field(..., min_length=1, description="PDF objects for template matching")
    extraction_fields: List[ExtractionFieldRequest] = Field(default_factory=list, description="Fields to extract from matching PDFs")


class PdfTemplateVersionCreateRequest(BaseModel):
    """Request to create a new version of an existing template"""
    signature_objects: List[PdfObjectRequest] = Field(..., min_length=1, description="PDF objects for template matching")
    extraction_fields: List[ExtractionFieldRequest] = Field(default_factory=list, description="Fields to extract from matching PDFs")


class PdfTemplateCreateResponse(APIResponse):
    """Response for template creation"""
    template_id: Optional[int] = Field(None, description="ID of created template")
    signature_object_count: Optional[int] = Field(None, description="Number of signature objects")
    extraction_field_count: Optional[int] = Field(None, description="Number of extraction fields")


class PdfTemplateVersionCreateResponse(APIResponse):
    """Response for template version creation"""
    template_id: Optional[int] = Field(None, description="ID of the template")
    version_id: Optional[int] = Field(None, description="ID of created version")
    version_number: Optional[int] = Field(None, description="Version number")
    signature_object_count: Optional[int] = Field(None, description="Number of signature objects")
    extraction_field_count: Optional[int] = Field(None, description="Number of extraction fields")


class TemplateListResponse(APIResponse):
    """Response for template listing"""
    templates: Optional[List[Dict[str, Any]]] = Field(None, description="List of templates")
    total_count: Optional[int] = Field(None, description="Total number of templates")


class TemplateListRequest(BaseModel):
    """Query parameters for listing templates"""
    status: Optional[str] = Field(None, pattern="^(active|inactive)$", description="Filter by template status")
    order_by: Optional[str] = Field("created_at", description="Field to order by")
    desc: bool = Field(False, description="Sort in descending order")
    page: int = Field(1, ge=1, description="Page number")
    limit: int = Field(20, ge=1, le=100, description="Items per page")
    include: Optional[str] = Field(None, pattern="^(current|all)$", description="Include version data")


class TemplateGetRequest(BaseModel):
    """Query parameters for getting single template"""
    include: Optional[str] = Field(None, pattern="^(current|all)$", description="Include version data")


class TemplateVersionGetRequest(BaseModel):
    """Query parameters for getting template version (likely empty)"""
    pass  # All data comes from URL path parameters


class TemplateUpdateRequest(BaseModel):
    """Request to update template fields"""
    name: Optional[str] = Field(None, min_length=1, max_length=255, description="Template name")
    description: Optional[str] = Field(None, max_length=1000, description="Template description")
    status: Optional[str] = Field(None, pattern="^(active|inactive)$", description="Template status")


class TemplateSetCurrentVersionRequest(BaseModel):
    """Request to set current template version"""
    version_id: int = Field(..., description="ID of version to set as current")


class TemplateDetailResponse(APIResponse):
    """Response for template details"""
    template: Optional[Dict[str, Any]] = Field(None, description="Template details")
    versions: Optional[List[Dict[str, Any]]] = Field(None, description="Template versions")