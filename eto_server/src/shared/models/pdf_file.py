"""
PDF File Pydantic Models
Domain models for PDF file storage and management
"""

import json
import logging
from pydantic import BaseModel, Field, field_validator
from typing import Optional, List, Dict, Any
from datetime import datetime

from .pdf_processing import PdfObject
from shared.utils import DateTimeUtils

logger = logging.getLogger(__name__)

class PdfFileBase(BaseModel):
    """Core fields for any PDF file"""
    email_id: Optional[int] = Field(None, description="Associated email ID (null for manual uploads)")
    filename: str = Field(..., description="Stored filename (usually hash-based)")
    original_filename: str = Field(..., description="Original filename from source")
    relative_path: str = Field(..., description="Relative path in storage system")
    file_hash: str = Field(..., description="SHA256 hash for deduplication")
    file_size: int = Field(..., gt=0, description="File size in bytes")
    page_count: int = Field(..., gt=0, description="Number of pages")
    object_count: int = Field(..., ge=0, description="Number of extracted objects")
    objects_json: List[PdfObject] = Field(default_factory=list, description="Extracted PDF objects as JSON")
    
    class Config:
        from_attributes = True


class PdfFileCreate(PdfFileBase):
    """Model for creating new PDF files - all data provided at creation"""
    # All fields inherited from base
    # PDF is already processed with objects extracted before storage

    def model_dump_for_db(self) -> Dict[str, Any]:
        """Convert to database format with JSON serialization"""
        data = self.model_dump(exclude={'objects_json'})

        # Serialize objects to JSON string for database storage
        if self.objects_json:
            # Convert PdfObject instances to dictionaries then serialize to JSON
            objects_dicts = [obj.model_dump() for obj in self.objects_json]
            data['objects_json'] = json.dumps(objects_dicts)
        else:
            data['objects_json'] = None

        return data



class PdfFile(PdfFileBase):
    """Complete PDF file with DB-generated fields"""
    id: int = Field(..., description="Database ID")
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
    def from_db_model(cls, db_model) -> 'PdfFile':
        """Convert from SQLAlchemy database model with JSON deserialization"""
        # Get all fields from the database model
        data = {
            'id': db_model.id,
            'email_id': db_model.email_id,
            'filename': db_model.filename,
            'original_filename': db_model.original_filename,
            'relative_path': db_model.relative_path, 
            'file_hash': db_model.file_hash,
            'file_size': db_model.file_size,
            'page_count': db_model.page_count,
            'object_count': db_model.object_count,
            'created_at': db_model.created_at,
            'updated_at': db_model.updated_at,
        }

        # Deserialize objects_json from JSON string to PdfObject list
        if db_model.objects_json:
            try:
                objects_dicts = json.loads(db_model.objects_json)
                # Convert dictionaries back to PdfObject instances
                data['objects_json'] = [PdfObject(**obj_dict) for obj_dict in objects_dicts]
            except (json.JSONDecodeError, TypeError, ValueError) as e:
                # If JSON is invalid, use empty list and log warning
                logger.warning(f"Failed to deserialize objects_json for PDF {db_model.id}: {e}")
                data['objects_json'] = []
        else:
            data['objects_json'] = []

        return cls(**data)


class PdfFileSummary(BaseModel):
    """Summary view of PDF file for list endpoints"""
    id: int = Field(..., description="Database ID")
    original_filename: str = Field(..., description="Original filename")
    file_hash: str = Field(..., description="File hash for deduplication")
    file_size: int = Field(..., description="File size in bytes")
    page_count: int = Field(..., description="Number of pages")
    email_id: Optional[int] = Field(None, description="Associated email ID")
    created_at: datetime = Field(..., description="Creation timestamp")
    has_extracted_objects: bool = Field(..., description="Whether objects have been extracted")

    @field_validator('created_at', mode='before')
    @classmethod
    def ensure_timezone_aware_summary(cls, v):
        """Ensure datetime fields are timezone-aware"""
        return DateTimeUtils.ensure_utc_aware(v)

    class Config:
        from_attributes = True
    
    @classmethod
    def from_pdf_file(cls, pdf: PdfFile) -> 'PdfFileSummary':
        """Create summary from full PDF file"""
        return cls(
            id=pdf.id,
            original_filename=pdf.original_filename,
            file_hash=pdf.file_hash,
            file_size=pdf.file_size,
            page_count=pdf.page_count,
            email_id=pdf.email_id,
            created_at=pdf.created_at,
            has_extracted_objects=bool(pdf.objects_json)
        )