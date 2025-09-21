"""
Email Listener Thread
Individual thread for monitoring a single email configuration
"""
import logging
import threading
import time
from typing import Optional, List, Dict, Any
from datetime import datetime, timezone
import imaplib
import email
from email.header import decode_header

from shared.models.email_config import EmailConfig
from shared.database.repositories.email import EmailRepository
from features.email_ingestion.config_service import EmailIngestionConfigService
from shared.exceptions import ServiceError

logger = logging.getLogger(__name__)


class EmailListenerThread(threading.Thread):
    """Thread for monitoring emails from a specific configuration"""
    
    def __init__(self, 
                 config: EmailConfig,
                 config_service: EmailIngestionConfigService,
                 email_repository: EmailRepository,
                 check_interval: int = 300):  # Default 5 minutes
        super().__init__(name=f"EmailListener-{config.id}")
        self.config = config
        self.config_service = config_service
        self.email_repository = email_repository
        self.check_interval = check_interval
        
        # Thread control
        self.stop_event = threading.Event()
        self.error_count = 0
        self.max_errors = 5
        
        # IMAP connection
        self.imap_conn: Optional[imaplib.IMAP4_SSL] = None
        
        logger.info(f"Initialized EmailListenerThread for config {config.id}")
    
    def run(self):
        """Main thread loop"""
        logger.info(f"Starting email listener for config {self.config.id}")
        
        while not self.stop_event.is_set():
            try:
                # Check emails
                self._check_emails()
                
                # Reset error count on success
                self.error_count = 0
                
                # Wait for next check
                self.stop_event.wait(self.check_interval)
                
            except Exception as e:
                self.error_count += 1
                logger.error(f"Error in listener {self.config.id}: {e} (error #{self.error_count})")
                
                if self.error_count >= self.max_errors:
                    logger.critical(f"Max errors reached for config {self.config.id}, stopping listener")
                    break
                
                # Exponential backoff on errors
                wait_time = min(60 * (2 ** self.error_count), 3600)  # Max 1 hour
                self.stop_event.wait(wait_time)
        
        # Cleanup
        self._disconnect()
        logger.info(f"Stopped email listener for config {self.config.id}")
    
    def stop(self):
        """Signal thread to stop"""
        logger.info(f"Stopping listener for config {self.config.id}")
        self.stop_event.set()
    
    def _check_emails(self):
        """Check for new emails"""
        try:
            # Connect to email server
            self._connect()
            
            # Get emails
            emails_processed = 0
            pdfs_found = 0
            
            # Select folder
            folder = self.config.folder_name or "INBOX"
            self.imap_conn.select(folder)
            
            # Search for all emails (or apply date filter if we have progress info)
            # In production, you'd want to filter by date if config.last_check_time exists
            # For now, simple search - get all emails
            _, message_ids = self.imap_conn.search(None, 'ALL')
            
            if message_ids[0]:
                for msg_id in message_ids[0].split():
                    try:
                        # Fetch email
                        _, msg_data = self.imap_conn.fetch(msg_id, '(RFC822)')
                        raw_email = msg_data[0][1]
                        email_message = email.message_from_bytes(raw_email)
                        
                        # Extract message ID
                        message_id = email_message.get('Message-ID', '')
                        if not message_id:
                            continue
                        
                        # Check if already processed
                        if self.email_repository.is_message_processed(self.config.id, message_id):
                            continue
                        
                        # Extract email details
                        email_data = self._extract_email_data(email_message)
                        
                        # Check for PDF attachments
                        has_pdf, attachment_count = self._check_attachments(email_message)
                        
                        # Save to repository
                        self.email_repository.create(
                            message_id=message_id,
                            subject=email_data['subject'],
                            sender_email=email_data['sender_email'],
                            sender_name=email_data['sender_name'],
                            received_date=email_data['received_date'],
                            folder_name=folder,
                            has_pdf_attachments=has_pdf,
                            attachment_count=attachment_count,
                            config_id=self.config.id
                        )
                        
                        emails_processed += 1
                        if has_pdf:
                            pdfs_found += 1
                        
                        # Process PDFs if configured
                        if has_pdf and self.config.auto_process_pdfs:
                            self._process_pdf_attachments(email_message, message_id)
                        
                    except Exception as e:
                        logger.error(f"Error processing email {msg_id}: {e}")
                        continue
            
            # Update progress tracking
            if emails_processed > 0 or pdfs_found > 0:
                self.config_service.update_progress(
                    self.config.id, 
                    emails_processed=emails_processed,
                    pdfs_found=pdfs_found
                )
                logger.info(f"Config {self.config.id}: Processed {emails_processed} emails, found {pdfs_found} PDFs")
            
        finally:
            self._disconnect()
    
    def _connect(self):
        """Connect to email server"""
        try:
            if self.imap_conn:
                self._disconnect()
            
            # Create IMAP connection
            self.imap_conn = imaplib.IMAP4_SSL(
                self.config.imap_server, 
                self.config.imap_port
            )
            
            # Login
            self.imap_conn.login(self.config.email, self.config.password)
            
            logger.debug(f"Connected to {self.config.imap_server} for config {self.config.id}")
            
        except Exception as e:
            logger.error(f"Failed to connect to email server for config {self.config.id}: {e}")
            raise ServiceError(f"Email connection failed: {e}")
    
    def _disconnect(self):
        """Disconnect from email server"""
        if self.imap_conn:
            try:
                self.imap_conn.logout()
            except:
                pass
            self.imap_conn = None
    
    def _extract_email_data(self, email_message) -> dict:
        """Extract relevant data from email message"""
        # Subject
        subject = email_message.get('Subject', '')
        if subject:
            decoded_subject = decode_header(subject)
            subject = ''.join([
                text.decode(encoding or 'utf-8') if isinstance(text, bytes) else text
                for text, encoding in decoded_subject
            ])
        
        # From
        from_header = email_message.get('From', '')
        sender_name, sender_email = self._parse_from_header(from_header)
        
        # Date
        date_str = email_message.get('Date', '')
        received_date = self._parse_date(date_str)
        
        return {
            'subject': subject[:500],  # Limit subject length
            'sender_email': sender_email,
            'sender_name': sender_name,
            'received_date': received_date
        }
    
    def _parse_from_header(self, from_header: str) -> tuple:
        """Parse From header into name and email"""
        import re
        
        # Extract email address
        email_match = re.search(r'<(.+?)>', from_header)
        if email_match:
            sender_email = email_match.group(1)
            sender_name = from_header[:email_match.start()].strip().strip('"')
        else:
            sender_email = from_header.strip()
            sender_name = None
        
        return sender_name, sender_email
    
    def _parse_date(self, date_str: str) -> datetime:
        """Parse email date string"""
        from email.utils import parsedate_to_datetime
        
        try:
            return parsedate_to_datetime(date_str)
        except:
            return datetime.now(timezone.utc)
    
    def _check_attachments(self, email_message) -> tuple:
        """Check for PDF attachments"""
        has_pdf = False
        attachment_count = 0
        
        for part in email_message.walk():
            if part.get_content_disposition() == 'attachment':
                attachment_count += 1
                filename = part.get_filename()
                if filename and filename.lower().endswith('.pdf'):
                    has_pdf = True
        
        return has_pdf, attachment_count
    
    def _process_pdf_attachments(self, email_message, message_id: str):
        """Process PDF attachments (placeholder for future implementation)"""
        # This would integrate with the PDF processing pipeline
        logger.info(f"Would process PDFs for message {message_id}")
        pass