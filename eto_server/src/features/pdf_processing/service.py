"""
PDF Processing Service
Consolidated service for all PDF operations including storage, extraction, and retrieval
"""
import json
import logging
from typing import Optional, List, Dict, Any, cast
from datetime import datetime

from shared.database.connection import DatabaseConnectionManager
from shared.database.repositories.pdf_file import PdfFileRepository
from shared.models.pdf_file import PdfFile, PdfFileCreate, PdfFileSummary
from shared.models.pdf_processing_new import PdfDetailData
from shared.exceptions import ServiceError

from .utils import (
    calculate_file_hash,
    extract_pdf_metadata,
    extract_pdf_objects,
    validate_pdf,
    save_pdf_to_disk,
    read_pdf_from_disk,
    ensure_storage_directory,
    get_storage_info
)

logger = logging.getLogger(__name__)


class PdfProcessingService:
    """
    Consolidated service for all PDF processing operations
    Handles storage, extraction, and retrieval of PDF files
    """
    
    def __init__(self, storage_path: str, connection_manager: DatabaseConnectionManager):
        """
        Initialize PDF processing service
        
        Args:
            storage_path: Base path for PDF file storage
            connection_manager: Database connection manager
        """
        self.storage_path = storage_path
        self.pdf_repository = PdfFileRepository(connection_manager)
        
        # Ensure storage directory exists
        if not ensure_storage_directory(storage_path):
            logger.error(f"Failed to create storage directory at {storage_path}")
            raise ServiceError(f"Cannot initialize PDF storage at {storage_path}")
        
        logger.info(f"PDF Processing Service initialized with storage at {storage_path}")
    
    # === Core PDF Operations ===
    
    def store_pdf(self, 
                  file_content: bytes, 
                  original_filename: str,
                  email_id: Optional[int] = None) -> PdfFile:
        """
        Main entry point for storing any PDF
        - Validates PDF
        - Calculates hash for deduplication
        - Extracts objects and text upfront
        - Stores file on disk
        - Creates DB record with all extracted data
        
        Args:
            file_content: PDF file content as bytes
            original_filename: Original name of the PDF file
            email_id: Optional ID of associated email (None for manual uploads)
            
        Returns:
            PdfFile domain object with all metadata
            
        Raises:
            ServiceError: If PDF is invalid or storage fails
        """
        try:
            # Step 1: Validate PDF
            is_valid, error_msg = validate_pdf(file_content)
            if not is_valid:
                raise ServiceError(f"Invalid PDF: {error_msg}")
            
            # Step 2: Calculate hash for deduplication
            file_hash = calculate_file_hash(file_content)
            
            # Step 3: Check for duplicate
            existing = self.pdf_repository.get_by_hash(file_hash)
            if existing:
                logger.info(f"PDF with hash {file_hash} already exists (ID: {existing.id})")
                return existing
            
            # Step 4: Extract all data upfront
            logger.info(f"Processing new PDF: {original_filename}")
            
            # Extract metadata
            metadata = extract_pdf_metadata(file_content)
            file_size = metadata.get('file_size', len(file_content))

            # Extract objects using new enhanced extractor
            extraction_result = extract_pdf_objects(file_content)

            if not extraction_result['success']:
                logger.warning(f"PDF extraction partially failed: {extraction_result.get('error_message', 'Unknown error')}")

            # Get data from extraction result (more reliable than metadata)
            pdf_objects = extraction_result['objects']
            page_count = extraction_result['page_count']  # Use page count from extractor

            # Log extraction results
            logger.info(f"Extracted {extraction_result['object_count']} objects from {page_count} pages")

            # Step 5: Store file on disk
            relative_path = save_pdf_to_disk(
                file_content=file_content,
                storage_base=self.storage_path,
                file_hash=file_hash,
                original_filename=original_filename
            )

            # Step 6: Create database record with all extracted data
            pdf_create = PdfFileCreate(
                filename=file_hash + '.pdf',  # Storage filename
                original_filename=original_filename,
                relative_path=relative_path,
                file_hash=file_hash,
                file_size=file_size,
                page_count=page_count,
                object_count=len(pdf_objects) if pdf_objects else 0,
                email_id=email_id,
                objects_json=cast(List[Dict[str, Any]], pdf_objects or [])
            )
            
            pdf_file = self.pdf_repository.create(pdf_create)
            
            logger.info(f"Successfully stored PDF {pdf_file.id}: {original_filename}")
            return pdf_file
            
        except ServiceError:
            raise
        except Exception as e:
            logger.error(f"Error storing PDF {original_filename}: {e}")
            raise ServiceError(f"Failed to store PDF: {str(e)}")
    
    # === Retrieval Operations ===
    
    def get_pdf(self, pdf_id: int) -> Optional[PdfFile]:
        """
        Get PDF metadata from database
        
        Args:
            pdf_id: PDF file ID
            
        Returns:
            PdfFile domain object or None if not found
        """
        return self.pdf_repository.get_by_id(pdf_id)
    
    def get_pdf_content(self, pdf_id: int) -> Optional[bytes]:
        """
        Read PDF file content from disk
        
        Args:
            pdf_id: PDF file ID
            
        Returns:
            PDF file content as bytes, or None if not found
        """
        pdf_file = self.get_pdf(pdf_id)
        if not pdf_file:
            return None
        
        return read_pdf_from_disk(self.storage_path, pdf_file.relative_path)
    
    def get_pdfs_by_email(self, email_id: int) -> List[PdfFile]:
        """
        Get all PDFs associated with an email
        
        Args:
            email_id: Email ID
            
        Returns:
            List of PdfFile domain objects
        """
        return self.pdf_repository.get_by_email(email_id)
    
    def get_manual_uploads(self, limit: Optional[int] = None, offset: Optional[int] = None) -> List[PdfFile]:
        """
        Get user-uploaded PDFs (no email association)
        
        Args:
            limit: Maximum number of results
            offset: Number of results to skip
            
        Returns:
            List of PdfFile domain objects
        """
        return self.pdf_repository.get_manual_uploads(limit=limit, offset=offset)
    
    def get_all_pdfs(self, 
                     has_email: Optional[bool] = None,
                     limit: Optional[int] = None,
                     offset: Optional[int] = None) -> List[PdfFile]:
        """
        Get all PDFs with optional filtering
        
        Args:
            has_email: Filter by email association
            limit: Maximum number of results
            offset: Number of results to skip
            
        Returns:
            List of PdfFile domain objects
        """
        return self.pdf_repository.get_all(
            has_email=has_email,
            limit=limit,
            offset=offset
        )
    
    def get_pdf_summaries(self,
                          has_email: Optional[bool] = None,
                          limit: Optional[int] = None,
                          offset: Optional[int] = None) -> List[PdfFileSummary]:
        """
        Get PDF summaries for list views
        
        Args:
            has_email: Filter by email association
            limit: Maximum number of results
            offset: Number of results to skip
            
        Returns:
            List of PdfFileSummary objects
        """
        return self.pdf_repository.get_summaries(
            has_email=has_email,
            limit=limit,
            offset=offset
        )
    
    def get_pdf_objects(self, pdf_id: int) -> Optional[List[Dict[str, Any]]]:
        """
        Get extracted PDF objects for a specific PDF

        Args:
            pdf_id: PDF file ID

        Returns:
            List of PDF objects as dictionaries, or None if not found
        """
        pdf_file = self.get_pdf(pdf_id)
        if not pdf_file or not pdf_file.objects_json:
            return None

        # Convert PdfObject instances to dictionaries
        return [obj.model_dump() for obj in pdf_file.objects_json]

    def get_pdf_detail_data(self, pdf_id: int) -> Optional[PdfDetailData]:
        """
        Get detailed PDF data with objects grouped by type for template builder

        Args:
            pdf_id: PDF file ID

        Returns:
            PdfDetailData with file info, email context, and objects grouped by type
        """
        try:
            detail_data = self.pdf_repository.get_pdf_from_id_detail(pdf_id)
            if not detail_data:
                logger.debug(f"PDF detail data not found for ID {pdf_id}")
                return None

            logger.info(f"Retrieved PDF detail data for ID {pdf_id}: {detail_data.total_object_count} objects")
            return detail_data

        except Exception as e:
            logger.error(f"Error getting PDF detail data for {pdf_id}: {e}")
            raise ServiceError(f"Failed to get PDF detail data: {e}") from e


    # === Utility Operations ===
    
    def check_duplicate(self, file_content: bytes) -> Optional[PdfFile]:
        """
        Check if a PDF already exists by hash
        
        Args:
            file_content: PDF content to check
            
        Returns:
            Existing PdfFile if duplicate found, None otherwise
        """
        file_hash = calculate_file_hash(file_content)
        return self.pdf_repository.get_by_hash(file_hash)
    
    def get_storage_info(self) -> Dict[str, Any]:
        """
        Get storage statistics
        
        Returns:
            Dictionary with storage information
        """
        storage_stats = get_storage_info(self.storage_path)
        
        # Add database statistics
        total_pdfs = self.pdf_repository.count()
        email_pdfs = self.pdf_repository.count(has_email=True)
        manual_pdfs = self.pdf_repository.count(has_email=False)
        
        return {
            **storage_stats,
            'database': {
                'total_pdfs': total_pdfs,
                'email_pdfs': email_pdfs,
                'manual_uploads': manual_pdfs
            }
        }
    
    # === API Helper Methods ===
    
    def get_pdf_metadata(self, pdf_id: int) -> Optional[Dict[str, Any]]:
        """
        Get PDF metadata for API consumption
        
        Args:
            pdf_id: PDF file ID
            
        Returns:
            Dict with PDF metadata or None if not found
        """
        pdf_file = self.get_pdf(pdf_id)
        if not pdf_file:
            return None
        
        return {
            "id": pdf_file.id,
            "original_filename": pdf_file.original_filename,
            "file_hash": pdf_file.file_hash,
            "file_size": pdf_file.file_size,
            "page_count": pdf_file.page_count,
            "email_id": pdf_file.email_id,
            "has_extracted_objects": bool(pdf_file.objects_json),
            "created_at": pdf_file.created_at.isoformat() if pdf_file.created_at else None,
            "updated_at": pdf_file.updated_at.isoformat() if pdf_file.updated_at else None
        }

    def is_healthy(self) -> bool:
        """
        Check if the PDF processing service is healthy

        Returns:
            True if service is operational, False otherwise
        """
        try:
            # Check if storage directory is accessible
            import os
            if not os.path.exists(self.storage_path):
                return False

            # Check if we can access the repository
            self.pdf_repository.count()

            return True
        except Exception as e:
            logger.error(f"PDF processing service health check failed: {e}")
            return False