"""
PDF Extraction Utilities
Functions for extracting metadata, text, and objects from PDF files
"""
import hashlib
import logging
from typing import List, Dict, Any, Optional
import pdfplumber
from io import BytesIO

from shared.models.pdf_processing import PdfObject

logger = logging.getLogger(__name__)


def calculate_file_hash(file_content: bytes) -> str:
    """
    Calculate SHA256 hash for deduplication
    
    Args:
        file_content: PDF file content as bytes
        
    Returns:
        SHA256 hash as hex string
    """
    return hashlib.sha256(file_content).hexdigest()


def extract_pdf_metadata(file_content: bytes) -> Dict[str, Any]:
    """
    Extract basic metadata from PDF
    
    Args:
        file_content: PDF file content as bytes
        
    Returns:
        Dictionary with page_count, file_size, and other metadata
    """
    try:
        with pdfplumber.open(BytesIO(file_content)) as pdf:
            metadata = {
                'page_count': len(pdf.pages),
                'file_size': len(file_content),
                'pdf_metadata': pdf.metadata if pdf.metadata else {}
            }
            
            # Add any useful metadata fields
            if pdf.metadata:
                metadata['author'] = pdf.metadata.get('Author', None)
                metadata['title'] = pdf.metadata.get('Title', None)
                metadata['subject'] = pdf.metadata.get('Subject', None)
                metadata['creator'] = pdf.metadata.get('Creator', None)
                
            return metadata
            
    except Exception as e:
        logger.error(f"Error extracting PDF metadata: {e}")
        # Return minimal metadata on error
        return {
            'page_count': 1,  # Assume at least 1 page
            'file_size': len(file_content),
            'pdf_metadata': {},
            'extraction_error': str(e)
        }


def extract_pdf_text(file_content: bytes) -> str:
    """
    Extract all text content from PDF
    
    Args:
        file_content: PDF file content as bytes
        
    Returns:
        Extracted text as string
    """
    try:
        text_parts = []
        
        with pdfplumber.open(BytesIO(file_content)) as pdf:
            for page_num, page in enumerate(pdf.pages, start=1):
                page_text = page.extract_text()
                if page_text:
                    text_parts.append(f"--- Page {page_num} ---\n{page_text}")
        
        return "\n\n".join(text_parts) if text_parts else ""
        
    except Exception as e:
        logger.error(f"Error extracting PDF text: {e}")
        return ""


def extract_pdf_objects(file_content: bytes) -> List[PdfObject]:
    """
    Extract text objects with positions using pdfplumber
    
    Args:
        file_content: PDF file content as bytes
        
    Returns:
        List of PdfObject with text, bbox, page, etc.
    """
    objects = []
    
    try:
        with pdfplumber.open(BytesIO(file_content)) as pdf:
            for page_num, page in enumerate(pdf.pages, start=1):
                # Get page dimensions
                page_width = float(page.width)
                page_height = float(page.height)

                # Extract words with positions
                words = page.extract_words(
                    keep_blank_chars=False,
                    use_text_flow=True,
                    extra_attrs=['fontname', 'size']
                )
                
                for word in words:
                    # Create PdfObject for each word with native PDF coordinates
                    pdf_object = PdfObject(
                        type="text",
                        text=word.get('text', ''),
                        page=page_num,
                        bbox=[
                            float(word['x0']),
                            float(word['top']),
                            float(word['x1']),
                            float(word['bottom'])
                        ],
                        confidence=1.0,  # pdfplumber doesn't provide confidence
                        metadata={
                            'fontname': word.get('fontname', 'unknown'),
                            'size': word.get('size', 0),
                            'direction': word.get('direction', 0),
                            'page_width': page_width,
                            'page_height': page_height
                        }
                    )
                    objects.append(pdf_object)
                
                # Also extract tables if present
                tables = page.extract_tables()
                for table_idx, table in enumerate(tables):
                    if table:
                        # Get table bounding box if available (keep native PDF coordinates)
                        table_bbox = page.find_tables()[table_idx].bbox if page.find_tables() else [0, 0, 0, 0]

                        table_object = PdfObject(
                            type="table",
                            text=str(table),  # Store table as string representation
                            page=page_num,
                            bbox=list(table_bbox),
                            confidence=1.0,
                            metadata={
                                'rows': len(table),
                                'cols': len(table[0]) if table else 0,
                                'data': table,  # Store actual table data
                                'page_width': page_width,
                                'page_height': page_height
                            }
                        )
                        objects.append(table_object)
        
        logger.info(f"Extracted {len(objects)} objects from PDF")
        return objects
        
    except Exception as e:
        logger.error(f"Error extracting PDF objects: {e}")
        return []


def extract_signature_objects(file_content: bytes, min_confidence: float = 0.8) -> List[PdfObject]:
    """
    Extract only high-confidence signature objects for template matching
    
    Args:
        file_content: PDF file content as bytes
        min_confidence: Minimum confidence threshold
        
    Returns:
        List of signature-worthy PdfObjects
    """
    all_objects = extract_pdf_objects(file_content)
    
    # Filter for signature objects (high confidence, reasonable size text)
    signature_objects = []
    
    for obj in all_objects:
        # Only include text objects with reasonable content
        if obj.type == "text" and obj.text:
            # Skip very short text (likely noise)
            if len(obj.text.strip()) < 2:
                continue
                
            # Skip pure numbers (likely data, not structure)
            if obj.text.strip().replace('.', '').replace(',', '').isdigit():
                continue
            
            # Skip if too long (likely paragraph text)
            if len(obj.text) > 100:
                continue
                
            signature_objects.append(obj)
    
    logger.info(f"Extracted {len(signature_objects)} signature objects from {len(all_objects)} total")
    return signature_objects


def validate_pdf(file_content: bytes) -> tuple[bool, Optional[str]]:
    """
    Validate that the file is a valid PDF
    
    Args:
        file_content: File content to validate
        
    Returns:
        Tuple of (is_valid, error_message)
    """
    # Check PDF header
    if not file_content.startswith(b'%PDF'):
        return False, "File does not have PDF header"
    
    # Try to open with pdfplumber
    try:
        with pdfplumber.open(BytesIO(file_content)) as pdf:
            # Check if we can access pages
            if len(pdf.pages) == 0:
                return False, "PDF has no pages"
        return True, None
        
    except Exception as e:
        return False, f"Invalid PDF: {str(e)}"