"""
PDF Repository
Data access layer for PdfFile model operations
"""
import logging
from typing import Optional, List
from sqlalchemy.exc import SQLAlchemyError
from .base_repository import BaseRepository, RepositoryError
from ..models import PdfFile


logger = logging.getLogger(__name__)


class PdfRepository(BaseRepository[PdfFile]):
    """Repository for PdfFile model operations"""
    
    @property
    def model_class(self):
        return PdfFile
    
    def get_by_email_id(self, email_id: int) -> List[PdfFile]:
        """Get all PDF files for a specific email"""
        if email_id is None:
            return []
        
        return self.get_by_field('email_id', email_id)
    
    def get_by_hash(self, sha256_hash: str) -> List[PdfFile]:
        """Get PDF files by SHA256 hash (may be multiple)"""
        if not sha256_hash:
            return []
        
        return self.get_by_field('sha256_hash', sha256_hash)
    
    def get_by_filename(self, filename: str) -> List[PdfFile]:
        """Get PDF files by filename"""
        if not filename:
            return []
        
        return self.get_by_field('filename', filename)
    
    def get_with_extracted_objects(self, limit: Optional[int] = None) -> List[PdfFile]:
        """Get PDF files that have extracted objects"""
        try:
            with self.connection_manager.session_scope() as session:
                query = session.query(self.model_class).filter(
                    self.model_class.objects_json.isnot(None),
                    self.model_class.objects_json != ''
                ).order_by(self.model_class.created_at.desc())
                
                if limit is not None:
                    query = query.limit(limit)
                
                return query.all()
                
        except SQLAlchemyError as e:
            logger.error(f"Error getting PDF files with extracted objects: {e}")
            raise RepositoryError(f"Failed to get PDF files with extracted objects: {e}") from e
    
    def get_without_extracted_objects(self, limit: Optional[int] = None) -> List[PdfFile]:
        """Get PDF files that need object extraction"""
        try:
            with self.connection_manager.session_scope() as session:
                query = session.query(self.model_class).filter(
                    (self.model_class.objects_json.is_(None)) | 
                    (self.model_class.objects_json == '')
                ).order_by(self.model_class.created_at.asc())
                
                if limit is not None:
                    query = query.limit(limit)
                
                return query.all()
                
        except SQLAlchemyError as e:
            logger.error(f"Error getting PDF files without extracted objects: {e}")
            raise RepositoryError(f"Failed to get PDF files without extracted objects: {e}") from e
    
    def update_objects_json(self, pdf_id: int, objects_json: str) -> Optional[PdfFile]:
        """Update the objects_json field for a PDF file"""
        if pdf_id is None:
            raise ValueError("pdf_id cannot be None")
        
        if objects_json is None:
            raise ValueError("objects_json cannot be None")
        
        try:
            # Parse objects_json to count objects if it's valid JSON
            import json
            try:
                parsed_objects = json.loads(objects_json) if objects_json else []
                object_count = len(parsed_objects) if isinstance(parsed_objects, list) else 0
            except json.JSONDecodeError:
                logger.warning(f"Invalid JSON provided for objects_json in PDF {pdf_id}")
                object_count = 0
            
            update_data = {
                'objects_json': objects_json,
                'object_count': object_count
            }
            
            updated_pdf = self.update(pdf_id, update_data)
            if updated_pdf:
                logger.debug(f"Updated objects_json for PDF {pdf_id} with {object_count} objects")
            
            return updated_pdf
            
        except Exception as e:
            logger.error(f"Error updating objects_json for PDF {pdf_id}: {e}")
            raise RepositoryError(f"Failed to update objects_json: {e}") from e