"""
PDF Template Version Pydantic Models
Core models for PDF template versioning
"""

from pydantic import BaseModel, Field, field_validator
from typing import Optional, List
from datetime import datetime
import json

from ..pdf_processing import PdfObjects, ExtractionField
from shared.utils import DateTimeUtils
from shared.database.models import PdfTemplateVersionModel
        
class PdfTemplateVersionBase(BaseModel):
    """Core fields required for any template version"""
    pdf_template_id: int = Field(..., description="ID of parent template")
    signature_objects: PdfObjects = Field(..., description="Objects for template matching")
    extraction_fields: List[ExtractionField] = Field(..., min_length=1, description="Fields to extract")
    
    class Config:
        from_attributes = True
    
             
class PdfTemplateVersion(PdfTemplateVersionBase):
    """Complete template version with DB-generated fields"""

    id: int = Field(..., description="Version ID (DB-generated)")
    version_num: int = Field(..., ge=1, description="Version number (DB-generated)")
    usage_count: int = Field(0, ge=0, description="Number of times used")
    last_used_at: Optional[datetime] = Field(None, description="Last usage timestamp")
    created_at: datetime = Field(..., description="Creation timestamp")

    @field_validator('last_used_at', 'created_at', mode='before')
    @classmethod
    def ensure_timezone_aware_version(cls, v):
        """Ensure datetime fields are timezone-aware"""
        return DateTimeUtils.ensure_utc_aware(v)

    class Config:
        from_attributes = True

    @classmethod
    def from_db_model(cls, db_model : PdfTemplateVersionModel) -> 'PdfTemplateVersion':
        """Create from database model with JSON deserialization"""
        # Parse JSON fields back to objects
        if db_model.signature_objects:
            signature_objects = PdfObjects.from_json(db_model.signature_objects)
        
        extraction_fields = []
        if db_model.extraction_fields:
            try:
                fields_data = json.loads(db_model.extraction_fields)
                extraction_fields = [ExtractionField(**field_data) for field_data in fields_data]
            except (json.JSONDecodeError, TypeError):
                pass
        
        return cls(
            id=db_model.id,
            pdf_template_id=db_model.pdf_template_id,
            version_num=db_model.version_num,
            signature_objects=signature_objects,
            extraction_fields=extraction_fields,
            usage_count=db_model.usage_count,
            last_used_at=db_model.last_used_at,
            created_at=db_model.created_at
        )
        
        
class PdfTemplateVersionCreate(PdfTemplateVersionBase):
    """Model for creating new template versions"""
    # Inherits all base fields: pdf_template_id, signature_objects, 
    # extraction_fields, signature_object_count
    # No id, version, usage_count, last_used_at, created_at - these are DB-generated
    
    # Explicit type annotations for IDE support (inherits actual Field definitions from base)
        
    def model_dump_for_db(self) -> dict:
        """Convert to database format with JSON serialization"""
        data = self.model_dump(exclude={'signature_objects', 'extraction_fields'})
        
        # Serialize objects and fields to JSON for database storage
        data['signature_objects'] = self.signature_objects.to_json()
        data['extraction_fields'] = json.dumps([field.model_dump() for field in self.extraction_fields])
        
        return data