"""
PDF Extraction Service
Handles extraction of PDF attachments from Outlook emails
"""
import logging
import os
import tempfile
from typing import List, Dict, Any, Optional, Tuple
from ..pdf_processing.types import PdfFile

logger = logging.getLogger(__name__)


class PdfExtractionService:
    """Service for extracting PDF attachments from emails"""
    
    def __init__(self, storage_service, pdf_repository):
        """
        Initialize PDF extraction service
        
        Args:
            storage_service: PdfStorageService instance
            pdf_repository: PdfRepository instance
        """
        self.storage_service = storage_service
        self.pdf_repository = pdf_repository
        logger.info("Initialized PDF extraction service")
    
    def extract_pdfs_from_email(self, email_id: int, outlook_mail_object: Any) -> List[Dict[str, Any]]:
        """
        Extract all PDF attachments from an Outlook email
        
        Args:
            email_id: Database ID of the email
            outlook_mail_object: Outlook COM mail object
            
        Returns:
            List[Dict]: List of created PDF metadata dictionaries
        """
        pdf_records = []
        
        try:
            # Check if email has attachments
            if not hasattr(outlook_mail_object, 'Attachments') or outlook_mail_object.Attachments.Count == 0:
                logger.debug(f"Email {email_id} has no attachments")
                return pdf_records
            
            logger.info(f"Processing {outlook_mail_object.Attachments.Count} attachments for email {email_id}")
            
            # Process each attachment
            for i in range(1, outlook_mail_object.Attachments.Count + 1):
                attachment = outlook_mail_object.Attachments.Item(i)
                
                try:
                    # Check if attachment is a PDF
                    if self.is_pdf_attachment(attachment):
                        logger.info(f"Found PDF attachment: {attachment.FileName}")
                        
                        # Download attachment content
                        pdf_content = self.download_attachment(attachment)
                        
                        # Validate PDF content
                        if not self.validate_pdf_content(pdf_content):
                            logger.warning(f"Invalid PDF content for attachment: {attachment.FileName}")
                            continue
                        
                        # Check for duplicate by hash
                        file_hash = self.storage_service.calculate_file_hash(pdf_content)
                        existing_pdf = self.pdf_repository.get_duplicate_by_hash(file_hash)
                        
                        if existing_pdf:
                            logger.info(f"Duplicate PDF found (hash: {file_hash[:16]}...), skipping storage")
                            pdf_records.append({
                                'id': existing_pdf.id,
                                'filename': existing_pdf.filename,
                                'file_size': existing_pdf.file_size,
                                'sha256_hash': file_hash,
                                'duplicate': True
                            })
                            continue
                        
                        # Store PDF file
                        file_path = self.storage_service.store_pdf(
                            pdf_content, 
                            attachment.FileName, 
                            email_id
                        )
                        
                        # Get PDF metadata
                        metadata = self.get_pdf_metadata(pdf_content, attachment.FileName)
                        
                        # Create PDF database record
                        pdf_data = {
                            'email_id': email_id,
                            'filename': os.path.basename(file_path),
                            'original_filename': attachment.FileName,
                            'file_path': file_path,
                            'file_size': len(pdf_content),
                            'sha256_hash': file_hash,
                            'mime_type': 'application/pdf',
                            'page_count': metadata.get('page_count'),
                            'object_count': metadata.get('object_count')
                        }
                        
                        pdf_id = self.create_pdf_record(pdf_data)
                        
                        pdf_records.append({
                            'id': pdf_id,
                            'filename': pdf_data['filename'],
                            'file_size': pdf_data['file_size'],
                            'sha256_hash': file_hash,
                            'duplicate': False
                        })
                        
                        logger.info(f"Successfully extracted PDF {attachment.FileName} -> record {pdf_id}")
                        
                except Exception as e:
                    logger.error(f"Error processing attachment {attachment.FileName}: {e}")
                    continue
            
            logger.info(f"Extracted {len(pdf_records)} PDF files from email {email_id}")
            return pdf_records
            
        except Exception as e:
            logger.error(f"Error extracting PDFs from email {email_id}: {e}")
            raise
    
    def download_attachment(self, attachment_object: Any) -> bytes:
        """
        Download attachment content from Outlook COM object
        
        Args:
            attachment_object: Outlook attachment COM object
            
        Returns:
            bytes: Attachment file content
        """
        try:
            # Create temporary file to save attachment
            with tempfile.NamedTemporaryFile(delete=False) as temp_file:
                temp_path = temp_file.name
            
            try:
                # Save attachment to temporary file
                attachment_object.SaveAsFile(temp_path)
                
                # Read the content
                with open(temp_path, 'rb') as f:
                    content = f.read()
                
                logger.debug(f"Downloaded attachment {attachment_object.FileName} ({len(content)} bytes)")
                return content
                
            finally:
                # Clean up temporary file
                if os.path.exists(temp_path):
                    os.unlink(temp_path)
                    
        except Exception as e:
            logger.error(f"Error downloading attachment {attachment_object.FileName}: {e}")
            raise
    
    def get_pdf_metadata(self, pdf_content: bytes, filename: str) -> Dict[str, Any]:
        """
        Extract basic metadata from PDF content
        
        Args:
            pdf_content: Raw PDF file bytes
            filename: Original filename
            
        Returns:
            Dict: PDF metadata (file_size, page_count, etc.)
        """
        metadata = {
            'page_count': None,
            'object_count': None
        }
        
        try:
            # Basic PDF metadata extraction without external dependencies
            # For now, we'll extract basic info from PDF structure
            
            # Check for PDF page count using simple parsing
            # Look for "/Count" entries in PDF structure
            content_str = pdf_content.decode('latin-1', errors='ignore')
            
            # Simple page count extraction (basic approach)
            if '/Count' in content_str:
                import re
                count_matches = re.findall(r'/Count\s+(\d+)', content_str)
                if count_matches:
                    # Take the first reasonable page count found
                    page_counts = [int(c) for c in count_matches if int(c) < 10000]
                    if page_counts:
                        metadata['page_count'] = max(page_counts)  # Take largest reasonable count
            
            # Simple object count (count PDF objects)
            obj_matches = re.findall(r'\d+\s+\d+\s+obj', content_str)
            if obj_matches:
                metadata['object_count'] = len(obj_matches)
            
            logger.debug(f"Extracted metadata for {filename}: pages={metadata['page_count']}, objects={metadata['object_count']}")
            
        except Exception as e:
            logger.warning(f"Could not extract PDF metadata from {filename}: {e}")
        
        return metadata
    
    def is_pdf_attachment(self, attachment_object: Any) -> bool:
        """
        Check if attachment is a PDF file
        
        Args:
            attachment_object: Outlook attachment COM object
            
        Returns:
            bool: True if attachment is a PDF
        """
        try:
            filename = getattr(attachment_object, 'FileName', '').lower()
            
            # Check file extension
            if filename.endswith('.pdf'):
                logger.debug(f"Attachment {filename} identified as PDF by extension")
                return True
            
            # Additional check: examine MIME type if available
            display_name = getattr(attachment_object, 'DisplayName', '').lower()
            if '.pdf' in display_name:
                logger.debug(f"Attachment {filename} identified as PDF by display name")
                return True
            
            return False
            
        except Exception as e:
            logger.error(f"Error checking if attachment is PDF: {e}")
            return False
    
    def create_pdf_record(self, pdf_data: Dict[str, Any]) -> int:
        """
        Create PDF database record
        
        Args:
            pdf_data: PDF metadata dictionary
            
        Returns:
            int: Created PDF record ID
        """
        try:
            pdf_id = self.pdf_repository.create_pdf_record(pdf_data)
            logger.info(f"Created PDF database record {pdf_id} for {pdf_data['filename']}")
            return pdf_id
        except Exception as e:
            logger.error(f"Error creating PDF record: {e}")
            raise
    
    def validate_pdf_content(self, content: bytes) -> bool:
        """
        Validate that content is a valid PDF file
        
        Args:
            content: File content bytes
            
        Returns:
            bool: True if valid PDF
        """
        try:
            # Check minimum file size
            if len(content) < 10:
                logger.debug("Content too small to be a valid PDF")
                return False
            
            # Check PDF magic bytes at start of file
            if not content.startswith(b'%PDF-'):
                logger.debug("Content does not start with PDF magic bytes")
                return False
            
            # Check for PDF version (should be something like %PDF-1.4)
            header = content[:10].decode('ascii', errors='ignore')
            if not header.startswith('%PDF-1.'):
                logger.debug(f"Invalid PDF version header: {header}")
                return False
            
            # Check for EOF marker (basic validation)
            content_str = content.decode('latin-1', errors='ignore')
            if '%%EOF' not in content_str:
                logger.debug("PDF missing EOF marker")
                return False
            
            logger.debug("PDF content validation passed")
            return True
            
        except Exception as e:
            logger.warning(f"Error validating PDF content: {e}")
            return False