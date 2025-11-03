"""
File Storage Utilities
Functions for managing PDF files on disk
"""
import os
import re
import logging
from pathlib import Path
from datetime import datetime
from typing import Optional

logger = logging.getLogger(__name__)


def sanitize_filename(filename: str) -> str:
    """
    Clean filename for safe storage
    
    Args:
        filename: Original filename
        
    Returns:
        Sanitized filename safe for filesystem
    """
    # Remove path components
    filename = os.path.basename(filename)
    
    # Replace problematic characters
    filename = re.sub(r'[<>:"/\\|?*]', '_', filename)
    
    # Remove control characters
    filename = ''.join(char for char in filename if ord(char) >= 32)
    
    # Limit length (leave room for hash prefix)
    max_length = 100
    if len(filename) > max_length:
        name, ext = os.path.splitext(filename)
        name = name[:max_length - len(ext)]
        filename = name + ext
    
    # Ensure it has a .pdf extension
    if not filename.lower().endswith('.pdf'):
        filename += '.pdf'
    
    return filename


def create_storage_path(storage_base: str, file_hash: str, original_filename: str) -> str:
    """
    Create organized storage path for PDF
    
    Args:
        storage_base: Base storage directory
        file_hash: File hash for uniqueness
        original_filename: Original filename for reference
        
    Returns:
        Relative path like 'pdfs/2025/01/hash_filename.pdf'
    """
    # Create date-based directory structure
    now = datetime.now()
    year = str(now.year)
    month = str(now.month).zfill(2)
    
    # Sanitize filename
    safe_filename = sanitize_filename(original_filename)
    
    # Create filename with hash prefix for uniqueness
    # Use first 8 chars of hash to keep filenames reasonable
    storage_filename = f"{file_hash[:8]}_{safe_filename}"
    
    # Build relative path
    relative_path = os.path.join('pdfs', year, month, storage_filename)
    
    return relative_path


def save_pdf_to_disk(file_content: bytes, 
                     storage_base: str, 
                     file_hash: str,
                     original_filename: str) -> str:
    """
    Save PDF to organized directory structure
    
    Args:
        file_content: PDF content to save
        storage_base: Base storage directory
        file_hash: File hash for organization
        original_filename: Original filename for reference
        
    Returns:
        Relative path where file was saved
        
    Raises:
        IOError: If file cannot be saved
    """
    try:
        # Create relative path
        relative_path = create_storage_path(storage_base, file_hash, original_filename)
        
        # Full path
        full_path = os.path.join(storage_base, relative_path)
        
        # Create directory structure
        directory = os.path.dirname(full_path)
        Path(directory).mkdir(parents=True, exist_ok=True)
        
        # Check if file already exists (deduplication)
        if os.path.exists(full_path):
            logger.info(f"File already exists at {relative_path}, skipping write")
            return relative_path
        
        # Write file
        with open(full_path, 'wb') as f:
            f.write(file_content)
        
        logger.info(f"Saved PDF to {relative_path}")
        return relative_path
        
    except Exception as e:
        logger.error(f"Error saving PDF to disk: {e}")
        raise IOError(f"Failed to save PDF: {e}")


def read_pdf_from_disk(storage_base: str, relative_path: str) -> Optional[bytes]:
    """
    Read PDF content from disk
    
    Args:
        storage_base: Base storage directory
        relative_path: Relative path to PDF file
        
    Returns:
        PDF content as bytes, or None if not found
    """
    try:
        full_path = os.path.join(storage_base, relative_path)
        
        if not os.path.exists(full_path):
            logger.warning(f"PDF file not found at {relative_path}")
            return None
        
        with open(full_path, 'rb') as f:
            content = f.read()
        
        logger.debug(f"Read PDF from {relative_path} ({len(content)} bytes)")
        return content
        
    except Exception as e:
        logger.error(f"Error reading PDF from disk: {e}")
        return None


def delete_pdf_from_disk(storage_base: str, relative_path: str) -> bool:
    """
    Delete PDF file from disk
    
    Args:
        storage_base: Base storage directory
        relative_path: Relative path to PDF file
        
    Returns:
        True if deleted successfully, False otherwise
    """
    try:
        full_path = os.path.join(storage_base, relative_path)
        
        if not os.path.exists(full_path):
            logger.warning(f"PDF file not found for deletion at {relative_path}")
            return False
        
        os.remove(full_path)
        logger.info(f"Deleted PDF at {relative_path}")
        
        # Try to clean up empty directories
        directory = os.path.dirname(full_path)
        try:
            os.removedirs(directory)  # Only removes if empty
            logger.debug(f"Cleaned up empty directory {directory}")
        except:
            pass  # Directory not empty or other issue
        
        return True
        
    except Exception as e:
        logger.error(f"Error deleting PDF from disk: {e}")
        return False


def ensure_storage_directory(storage_base: str) -> bool:
    """
    Ensure the base storage directory exists
    
    Args:
        storage_base: Base storage directory path
        
    Returns:
        True if directory exists or was created
    """
    try:
        Path(storage_base).mkdir(parents=True, exist_ok=True)
        
        # Also create the pdfs subdirectory
        pdfs_dir = os.path.join(storage_base, 'pdfs')
        Path(pdfs_dir).mkdir(parents=True, exist_ok=True)
        
        logger.info(f"Storage directory ready at {storage_base}")
        return True
        
    except Exception as e:
        logger.error(f"Error creating storage directory: {e}")
        return False


def get_storage_info(storage_base: str) -> dict:
    """
    Get information about storage usage
    
    Args:
        storage_base: Base storage directory
        
    Returns:
        Dictionary with storage statistics
    """
    try:
        pdfs_dir = os.path.join(storage_base, 'pdfs')
        
        if not os.path.exists(pdfs_dir):
            return {
                'exists': False,
                'total_files': 0,
                'total_size_mb': 0
            }
        
        total_files = 0
        total_size = 0
        
        for root, dirs, files in os.walk(pdfs_dir):
            for file in files:
                if file.endswith('.pdf'):
                    total_files += 1
                    file_path = os.path.join(root, file)
                    total_size += os.path.getsize(file_path)
        
        return {
            'exists': True,
            'total_files': total_files,
            'total_size_mb': round(total_size / (1024 * 1024), 2),
            'base_path': storage_base
        }
        
    except Exception as e:
        logger.error(f"Error getting storage info: {e}")
        return {
            'exists': False,
            'error': str(e)
        }