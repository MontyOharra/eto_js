"""
PDF Processing Service
Standalone service for all PDF-related operations including storage, extraction, and management.
This service can be shared across multiple features (email ingestion, manual upload, ETO processing).
"""
import logging
from typing import Optional, List, Dict, Any
from datetime import datetime, timezone

from ...shared.database import get_connection_manager
from ...shared.database.repositories import PdfRepository
from .storage_service import PdfStorageService
from .object_extraction_service import PdfObjectExtractionService
from .types import PdfFile, PdfStoreRequest

logger = logging.getLogger(__name__)


class PdfProcessingService:
    """
    Standalone PDF processing service that handles all PDF-related operations.
    Can be shared across multiple features for consistent PDF handling.
    """
    
    def __init__(self, storage_path: str):
        """
        Initialize PDF processing service with storage configuration
        
        Args:
            storage_path: Path for PDF file storage
        """
        # Database connection
        self.connection_manager = get_connection_manager()
        if not self.connection_manager:
            raise RuntimeError("Database connection manager is required")
        
        # Repository layer
        self.pdf_repo = PdfRepository(self.connection_manager)
        
        # Service dependencies
        self.storage_service = PdfStorageService(storage_path, self.pdf_repo)
        self.extraction_service = PdfObjectExtractionService()
        
        logger.info(f"PDF Processing Service initialized with storage path: {storage_path}")
    
    # === Core PDF Management Methods ===
    
    def store_pdf(self, content_bytes: bytes, store_request: PdfStoreRequest) -> PdfFile:
        """
        Store PDF file and create database record using domain objects
        
        Args:
            content_bytes: PDF file content
            store_request: Domain object with storage request details
            
        Returns:
            PdfFile: Created PDF domain object
        """
        try:
            # Delegate complete storage workflow to storage service
            return self.storage_service.store_pdf_complete(content_bytes, store_request)
            
        except Exception as e:
            logger.error(f"Error storing PDF: {e}")
            raise
    
    def extract_pdf_objects(self, pdf_id: int) -> Dict[str, Any]:
        """
        Extract objects from stored PDF and update database record
        
        Args:
            pdf_id: PDF ID to extract objects from
            
        Returns:
            Dict: Extraction result with objects and metadata
        """
        try:
            # Get PDF file record
            pdf_file = self.pdf_repo.get_by_id(pdf_id)
            if not pdf_file:
                raise ValueError(f"PDF {pdf_id} not found")
            
            # Get PDF content using storage service
            pdf_content = self.storage_service.retrieve_pdf_content(pdf_file.file_path)
            if not pdf_content:
                raise ValueError(f"PDF content not found for {pdf_id}")
            
            # Extract objects using extraction service
            extraction_result = self.extraction_service.extract_objects_from_bytes(pdf_content)
            
            if extraction_result.get('success'):
                # Update database with extracted objects
                objects_json = extraction_result.get('objects_json', '[]')
                self.pdf_repo.update_objects_json(pdf_id, objects_json)
                
                logger.info(f"Extracted {extraction_result.get('object_count', 0)} objects from PDF {pdf_id}")
            else:
                logger.warning(f"Object extraction failed for PDF {pdf_id}: {extraction_result.get('error')}")
            
            return extraction_result
            
        except Exception as e:
            logger.error(f"Error extracting objects from PDF {pdf_id}: {e}")
            raise
    
    # === API Access Methods ===
    
    def get_pdf_metadata(self, pdf_id: int) -> Optional[Dict[str, Any]]:
        """
        Get PDF metadata for API consumption
        
        Args:
            pdf_id: PDF file ID
            
        Returns:
            Dict with PDF metadata or None if not found
        """
        try:
            pdf_file = self.pdf_repo.get_by_id(pdf_id)
            if not pdf_file:
                return None
            
            return {
                "id": pdf_file.id,
                "email_id": pdf_file.email_id,
                "filename": pdf_file.filename,
                "original_filename": pdf_file.original_filename,
                "file_size": pdf_file.file_size,
                "sha256_hash": pdf_file.sha256_hash,
                "mime_type": pdf_file.mime_type,
                "page_count": pdf_file.page_count,
                "object_count": pdf_file.object_count,
                "created_at": pdf_file.created_at.isoformat() if pdf_file.created_at else None,
                "updated_at": pdf_file.updated_at.isoformat() if pdf_file.updated_at else None
            }
            
        except Exception as e:
            logger.error(f"Error getting PDF metadata for {pdf_id}: {e}")
            return None
    
    def get_pdf_content(self, pdf_id: int) -> Optional[bytes]:
        """
        Get PDF file content for download
        
        Args:
            pdf_id: PDF file ID
            
        Returns:
            PDF content bytes or None if not found
        """
        try:
            pdf_file = self.pdf_repo.get_by_id(pdf_id)
            if not pdf_file or not pdf_file.file_path:
                return None
            
            return self.storage_service.retrieve_pdf_content(pdf_file.file_path)
            
        except Exception as e:
            logger.error(f"Error getting PDF content for {pdf_id}: {e}")
            return None
    
    def get_pdfs_by_email(self, email_id: int, limit: Optional[int] = None) -> List[Dict[str, Any]]:
        """
        Get all PDFs for a specific email
        
        Args:
            email_id: Email ID
            limit: Optional limit on number of results
            
        Returns:
            List of PDF metadata dictionaries
        """
        try:
            pdf_files = self.pdf_repo.get_by_email_id(email_id)
            
            if limit:
                pdf_files = pdf_files[:limit]
            
            return [
                {
                    "id": pdf.id,
                    "email_id": pdf.email_id,
                    "filename": pdf.filename,
                    "original_filename": pdf.original_filename,
                    "file_size": pdf.file_size,
                    "sha256_hash": pdf.sha256_hash,
                    "mime_type": pdf.mime_type,
                    "page_count": pdf.page_count,
                    "object_count": pdf.object_count,
                    "created_at": pdf.created_at.isoformat() if pdf.created_at else None,
                    "updated_at": pdf.updated_at.isoformat() if pdf.updated_at else None
                }
                for pdf in pdf_files
            ]
            
        except Exception as e:
            logger.error(f"Error getting PDFs for email {email_id}: {e}")
            return []
    
    def get_pdf_by_id(self, pdf_id: int) -> Optional[PdfFile]:
        """
        Get PDF domain object by ID
        
        Args:
            pdf_id: PDF file ID
            
        Returns:
            PdfFile domain object or None if not found
        """
        try:
            return self.pdf_repo.get_by_id(pdf_id)
        except Exception as e:
            logger.error(f"Error getting PDF {pdf_id}: {e}")
            return None
    
    def get_storage_info(self) -> Dict[str, Any]:
        """
        Get PDF storage service information
        
        Returns:
            Dict with storage information
        """
        try:
            return self.storage_service.get_storage_info()
        except Exception as e:
            logger.error(f"Error getting PDF storage info: {e}")
            return {}
    
    # === Administrative Methods ===
    
    def get_processing_statistics(self) -> Dict[str, Any]:
        """
        Get PDF processing statistics
        
        Returns:
            Dict with processing statistics
        """
        try:
            # This would need to be implemented in the repository if needed
            return {
                "message": "PDF processing statistics not yet implemented"
            }
        except Exception as e:
            logger.error(f"Error getting processing statistics: {e}")
            return {}


# Global service management (optional - for singleton pattern if needed)
_pdf_processing_service: Optional[PdfProcessingService] = None


def get_pdf_processing_service() -> Optional[PdfProcessingService]:
    """Get the global PDF processing service instance"""
    return _pdf_processing_service


def init_pdf_processing_service(storage_path: str) -> PdfProcessingService:
    """Initialize the global PDF processing service"""
    global _pdf_processing_service
    
    if _pdf_processing_service is not None:
        logger.warning("PDF processing service already initialized")
        return _pdf_processing_service
    
    _pdf_processing_service = PdfProcessingService(storage_path)
    logger.info("Global PDF processing service initialized")
    return _pdf_processing_service