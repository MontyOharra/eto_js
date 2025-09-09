"""
PDF Repository
Data access layer for PdfFile model operations
"""
from typing import Optional, List
from .base_repository import BaseRepository
from ..models import PdfFile


class PdfRepository(BaseRepository):
    """Repository for PdfFile model operations"""
    
    @property
    def model_class(self):
        return PdfFile
    
    def get_by_email_id(self, email_id: int) -> List[PdfFile]:
        """Get all PDF files for a specific email"""
        pass
    
    def get_by_hash(self, sha256_hash: str) -> List[PdfFile]:
        """Get PDF files by SHA256 hash (may be multiple)"""
        pass
    
    def get_by_filename(self, filename: str) -> List[PdfFile]:
        """Get PDF files by filename"""
        pass
    
    def get_with_extracted_objects(self, limit: Optional[int] = None) -> List[PdfFile]:
        """Get PDF files that have extracted objects"""
        pass
    
    def get_without_extracted_objects(self, limit: Optional[int] = None) -> List[PdfFile]:
        """Get PDF files that need object extraction"""
        pass
    
    def update_objects_json(self, pdf_id: int, objects_json: str) -> Optional[PdfFile]:
        """Update the objects_json field for a PDF file"""
        pass