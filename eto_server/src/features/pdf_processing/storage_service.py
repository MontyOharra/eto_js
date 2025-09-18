"""
PDF Storage Service
Handles complete PDF storage workflow including file operations and database persistence
"""
import logging
import hashlib
import os
import re
import tempfile
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, Optional

from shared.database.repositories.pdf_repository import PdfRepository

from shared.domain import PdfStoreRequest, PdfFile


logger = logging.getLogger(__name__)


class PdfStorageService:
    """Service for managing complete PDF storage workflow with database integration"""
    
    def __init__(self, storage_root: str, pdf_repository: PdfRepository):
        """
        Initialize PDF storage service with auto-creation and fallback
        
        Args:
            storage_root: Root directory for PDF storage
            pdf_repository: Repository for PDF database operations
        """
        self.original_storage_root = storage_root
        self.storage_root = Path(storage_root)
        self.pdf_root = self.storage_root / "pdfs"
        self.pdf_repo = pdf_repository
        
        # Initialize storage directories with auto-creation and fallback
        self._initialize_storage()
        
        logger.info(f"Initialized PDF storage service with root: {self.storage_root}")
    
    def store_pdf(self, content_bytes: bytes, store_request: PdfStoreRequest) -> PdfFile:
        """
        Complete PDF storage workflow including file storage and database record creation
        
        Args:
            content_bytes: PDF file content
            store_request: Domain object with storage request details
            
        Returns:
            PdfFile: Created PDF domain object
        """
        try:
            # Calculate file hash for deduplication
            file_hash = self.calculate_file_hash(content_bytes)
            
            # Check for existing PDF with same hash
            existing_pdf = self.pdf_repo.get_duplicate_by_hash(file_hash)
            if existing_pdf:
                logger.info(f"PDF already exists with hash {file_hash[:16]}...: {existing_pdf.filename}")
                return existing_pdf
            
            # Store PDF file to disk
            file_path = self._write_pdf_file(
                pdf_content=content_bytes,
                original_filename=store_request.original_filename,
                email_id=store_request.email_id
            )
            
            # Create database record
            pdf_data = {
                'email_id': store_request.email_id,
                'filename': store_request.filename,
                'original_filename': store_request.original_filename,
                'file_path': file_path,
                'file_size': len(content_bytes),
                'sha256_hash': file_hash,
                'mime_type': store_request.mime_type
            }
            
            pdf_file = self.pdf_repo.create_pdf_record(pdf_data)
            logger.info(f"Stored PDF: {pdf_file.filename} (ID: {pdf_file.id}, Hash: {file_hash[:16]}...)")
            
            return pdf_file
            
        except Exception as e:
            logger.error(f"Error in complete PDF storage workflow: {e}")
            raise
    
    def _initialize_storage(self):
        """Initialize storage directories with proper permissions and fallback handling"""
        try:
            # Create base directories
            self.storage_root.mkdir(parents=True, exist_ok=True)
            self.pdf_root.mkdir(parents=True, exist_ok=True)
            
            # Test write permissions by creating and removing a test file
            test_file = self.storage_root / ".write_test"
            test_file.write_text("test")
            test_file.unlink()
            
            logger.info(f"Storage directories initialized successfully: {self.storage_root}")
            
        except PermissionError as e:
            logger.error(f"Permission denied creating storage directory: {self.storage_root}")
            fallback_path = self._get_fallback_storage()
            logger.info(f"Using fallback storage path: {fallback_path}")
            
            self.storage_root = Path(fallback_path)
            self.pdf_root = self.storage_root / "pdfs"
            self._initialize_storage()  # Retry with fallback
            
        except OSError as e:
            logger.error(f"OS error creating storage directory: {self.storage_root} - {e}")
            fallback_path = self._get_fallback_storage()
            logger.info(f"Using fallback storage path: {fallback_path}")
            
            self.storage_root = Path(fallback_path)
            self.pdf_root = self.storage_root / "pdfs"
            self._initialize_storage()  # Retry with fallback
            
        except Exception as e:
            logger.error(f"Unexpected error initializing storage: {e}")
            # Try absolute fallback to temp directory
            temp_storage = self._get_temp_fallback_storage()
            logger.warning(f"Using temporary fallback storage: {temp_storage}")
            
            self.storage_root = Path(temp_storage)
            self.pdf_root = self.storage_root / "pdfs"
            
            # Final attempt - if this fails, raise the exception
            try:
                self.storage_root.mkdir(parents=True, exist_ok=True)
                self.pdf_root.mkdir(parents=True, exist_ok=True)
            except Exception as final_error:
                logger.error(f"Final fallback storage initialization failed: {final_error}")
                raise Exception(f"Unable to initialize any storage location. Original: {self.original_storage_root}, Fallback attempted: {temp_storage}")
    
    def _get_fallback_storage(self) -> str:
        """Get fallback storage location if primary fails"""
        try:
            # Import here to avoid circular imports
            from ...shared.utils.storage_config import get_fallback_storage
            return get_fallback_storage()
        except Exception as e:
            logger.warning(f"Error getting configured fallback storage: {e}")
            return self._get_temp_fallback_storage()
    
    def _get_temp_fallback_storage(self) -> str:
        """Get temporary directory fallback storage"""
        temp_storage = os.path.join(tempfile.gettempdir(), 'eto_system_fallback', 'pdf_storage')
        logger.info(f"Using temp directory fallback: {temp_storage}")
        return temp_storage
    
    def _write_pdf_file(self, pdf_content: bytes, original_filename: str, email_id: Optional[int]) -> str:
        """
        Store PDF file to disk with organized directory structure
        
        Args:
            pdf_content: Raw PDF file bytes
            original_filename: Original filename from email attachment
            email_id: ID of the email this PDF belongs to
            
        Returns:
            str: File path where PDF was stored
        """
        try:
            # Sanitize filename for safe storage
            safe_filename = self.sanitize_filename(original_filename)
            
            # Generate organized file path
            file_path = self.generate_file_path(safe_filename, email_id)
            
            # Ensure directory exists
            directory_path = str(Path(file_path).parent)
            self.ensure_storage_directory(directory_path)
            
            # Write PDF content to file
            with open(file_path, 'wb') as f:
                f.write(pdf_content)
            
            logger.info(f"Stored PDF {safe_filename} for email {email_id} at: {file_path}")
            return file_path
            
        except Exception as e:
            logger.error(f"Error storing PDF {original_filename} for email {email_id}: {e}")
            raise
    
    def retrieve_pdf_content(self, file_path: str) -> bytes:
        """
        Load PDF file content from disk for client delivery
        
        Args:
            file_path: Path to the stored PDF file
            
        Returns:
            bytes: PDF file content
            
        Raises:
            FileNotFoundError: If PDF file doesn't exist
        """
        try:
            if not os.path.exists(file_path):
                raise FileNotFoundError(f"PDF file not found: {file_path}")
            
            with open(file_path, 'rb') as f:
                content = f.read()
            
            logger.debug(f"Retrieved PDF content from: {file_path} ({len(content)} bytes)")
            return content
            
        except Exception as e:
            logger.error(f"Error retrieving PDF content from {file_path}: {e}")
            raise
    
    def generate_file_path(self, filename: str, email_id: Optional[int] = None) -> str:
        """
        Generate organized file path for PDF storage
        Structure:
        - Email PDFs: /storage/pdfs/YYYY/MM/email_{email_id}_{filename}.pdf
        - Manual PDFs: /storage/pdfs/YYYY/MM/manual_{timestamp}_{filename}.pdf

        Args:
            filename: Sanitized filename
            email_id: Email ID (None for manual uploads)

        Returns:
            str: Generated file path
        """
        now = datetime.now()
        year = now.strftime("%Y")
        month = now.strftime("%m")

        # Create directory structure: pdfs/YYYY/MM/
        directory = self.pdf_root / year / month

        # Remove .pdf extension if already present, we'll add it
        base_filename = filename.replace('.pdf', '').replace('.PDF', '')

        # Generate unique filename based on source
        if email_id is not None:
            # Email-sourced PDF
            unique_filename = f"email_{email_id}_{base_filename}.pdf"
        else:
            # Manual upload - use timestamp for uniqueness
            timestamp = now.strftime("%Y%m%d_%H%M%S")
            unique_filename = f"manual_{timestamp}_{base_filename}.pdf"

        file_path = directory / unique_filename
        return str(file_path)
    
    def calculate_file_hash(self, content: bytes) -> str:
        """
        Calculate SHA256 hash for PDF content
        
        Args:
            content: PDF file bytes
            
        Returns:
            str: SHA256 hash as hex string
        """
        sha256_hash = hashlib.sha256()
        sha256_hash.update(content)
        hash_hex = sha256_hash.hexdigest()
        
        logger.debug(f"Calculated SHA256 hash: {hash_hex[:16]}... (length: {len(content)} bytes)")
        return hash_hex
    
    def sanitize_filename(self, filename: str) -> str:
        """
        Sanitize filename for safe storage
        
        Args:
            filename: Original filename
            
        Returns:
            str: Sanitized filename safe for file system
        """
        # Remove or replace unsafe characters
        # Keep alphanumeric, dots, hyphens, underscores, and spaces
        sanitized = re.sub(r'[^\w\s\-_\.]', '_', filename)
        
        # Replace multiple spaces with single underscores
        sanitized = re.sub(r'\s+', '_', sanitized)
        
        # Remove leading/trailing dots and spaces
        sanitized = sanitized.strip(' .')
        
        # Ensure filename isn't empty
        if not sanitized:
            sanitized = "unnamed_file"
        
        # Limit length to prevent filesystem issues
        if len(sanitized) > 200:
            # Keep extension if present
            if '.' in sanitized:
                name, ext = sanitized.rsplit('.', 1)
                sanitized = name[:195] + '.' + ext
            else:
                sanitized = sanitized[:200]
        
        logger.debug(f"Sanitized filename '{filename}' -> '{sanitized}'")
        return sanitized
    
    def ensure_storage_directory(self, directory_path: str) -> None:
        """
        Ensure storage directory exists, create if necessary
        
        Args:
            directory_path: Directory path to create
        """
        try:
            os.makedirs(directory_path, exist_ok=True)
            logger.debug(f"Ensured directory exists: {directory_path}")
        except Exception as e:
            logger.error(f"Error creating directory {directory_path}: {e}")
            raise
    
    def get_storage_info(self) -> Dict[str, Any]:
        """
        Get information about the storage configuration and status

        Returns:
            Dict[str, Any]: Storage information including paths and basic status
        """
        try:
            storage_info = {
                'original_root': self.original_storage_root,
                'current_root': str(self.storage_root),
                'pdf_directory': str(self.pdf_root),
                'root_exists': self.storage_root.exists(),
                'pdf_directory_exists': self.pdf_root.exists(),
                'fallback_used': str(self.storage_root) != self.original_storage_root
            }

            return storage_info

        except Exception as e:
            logger.error(f"Error getting storage info: {e}")
            return {
                'error': str(e),
                'original_root': self.original_storage_root,
                'current_root': str(self.storage_root)
            }
