"""
PDF File Pydantic Models
Domain models for PDF file storage and management
"""

from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime


class PdfFileBase(BaseModel):
    """Core fields for any PDF file"""
    filename: str = Field(..., description="Stored filename (usually hash-based)")
    original_filename: str = Field(..., description="Original filename from source")
    file_hash: str = Field(..., description="SHA256 hash for deduplication")
    file_size: int = Field(..., gt=0, description="File size in bytes")
    page_count: int = Field(..., gt=0, description="Number of pages")
    storage_path: str = Field(..., description="Relative path in storage system")
    email_id: Optional[int] = Field(None, description="Associated email ID (null for manual uploads)")
    extracted_text: Optional[str] = Field(None, description="Extracted text content")
    objects_json: Optional[str] = Field(None, description="Extracted PDF objects as JSON")
    
    class Config:
        from_attributes = True


class PdfFileCreate(PdfFileBase):
    """Model for creating new PDF files - all data provided at creation"""
    # All fields inherited from base
    # PDF is already processed with objects extracted before storage
    
    def model_dump_for_db(self) -> dict:
        """Convert to database format"""
        return self.model_dump()


class PdfFileUpdate(BaseModel):
    """Model for updating PDF files - only metadata can be updated"""
    # PDFs are mostly immutable, but we might update extracted data if re-processing
    extracted_text: Optional[str] = Field(None, description="Updated extracted text")
    objects_json: Optional[str] = Field(None, description="Updated extracted objects")
    
    def model_dump_for_db(self) -> dict:
        """Convert to database format, only including explicitly set fields"""
        return self.model_dump(exclude_unset=True)
    
    class Config:
        from_attributes = True


class PdfFile(PdfFileBase):
    """Complete PDF file with DB-generated fields"""
    id: int = Field(..., description="Database ID")
    created_at: datetime = Field(..., description="Creation timestamp")
    updated_at: datetime = Field(..., description="Last update timestamp")
    
    class Config:
        from_attributes = True


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