"""
PDF Template Pydantic Models
Core models for PDF template management
"""

from pydantic import BaseModel, Field, field_validator
from typing import Optional, List
from datetime import datetime

from ..pdfs import PdfObjects, ExtractionField
from shared.utils import DateTimeUtils
from shared.database.models import PdfTemplateModel


class PdfTemplateBase(BaseModel):
    """Core fields required for any PDF template"""
    name: str = Field(..., min_length=1, max_length=255, description="Template name")
    description: Optional[str] = Field(None, max_length=1000, description="Template description")
    source_pdf_id: int = Field(..., description="ID of the source PDF file")
    
    class Config:
        from_attributes = True
      

class PdfTemplate(PdfTemplateBase):
    """Complete PDF template with DB-generated fields"""
    # Inherits all base fields: name, description, pdf_id, status
    
    # DB-generated fields
    id: int = Field(..., description="Template ID (DB-generated)")
    current_version_id: Optional[int] = Field(None, description="ID of current active version")
    status: str = Field("active", pattern="^(active|inactive)$", description="Template status")
    created_at: datetime = Field(..., description="Creation timestamp")
    updated_at: datetime = Field(..., description="Last update timestamp")

    @field_validator('created_at', 'updated_at', mode='before')
    @classmethod
    def ensure_timezone_aware(cls, v):
        """Ensure datetime fields are timezone-aware"""
        return DateTimeUtils.ensure_utc_aware(v)

    class Config:
        from_attributes = True
        
    @classmethod
    def from_db_model(cls, db_model : PdfTemplateModel) -> 'PdfTemplate':
        """Create from database model with JSON deserialization"""
        return cls(
            id=db_model.id,
            name=db_model.name,
            description=db_model.description,
            source_pdf_id=db_model.source_pdf_id,
            status=db_model.status,
            created_at=db_model.created_at,
            updated_at=db_model.updated_at,
            current_version_id=db_model.current_version_id
        )
        

class PdfTemplateCreate(PdfTemplateBase):
    """Model for creating new PDF templates"""

    initial_signature_objects: PdfObjects
    initial_extraction_fields: List[ExtractionField]

    def model_dump_for_db(self) -> dict:
      return self.model_dump(exclude={'initial_signature_objects', 'initial_extraction_fields'})


class PdfTemplateUpdate(BaseModel):
    """Model for updating existing PDF templates"""
    name: Optional[str] = Field(None, min_length=1, max_length=255, description="Template name")
    description: Optional[str] = Field(None, max_length=1000, description="Template description")
    status: Optional[str] = Field(None, pattern="^(active|inactive)$", description="Template status")
    
    def model_dump_for_db(self) -> dict:
        """Convert to database format, only including explicitly set fields"""
        return self.model_dump(exclude_unset=True)
    
    class Config:
        from_attributes = True