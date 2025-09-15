"""
PDF Storage Service
Handles physical file storage and retrieval operations for PDF files
"""
import logging
import hashlib
import os
import re
import tempfile
from pathlib import Path
from datetime import datetime
from typing import Optional, Dict, Any

logger = logging.getLogger(__name__)


class PdfStorageService:
    """Service for managing PDF file storage operations with cross-platform support"""
    
    def __init__(self, storage_root: str):
        """
        Initialize PDF storage service with auto-creation and fallback
        
        Args:
            storage_root: Root directory for PDF storage
        """
        self.original_storage_root = storage_root
        self.storage_root = Path(storage_root)
        self.pdf_root = self.storage_root / "pdfs"
        
        # Initialize storage directories with auto-creation and fallback
        self._initialize_storage()
        
        logger.info(f"Initialized PDF storage service with root: {self.storage_root}")
    
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
    
    def store_pdf(self, pdf_content: bytes, original_filename: str, email_id: int) -> str:
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
            file_path = self.generate_file_path(email_id, safe_filename)
            
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
    
    def generate_file_path(self, email_id: int, filename: str) -> str:
        """
        Generate organized file path for PDF storage
        Structure: /storage/pdfs/YYYY/MM/email_{email_id}_{filename}.pdf
        
        Args:
            email_id: Email ID
            filename: Sanitized filename
            
        Returns:
            str: Generated file path
        """
        now = datetime.now()
        year = now.strftime("%Y")
        month = now.strftime("%m")
        
        # Create directory structure: pdfs/YYYY/MM/
        directory = self.pdf_root / year / month
        
        # Generate unique filename with email ID prefix
        # Remove .pdf extension if already present, we'll add it
        base_filename = filename.replace('.pdf', '').replace('.PDF', '')
        unique_filename = f"email_{email_id}_{base_filename}.pdf"
        
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
            Dict[str, Any]: Storage information including paths, sizes, and status
        """
        try:
            storage_info = {
                'original_root': self.original_storage_root,
                'current_root': str(self.storage_root),
                'pdf_directory': str(self.pdf_root),
                'root_exists': self.storage_root.exists(),
                'pdf_directory_exists': self.pdf_root.exists(),
                'is_writable': self._test_write_permissions(),
                'storage_size_mb': self._get_storage_size_mb(),
                'file_count': self._get_file_count(),
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
    
    def _test_write_permissions(self) -> bool:
        """Test if storage directory is writable"""
        try:
            test_file = self.storage_root / ".permission_test"
            test_file.write_text("test")
            test_file.unlink()
            return True
        except Exception:
            return False
    
    def _get_storage_size_mb(self) -> float:
        """Get total storage size in MB"""
        try:
            total_size = 0
            for file_path in self.storage_root.rglob('*'):
                if file_path.is_file():
                    total_size += file_path.stat().st_size
            return round(total_size / (1024 * 1024), 2)
        except Exception:
            return 0.0
    
    def _get_file_count(self) -> int:
        """Get total number of files in storage"""
        try:
            return len([f for f in self.storage_root.rglob('*') if f.is_file()])
        except Exception:
            return 0