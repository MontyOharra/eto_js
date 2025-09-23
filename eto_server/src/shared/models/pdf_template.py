"""
PDF Template Pydantic Models
Core models for PDF template management and versioning
"""

from pydantic import BaseModel, Field, field_validator
from typing import Optional, List
from datetime import datetime
import json

from .pdf_processing import PdfObject, ExtractionField
from shared.utils import DateTimeUtils


""" PDF Template Models """

class PdfTemplateBase(BaseModel):
    """Core fields required for any PDF template"""
    name: str = Field(..., min_length=1, max_length=255, description="Template name")
    description: Optional[str] = Field(None, max_length=1000, description="Template description")
    source_pdf_id: int = Field(..., description="ID of the source PDF file")
    status: str = Field("active", pattern="^(active|inactive)$", description="Template status")
    
    class Config:
        from_attributes = True
      
class PdfTemplateCreate(PdfTemplateBase):
    """Model for creating new PDF templates"""

    initial_signature_objects: List[PdfObject]
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

class PdfTemplate(PdfTemplateBase):
    """Complete PDF template with DB-generated fields"""
    # Inherits all base fields: name, description, pdf_id, status
    
    # DB-generated fields
    id: int = Field(..., description="Template ID (DB-generated)")
    current_version_id: Optional[int] = Field(None, description="ID of current active version")
    created_at: datetime = Field(..., description="Creation timestamp")
    updated_at: datetime = Field(..., description="Last update timestamp")

    @field_validator('created_at', 'updated_at', mode='before')
    @classmethod
    def ensure_timezone_aware(cls, v):
        """Ensure datetime fields are timezone-aware"""
        return DateTimeUtils.ensure_utc_aware(v)

    class Config:
        from_attributes = True
        

""" PDF Template Version Models """
        
class PdfTemplateVersionBase(BaseModel):
    """Core fields required for any template version"""
    pdf_template_id: int = Field(..., description="ID of parent template")
    signature_objects: List[PdfObject] = Field(..., min_length=1, description="Objects for template matching")
    extraction_fields: List[ExtractionField] = Field(..., min_length=1, description="Fields to extract")
    
    # Computed/derived fields
    signature_object_count: int = Field(..., ge=1, description="Count of signature objects")
    
    class Config:
        from_attributes = True
    
    @field_validator('signature_object_count')
    @classmethod
    def validate_signature_object_count(cls, v, info):
        """Ensure signature_object_count matches signature_objects length"""
        if 'signature_objects' in info.data:
            actual_count = len(info.data['signature_objects'])
            if v != actual_count:
                return actual_count
        return v
             
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
    def from_db_model(cls, db_model) -> 'PdfTemplateVersion':
        """Create from database model with JSON deserialization"""
        # Parse JSON fields back to objects
        signature_objects = []
        if db_model.signature_objects:
            try:
                objects_data = json.loads(db_model.signature_objects)
                signature_objects = [PdfObject(**obj_data) for obj_data in objects_data]
            except (json.JSONDecodeError, TypeError):
                pass
        
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
            signature_object_count=len(signature_objects),
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
        data['signature_objects'] = json.dumps([obj.model_dump() for obj in self.signature_objects])
        data['extraction_fields'] = json.dumps([field.model_dump() for field in self.extraction_fields])
        
        return data
    
class PdfTemplateMatchResult(BaseModel):
    """Result of template matching operation"""
    template_found: bool
    template_id: Optional[int] = None
    template_version: Optional[int] = None
    coverage_percentage: Optional[float] = None
    unmatched_object_count: Optional[int] = None
    match_details: Optional[str] = None

    def get_match_data(self) -> tuple[int, int]:
        """
        Get matched template data with type safety

        Returns:
            Tuple of (template_id, template_version)

        Raises:
            ValueError: If no template was found
        """
        if not self.template_found or self.template_id is None or self.template_version is None:
            raise ValueError("No template match found - cannot get match data")

        return self.template_id, self.template_version

    class Config:
        from_attributes = True