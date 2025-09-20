"""
PDF Processing Domain Types
Domain objects for PDF file processing and analysis
"""
from dataclasses import dataclass
from typing import Optional, List
from datetime import datetime


@dataclass 
class PdfFile:
    """PDF file domain object"""
    id: int
    email_id: Optional[int]  # Made optional for manual uploads
    filename: str
    file_path: str
    file_size: int
    sha256_hash: str
    created_at: datetime
    updated_at: datetime
    page_count: Optional[int] = None
    object_count: Optional[int] = None
    objects_json: Optional[str] = None
    
@dataclass
class PdfFileCreate:
    """Domain object for creating PDF files (no ID)"""
    email_id: Optional[int]
    filename: str


@dataclass
class PdfObject:
    """Individual PDF object for template matching"""
    type: str  # 'word', 'text_line', 'rect', 'line', 'image', etc.
    page: int
    text: str  # content for text objects, empty for shapes/images
    x: float
    y: float
    width: float
    height: float
    font_name: Optional[str] = None
    font_size: Optional[float] = None
    char_count: Optional[int] = None
    bbox: Optional[List[float]] = None


@dataclass
class PdfObjectExtractionResult:
    """Service-level result for PDF object extraction (no pdf_id)"""
    success: bool
    objects: List[PdfObject]
    signature_hash: Optional[str]
    page_count: int
    object_count: int
    error_message: Optional[str] = None
    
    
@dataclass
class PdfStoreRequest:
    """Domain object for storing any PDF (email, manual, API)"""
    original_filename: str
    email_id: Optional[int] = None  # None for manual/API uploads
    filename: Optional[str] = None  # Auto-generated if None