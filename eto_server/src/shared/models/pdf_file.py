"""
PDF File Pydantic Models - New Nested Object Structure
Domain models for PDF file storage and management with structured object types
"""

import json
import logging
from pydantic import BaseModel, Field, field_validator
from typing import Optional, List, Dict, Any, Union
from datetime import datetime

from .pdf_processing import PdfObjects
from shared.utils import DateTimeUtils
from shared.database.models import PdfFileModel

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

    class Config:
        from_attributes = True


class PdfFileCreate(PdfFileBase):
    """Model for creating new PDF files - all data provided at creation"""
    # Override pdf_objects to accept both structured and legacy dict formats for performance during creation
    pdf_objects: List[Dict[str, Any]] = Field(default_factory=list, description="Extracted PDF objects")

    def model_dump_for_db(self) -> Dict[str, Any]:
        """Convert to database format with JSON serialization"""
        data = self.model_dump(exclude={'pdf_objects'})

        # Serialize objects to JSON string for database storage
        if self.pdf_objects:
            data['objects_json'] = json.dumps(self.pdf_objects)
        else:
            data['objects_json'] = None

        return data


class PdfFile(PdfFileBase):
    """Complete PDF file with DB-generated fields"""
    id: int = Field(..., description="Database ID")
    pdf_objects: PdfObjects = Field(default_factory=PdfObjects, description="Extracted PDF objects organized by type")
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
    def from_db_model(cls, db_model : PdfFileModel) -> 'PdfFile':
        """Convert from SQLAlchemy database model with JSON deserialization"""
        # Get all fields from the database model
        data = {
            'id': db_model.id,
            'email_id': db_model.email_id,
            'filename': db_model.filename,
            'original_filename': db_model.original_filename,
            'relative_path': db_model.relative_path,
            'file_size': db_model.file_size,
            'file_hash': db_model.file_hash,
            'page_count': db_model.page_count,
            'created_at': db_model.created_at,
            'updated_at': db_model.updated_at,
        }

        # Deserialize objects_json from JSON string to PdfObjects
        if db_model.objects_json:
            data['pdf_objects'] = PdfObjects.from_json(db_model.objects_json)
        else:
            data['pdf_objects'] = PdfObjects()

        return cls(**data)
    

class PdfDetailData(BaseModel):
    """PDF file detail data for template builder with nested object structure"""
    # PDF file info
    pdf_id: int
    filename: str
    original_filename: str
    file_size: int

    # PDF objects organized by type
    pdf_objects: PdfObjects = Field(default_factory=PdfObjects)

    # Email context (nullable)
    email_subject: Optional[str] = None
    sender_email: Optional[str] = None
    received_date: Optional[Any] = None  # datetime, but allowing Any for flexibility

    @property
    def total_object_count(self) -> int:
        """Get total count of all objects"""
        return self.pdf_objects.get_total_count()