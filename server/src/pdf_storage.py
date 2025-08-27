"""
PDF Storage Service for ETO system
Handles content-addressed storage of PDF files
"""

import os
import hashlib
import logging
from pathlib import Path
from PyPDF2 import PdfReader
import tempfile

logger = logging.getLogger(__name__)

class PdfStorageService:
    """Handles PDF file storage with content-addressed naming"""
    
    def __init__(self, storage_root="storage"):
        self.storage_root = Path(storage_root)
        self.pdf_storage_path = self.storage_root / "pdfs"
        self._ensure_storage_directories()
    
    def _ensure_storage_directories(self):
        """Create storage directories if they don't exist"""
        try:
            self.storage_root.mkdir(parents=True, exist_ok=True)
            self.pdf_storage_path.mkdir(parents=True, exist_ok=True)
            logger.info(f"Storage directories ready: {self.storage_root}")
        except Exception as e:
            logger.error(f"Error creating storage directories: {e}")
            raise
    
    def save_pdf_attachment(self, attachment):
        """
        Save PDF attachment to content-addressed storage
        
        Args:
            attachment: Outlook COM attachment object
            
        Returns:
            dict: {
                'success': bool,
                'sha256_hash': str,
                'file_path': str,
                'file_size': int,
                'page_count': int,
                'error': str (if failed)
            }
        """
        try:
            # Get attachment data
            pdf_data = self._extract_attachment_data(attachment)
            
            # Calculate SHA-256 hash
            sha256_hash = hashlib.sha256(pdf_data).hexdigest()
            
            # Create storage path: /storage/pdfs/ab/cd/abcd1234...pdf
            folder_path = self.pdf_storage_path / sha256_hash[:2] / sha256_hash[2:4]
            folder_path.mkdir(parents=True, exist_ok=True)
            
            file_path = folder_path / f"{sha256_hash}.pdf"
            
            # Check if file already exists (deduplication)
            if file_path.exists():
                logger.info(f"PDF already exists: {sha256_hash}")
                return {
                    'success': True,
                    'sha256_hash': sha256_hash,
                    'file_path': str(file_path),
                    'file_size': len(pdf_data),
                    'page_count': self._get_pdf_page_count(pdf_data),
                    'deduplication': True
                }
            
            # Save PDF to storage
            with open(file_path, 'wb') as f:
                f.write(pdf_data)
            
            # Get PDF metadata
            page_count = self._get_pdf_page_count(pdf_data)
            
            logger.info(f"PDF saved: {sha256_hash} ({len(pdf_data)} bytes, {page_count} pages)")
            
            return {
                'success': True,
                'sha256_hash': sha256_hash,
                'file_path': str(file_path),
                'file_size': len(pdf_data),
                'page_count': page_count,
                'deduplication': False
            }
            
        except Exception as e:
            logger.error(f"Error saving PDF attachment: {e}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def _extract_attachment_data(self, attachment):
        """Extract binary data from Outlook COM attachment"""
        try:
            # Create temporary file to save attachment
            with tempfile.NamedTemporaryFile(delete=False) as temp_file:
                temp_path = temp_file.name
            
            try:
                # Save attachment to temporary file
                attachment.SaveAsFile(temp_path)
                
                # Read the file data
                with open(temp_path, 'rb') as f:
                    pdf_data = f.read()
                
                return pdf_data
                
            finally:
                # Clean up temporary file
                try:
                    os.unlink(temp_path)
                except:
                    pass
                    
        except Exception as e:
            logger.error(f"Error extracting attachment data: {e}")
            raise
    
    def _get_pdf_page_count(self, pdf_data):
        """Get page count from PDF data"""
        temp_path = None
        try:
            # Create temporary file
            with tempfile.NamedTemporaryFile(delete=False) as temp_file:
                temp_file.write(pdf_data)
                temp_file.flush()
                temp_path = temp_file.name
            
            # File is now closed, safe to read with PdfReader
            reader = PdfReader(temp_path)
            return len(reader.pages)
            
        except Exception as e:
            logger.warning(f"Error getting PDF page count: {e}")
            return None
        finally:
            # Clean up temporary file
            if temp_path and os.path.exists(temp_path):
                try:
                    os.unlink(temp_path)
                except Exception as cleanup_error:
                    logger.debug(f"Could not delete temp file {temp_path}: {cleanup_error}")
    
    def get_pdf_path(self, sha256_hash):
        """Get file system path for a PDF by its SHA-256 hash"""
        folder_path = self.pdf_storage_path / sha256_hash[:2] / sha256_hash[2:4]
        file_path = folder_path / f"{sha256_hash}.pdf"
        return str(file_path) if file_path.exists() else None
    
    def pdf_exists(self, sha256_hash):
        """Check if PDF exists in storage"""
        return self.get_pdf_path(sha256_hash) is not None
    
    def get_storage_stats(self):
        """Get storage statistics"""
        try:
            pdf_count = 0
            total_size = 0
            
            for pdf_file in self.pdf_storage_path.rglob("*.pdf"):
                pdf_count += 1
                total_size += pdf_file.stat().st_size
            
            return {
                'pdf_count': pdf_count,
                'total_size_bytes': total_size,
                'total_size_mb': round(total_size / (1024 * 1024), 2),
                'storage_path': str(self.storage_root)
            }
        except Exception as e:
            logger.error(f"Error getting storage stats: {e}")
            return {
                'error': str(e)
            }

# Global storage service instance
pdf_storage = None

def init_pdf_storage(storage_root="storage"):
    """Initialize PDF storage service"""
    global pdf_storage
    try:
        pdf_storage = PdfStorageService(storage_root)
        logger.info("PDF storage service initialized")
        return pdf_storage
    except Exception as e:
        logger.error(f"Failed to initialize PDF storage: {e}")
        raise

def get_pdf_storage():
    """Get the global PDF storage service instance"""
    if pdf_storage is None:
        raise RuntimeError("PDF storage not initialized. Call init_pdf_storage() first.")
    return pdf_storage