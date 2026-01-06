"""
PDF Files API Schemas

Pydantic models for PDF file access endpoints.
Reuses domain types from shared/types where possible.
"""
from pydantic import BaseModel

from shared.types.pdf_files import (
    PdfFile as DomainPdfFile,
    PdfObjects,
    TextWord,
    GraphicRect,
    GraphicLine,
    GraphicCurve,
    Image,
    Table,
)


# ========== Re-export domain types for API use ==========
# These are the same as domain types - no transformation needed

__all__ = [
    "TextWord",
    "GraphicRect",
    "GraphicLine",
    "GraphicCurve",
    "Image",
    "Table",
    "PdfObjects",
    "PdfFileResponse",
    "GetPdfObjectsResponse",
    "ProcessPdfObjectsResponse",
]


# ========== Response Schemas ==========

class PdfFileResponse(BaseModel):
    """
    PDF File API response.

    Similar to domain PdfFile but excludes internal audit fields
    (created_at/updated_at) and uses string for stored_at.
    """
    id: int
    original_filename: str
    file_hash: str
    file_size_bytes: int
    file_path: str
    page_count: int | None = None
    stored_at: str  # ISO 8601
    extracted_objects: PdfObjects


class GetPdfObjectsResponse(BaseModel):
    """Response for GET /pdf-files/{id}/objects endpoint."""
    pdf_file_id: int
    page_count: int
    objects: PdfObjects


class ProcessPdfObjectsResponse(BaseModel):
    """Response for POST /pdf-files/process-objects endpoint."""
    page_count: int
    objects: PdfObjects
