"""
PDF File Repository (New)
Repository for PDF file operations using Pydantic models
"""
import logging
from typing import Optional, List
from datetime import datetime, timezone, timedelta
from sqlalchemy.exc import SQLAlchemyError

from shared.database.repositories import BaseRepository
from shared.exceptions import RepositoryError, ObjectNotFoundError
from shared.database.models import PdfFileModel
from shared.database.connection import DatabaseConnectionManager
from shared.models import PdfFile, PdfFileCreate, PdfFileUpdate, PdfFileSummary

logger = logging.getLogger(__name__)


class PdfFileRepository(BaseRepository[PdfFileModel]):
    """Repository for PDF file operations with Pydantic models"""
    
    def __init__(self, connection_manager: DatabaseConnectionManager):
        super().__init__(connection_manager)
    
    @property
    def model_class(self):
        return PdfFileModel
    
    def _convert_to_domain_object(self, model: PdfFileModel) -> PdfFile:
        """Convert SQLAlchemy model to Pydantic domain object"""
        return PdfFile.model_validate(model)
    
    # === Core CRUD Operations ===
    
    def create(self, pdf_create: PdfFileCreate) -> PdfFile:
        """
        Create a new PDF file record
        
        Args:
            pdf_create: PdfFileCreate model with file data
            
        Returns:
            Created PdfFile domain model
        """
        try:
            with self.connection_manager.session_scope() as session:
                # Check for duplicate by hash
                existing = session.query(self.model_class).filter(
                    self.model_class.file_hash == pdf_create.file_hash
                ).first()
                
                if existing:
                    logger.info(f"PDF with hash {pdf_create.file_hash} already exists, returning existing record")
                    return self._convert_to_domain_object(existing)
                
                # Create new record
                model_data = pdf_create.model_dump_for_db()
                model = self.model_class(**model_data)
                
                session.add(model)
                session.flush()
                session.refresh(model)
                
                logger.debug(f"Created PDF file record with ID: {model.id}")
                return self._convert_to_domain_object(model)
                
        except SQLAlchemyError as e:
            logger.error(f"Error creating PDF file record: {e}")
            raise RepositoryError(f"Failed to create PDF file: {e}") from e
    
    def get_by_id(self, pdf_id: int) -> Optional[PdfFile]:
        """
        Get PDF file by ID
        
        Args:
            pdf_id: PDF file ID
            
        Returns:
            PdfFile domain model or None if not found
        """
        try:
            with self.connection_manager.session_scope() as session:
                model = session.get(self.model_class, pdf_id)
                
                if not model:
                    return None
                    
                return self._convert_to_domain_object(model)
                
        except SQLAlchemyError as e:
            logger.error(f"Error getting PDF file {pdf_id}: {e}")
            raise RepositoryError(f"Failed to get PDF file: {e}") from e
    
    def get_by_hash(self, file_hash: str) -> Optional[PdfFile]:
        """
        Get PDF file by hash for deduplication checks
        
        Args:
            file_hash: SHA256 hash of the file
            
        Returns:
            PdfFile domain model or None if not found
        """
        try:
            with self.connection_manager.session_scope() as session:
                model = session.query(self.model_class).filter(
                    self.model_class.file_hash == file_hash
                ).first()
                
                if not model:
                    return None
                    
                return self._convert_to_domain_object(model)
                
        except SQLAlchemyError as e:
            logger.error(f"Error getting PDF file by hash {file_hash}: {e}")
            raise RepositoryError(f"Failed to get PDF file by hash: {e}") from e
    
    def exists_by_hash(self, file_hash: str) -> bool:
        """
        Check if PDF with given hash exists (for quick deduplication)
        
        Args:
            file_hash: SHA256 hash to check
            
        Returns:
            True if PDF with hash exists
        """
        try:
            with self.connection_manager.session_scope() as session:
                exists = session.query(
                    session.query(self.model_class).filter(
                        self.model_class.file_hash == file_hash
                    ).exists()
                ).scalar()
                
                return exists
                
        except SQLAlchemyError as e:
            logger.error(f"Error checking PDF hash existence: {e}")
            raise RepositoryError(f"Failed to check PDF hash: {e}") from e
    
    def update(self, pdf_id: int, update_data: PdfFileUpdate) -> Optional[PdfFile]:
        """
        Update PDF file metadata (mainly extracted text/objects if re-processing)
        
        Args:
            pdf_id: PDF file ID to update
            update_data: PdfFileUpdate with fields to update
            
        Returns:
            Updated PdfFile or None if not found
        """
        try:
            with self.connection_manager.session_scope() as session:
                model = session.get(self.model_class, pdf_id)
                
                if not model:
                    return None
                
                # Update only provided fields
                update_dict = update_data.model_dump_for_db()
                for field, value in update_dict.items():
                    if hasattr(model, field):
                        setattr(model, field, value)
                
                # Update timestamp
                model.updated_at = datetime.now(timezone.utc)
                
                session.flush()
                session.refresh(model)
                
                logger.debug(f"Updated PDF file with ID: {pdf_id}")
                return self._convert_to_domain_object(model)
                
        except SQLAlchemyError as e:
            logger.error(f"Error updating PDF file {pdf_id}: {e}")
            raise RepositoryError(f"Failed to update PDF file: {e}") from e
    
    # === Query Methods ===
    
    def get_by_email(self, email_id: int) -> List[PdfFile]:
        """
        Get all PDF files associated with an email
        
        Args:
            email_id: Email ID to get PDFs for
            
        Returns:
            List of PdfFile domain models
        """
        try:
            with self.connection_manager.session_scope() as session:
                models = session.query(self.model_class).filter(
                    self.model_class.email_id == email_id
                ).order_by(self.model_class.created_at).all()
                
                return [self._convert_to_domain_object(model) for model in models]
                
        except SQLAlchemyError as e:
            logger.error(f"Error getting PDFs for email {email_id}: {e}")
            raise RepositoryError(f"Failed to get PDFs by email: {e}") from e
    
    def get_manual_uploads(self, limit: Optional[int] = None, offset: Optional[int] = None) -> List[PdfFile]:
        """
        Get PDF files that were manually uploaded (no email_id)
        
        Args:
            limit: Maximum number of results
            offset: Number of results to skip
            
        Returns:
            List of PdfFile domain models
        """
        try:
            with self.connection_manager.session_scope() as session:
                query = session.query(self.model_class).filter(
                    self.model_class.email_id.is_(None)
                ).order_by(self.model_class.created_at.desc())
                
                if offset is not None:
                    query = query.offset(offset)
                    
                if limit is not None:
                    query = query.limit(limit)
                
                models = query.all()
                return [self._convert_to_domain_object(model) for model in models]
                
        except SQLAlchemyError as e:
            logger.error(f"Error getting manual upload PDFs: {e}")
            raise RepositoryError(f"Failed to get manual uploads: {e}") from e
    
    def get_all(self, 
                has_email: Optional[bool] = None,
                limit: Optional[int] = None, 
                offset: Optional[int] = None) -> List[PdfFile]:
        """
        Get all PDF files with optional filtering
        
        Args:
            has_email: Filter by whether PDF has associated email
            limit: Maximum number of results
            offset: Number of results to skip
            
        Returns:
            List of PdfFile domain models
        """
        try:
            with self.connection_manager.session_scope() as session:
                query = session.query(self.model_class)
                
                # Apply filters
                if has_email is not None:
                    if has_email:
                        query = query.filter(self.model_class.email_id.isnot(None))
                    else:
                        query = query.filter(self.model_class.email_id.is_(None))
                
                # Order by creation date (newest first)
                query = query.order_by(self.model_class.created_at.desc())
                
                if offset is not None:
                    query = query.offset(offset)
                    
                if limit is not None:
                    query = query.limit(limit)
                
                models = query.all()
                return [self._convert_to_domain_object(model) for model in models]
                
        except SQLAlchemyError as e:
            logger.error(f"Error getting all PDF files: {e}")
            raise RepositoryError(f"Failed to get PDF files: {e}") from e
    
    def get_summaries(self, 
                      has_email: Optional[bool] = None,
                      limit: Optional[int] = None, 
                      offset: Optional[int] = None) -> List[PdfFileSummary]:
        """
        Get PDF file summaries for list views
        
        Args:
            has_email: Filter by whether PDF has associated email
            limit: Maximum number of results
            offset: Number of results to skip
            
        Returns:
            List of PdfFileSummary models
        """
        # Get full models and convert to summaries
        pdfs = self.get_all(has_email=has_email, limit=limit, offset=offset)
        return [PdfFileSummary.from_pdf_file(pdf) for pdf in pdfs]
    
    def count(self, has_email: Optional[bool] = None) -> int:
        """
        Count PDF files with optional filtering
        
        Args:
            has_email: Filter by whether PDF has associated email
            
        Returns:
            Count of PDF files
        """
        try:
            with self.connection_manager.session_scope() as session:
                query = session.query(self.model_class)
                
                if has_email is not None:
                    if has_email:
                        query = query.filter(self.model_class.email_id.isnot(None))
                    else:
                        query = query.filter(self.model_class.email_id.is_(None))
                
                return query.count()
                
        except SQLAlchemyError as e:
            logger.error(f"Error counting PDF files: {e}")
            raise RepositoryError(f"Failed to count PDF files: {e}") from e
    
    def get_recent(self, days: int = 7, limit: int = 100) -> List[PdfFile]:
        """
        Get recently added PDF files
        
        Args:
            days: Number of days to look back
            limit: Maximum number of results
            
        Returns:
            List of recent PdfFile domain models
        """
        try:
            with self.connection_manager.session_scope() as session:
                cutoff_date = datetime.now(timezone.utc) - timedelta(days=days)
                
                models = session.query(self.model_class).filter(
                    self.model_class.created_at >= cutoff_date
                ).order_by(
                    self.model_class.created_at.desc()
                ).limit(limit).all()
                
                return [self._convert_to_domain_object(model) for model in models]
                
        except SQLAlchemyError as e:
            logger.error(f"Error getting recent PDF files: {e}")
            raise RepositoryError(f"Failed to get recent PDFs: {e}") from e