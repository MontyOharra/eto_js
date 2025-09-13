"""
PDF Storage Service
Handles physical file storage and retrieval operations for PDF files
"""
import logging
import hashlib
import os
import re
from pathlib import Path
from datetime import datetime
from typing import Optional, Dict, Any

logger = logging.getLogger(__name__)


class PdfStorageService:
    """Service for managing PDF file storage operations"""
    
    def __init__(self, storage_root: str):
        """
        Initialize PDF storage service
        
        Args:
            storage_root: Root directory for PDF storage
        """
        self.storage_root = Path(storage_root)
        self.pdf_root = self.storage_root / "pdfs"
        
        # Ensure base directories exist
        self.ensure_storage_directory(str(self.storage_root))
        self.ensure_storage_directory(str(self.pdf_root))
        
        logger.info(f"Initialized PDF storage service with root: {self.storage_root}")
    
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