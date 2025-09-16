"""
PDF Repository
Data access layer for PdfFileModel model operations
"""
import logging
from typing import Optional, List, Dict, Any, TYPE_CHECKING
from datetime import datetime, timezone
from sqlalchemy.exc import SQLAlchemyError
from .base_repository import BaseRepository, RepositoryError
from ..models import PdfFileModel

if TYPE_CHECKING:
    from src.features.pdf_processing.types import PdfFile


logger = logging.getLogger(__name__)


class PdfRepository(BaseRepository[PdfFileModel]):
    """Repository for PdfFileModel model operations"""
    
    @property
    def model_class(self):
        return PdfFileModel
    
    def _convert_to_domain_object(self, pdf_model: PdfFileModel) -> "PdfFile":
        """Convert database model to domain object while session is active"""
        pdf_data = {
            'id': getattr(pdf_model, 'id'),
            'email_id': getattr(pdf_model, 'email_id'),
            'filename': getattr(pdf_model, 'filename'),
            'original_filename': getattr(pdf_model, 'original_filename'),
            'file_path': getattr(pdf_model, 'file_path'),
            'file_size': getattr(pdf_model, 'file_size'),
            'sha256_hash': getattr(pdf_model, 'sha256_hash'),
            'mime_type': getattr(pdf_model, 'mime_type') or 'application/pdf',
            'page_count': getattr(pdf_model, 'page_count'),
            'object_count': getattr(pdf_model, 'object_count'),
            'objects_json': getattr(pdf_model, 'objects_json'),
            'created_at': getattr(pdf_model, 'created_at'),
            'updated_at': getattr(pdf_model, 'updated_at')
        }
        # Import PdfFile dynamically to avoid circular imports
        from src.features.pdf_processing.types import PdfFile
        return PdfFile(**pdf_data)
    
    def get_by_id(self, id: int) -> Optional["PdfFile"]:
        """Override BaseRepository method to return domain object"""
        try:
            with self.connection_manager.session_scope() as session:
                # Get the model from the session using SQLAlchemy 2.x pattern
                model = session.get(self.model_class, id)
                
                if model:
                    # Convert to domain object while session is still active
                    logger.debug(f"Retrieved PDF: {getattr(model, 'filename')} from email {getattr(model, 'email_id')}")
                    return self._convert_to_domain_object(model)
                else:
                    return None
        except SQLAlchemyError as e:
            logger.error(f"Error getting PDF {id}: {e}")
            raise RepositoryError(f"Failed to get PDF: {e}") from e
    
    def get_by_email_id(self, email_id: int) -> List["PdfFile"]:
        """Get all PDF files for a specific email - returns domain objects"""
        if email_id is None:
            return []
        
        try:
            with self.connection_manager.session_scope() as session:
                models = session.query(self.model_class).filter(
                    self.model_class.email_id == email_id
                ).all()
                
                # Convert all models to domain objects
                return [self._convert_to_domain_object(model) for model in models]
                
        except SQLAlchemyError as e:
            logger.error(f"Error getting PDFs for email {email_id}: {e}")
            raise RepositoryError(f"Failed to get PDFs for email: {e}") from e
    
    def get_by_hash(self, sha256_hash: str) -> List["PdfFile"]:
        """Get PDF files by SHA256 hash (may be multiple)"""
        if not sha256_hash:
            return []
        
        try:
            with self.connection_manager.session_scope() as session:
                models = session.query(self.model_class).filter(
                    self.model_class.sha256_hash == sha256_hash
                ).all()
                
                # Convert all models to domain objects
                return [self._convert_to_domain_object(model) for model in models]
                
        except SQLAlchemyError as e:
            logger.error(f"Error getting PDFs by hash {sha256_hash}: {e}")
            raise RepositoryError(f"Failed to get PDFs by hash: {e}") from e
    
    def get_by_filename(self, filename: str) -> List["PdfFile"]:
        """Get PDF files by filename"""
        if not filename:
            return []   
        
        try:
            with self.connection_manager.session_scope() as session:
                models = session.query(self.model_class).filter(
                    self.model_class.filename == filename
                ).all()
                
                # Convert all models to domain objects
                return [self._convert_to_domain_object(model) for model in models]
                
        except SQLAlchemyError as e:
            logger.error(f"Error getting PDFs by filename {filename}: {e}")
            raise RepositoryError(f"Failed to get PDFs by filename: {e}") from e

    # === Phase 1: Essential PDF Repository Methods ===
    
    def create_pdf_record(self, pdf_data: Dict[str, Any]) -> "PdfFile":
        """
        Create PDF record and return the domain object
        
        Args:
            pdf_data: Dictionary containing PDF metadata
            
        Returns:
            PdfFile: Created PDF domain object
        """
        try:
            # Ensure required fields are present
            required_fields = ['email_id', 'filename', 'original_filename', 'file_path', 'file_size', 'sha256_hash']
            for field in required_fields:
                if field not in pdf_data:
                    raise ValueError(f"Required field '{field}' missing from pdf_data")
            
            # Add default values for optional fields
            pdf_data.setdefault('mime_type', 'application/pdf')
            pdf_data.setdefault('created_at', datetime.now(timezone.utc))
            pdf_data.setdefault('updated_at', datetime.now(timezone.utc))
            
            # Create the record using base repository method
            pdf_record = self.create(pdf_data)
            
            logger.debug(f"Created PDF record {pdf_record.id} for email {pdf_data['email_id']}: {pdf_data['filename']}")
            
            # Convert to domain object before returning
            with self.connection_manager.session_scope() as session:
                fresh_model = session.get(self.model_class, pdf_record.id)
                if fresh_model:
                    return self._convert_to_domain_object(fresh_model)
                else:
                    raise RepositoryError(f"Failed to retrieve created PDF record {pdf_record.id}")
            
        except Exception as e:
            logger.error(f"Error creating PDF record: {e}")
            raise RepositoryError(f"Failed to create PDF record: {e}") from e
    
    def exists_by_hash(self, sha256_hash: str) -> bool:
        """
        Quick check if PDF with this hash already exists
        
        Args:
            sha256_hash: SHA256 hash to check
            
        Returns:
            bool: True if PDF with this hash exists
        """
        if not sha256_hash:
            return False
            
        try:
            with self.connection_manager.session_scope() as session:
                exists = session.query(self.model_class).filter(
                    self.model_class.sha256_hash == sha256_hash
                ).first() is not None
                
                logger.debug(f"Hash {sha256_hash[:16]}... exists: {exists}")
                return exists
                
        except SQLAlchemyError as e:
            logger.error(f"Error checking if hash exists {sha256_hash}: {e}")
            raise RepositoryError(f"Failed to check hash existence: {e}") from e
    
    def get_duplicate_by_hash(self, sha256_hash: str) -> Optional["PdfFile"]:
        """
        Get existing PDF with same hash for deduplication
        
        Args:
            sha256_hash: SHA256 hash to find duplicate for
            
        Returns:
            Optional[PdfFile]: Existing PDF domain object or None
        """
        if not sha256_hash:
            return None
            
        try:
            with self.connection_manager.session_scope() as session:
                model = session.query(self.model_class).filter(
                    self.model_class.sha256_hash == sha256_hash
                ).first()
                
                if model:
                    logger.debug(f"Found duplicate PDF by hash {sha256_hash[:16]}...: {model.filename}")
                    return self._convert_to_domain_object(model)
                else:
                    return None
                    
        except SQLAlchemyError as e:
            logger.error(f"Error getting duplicate by hash {sha256_hash}: {e}")
            raise RepositoryError(f"Failed to get duplicate by hash: {e}") from e
    
    def update_pdf_processing_status(self, pdf_id: int, status_data: Dict[str, Any]) -> Optional["PdfFile"]:
        """
        Update PDF processing metadata (page_count, object_count, etc.)
        
        Args:
            pdf_id: PDF ID to update
            status_data: Dictionary with processing status updates
            
        Returns:
            Optional[PdfFile]: Updated PDF domain object or None
        """
        if pdf_id is None:
            raise ValueError("pdf_id cannot be None")
            
        try:
            # Add timestamp for update tracking
            status_data['updated_at'] = datetime.now(timezone.utc)
            
            # Update using base repository method
            updated_model = self.update(pdf_id, status_data)
            
            if updated_model:
                logger.debug(f"Updated processing status for PDF {pdf_id}: {list(status_data.keys())}")
                # Convert to domain object (need to fetch from session to get latest data)
                with self.connection_manager.session_scope() as session:
                    fresh_model = session.get(self.model_class, pdf_id)
                    if fresh_model:
                        return self._convert_to_domain_object(fresh_model)
            
            return None
            
        except Exception as e:
            logger.error(f"Error updating PDF processing status for {pdf_id}: {e}")
            raise RepositoryError(f"Failed to update PDF processing status: {e}") from e
    
    def update_objects_json(self, pdf_id: int, objects_json: str) -> Optional["PdfFile"]:
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
                
                # Convert to domain object before returning
                with self.connection_manager.session_scope() as session:
                    fresh_model = session.get(self.model_class, pdf_id)
                    if fresh_model:
                        return self._convert_to_domain_object(fresh_model)
            
            return None
            
        except Exception as e:
            logger.error(f"Error updating objects_json for PDF {pdf_id}: {e}")
            raise RepositoryError(f"Failed to update objects_json: {e}") from e