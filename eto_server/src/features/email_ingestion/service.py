"""
Email Ingestion Service
Main orchestrator for email processing with automatic startup and downtime recovery
"""
import logging
import threading
import time
import os
from typing import Dict, List, Any, Optional
from datetime import datetime, timedelta, timezone
from dataclasses import dataclass, field

from .config_service import EmailIngestionConfigService
from .cursor_service import EmailIngestionCursorService
from .integrations.outlook_com_service import OutlookComService

from shared.database import get_connection_manager
from shared.database.repositories import EmailIngestionConfigRepository, EmailIngestionCursorRepository, EmailRepository, EtoRunRepository
from shared.utils.service_registry import get_pdf_processing_service
from shared.domain import (
    EmailIngestionConfig, EmailIngestionStats, EmailServiceHealth,
    EmailData, EmailIngestionConnectionConfig, EmailCreate, 
    EmailServiceStartResponse, EmailServiceStopResponse, 
    EmailServiceStatusResponse, EmailConfigSummary, EmailServiceConnectionStatus,
    PdfStoreRequest
)

logger = logging.getLogger(__name__)


class EmailIngestionService:
    """Main orchestrator for email processing with automatic startup and downtime recovery"""

    def __init__(self, connection_manager=None):
        # Infrastructure layer - single source of truth
        self.connection_manager = connection_manager or get_connection_manager()
        assert self.connection_manager is not None

        # Repository layer - only email-specific repositories
        self.config_repo = EmailIngestionConfigRepository(self.connection_manager)
        self.cursor_repo = EmailIngestionCursorRepository(self.connection_manager)
        self.email_repo = EmailRepository(self.connection_manager)
        self.eto_run_repo = EtoRunRepository(self.connection_manager)

        # Service layer - repositories injected as dependencies
        self.config_service = EmailIngestionConfigService(self.config_repo)
        self.cursor_service = EmailIngestionCursorService(self.cursor_repo)
        self.outlook_service = OutlookComService()
        
        # Service state
        self.is_running = False
        self.is_connected = False
        self.current_config: Optional[EmailIngestionConfig] = None
        self.processing_thread: Optional[threading.Thread] = None
        self.stop_event = threading.Event()
        
        # Statistics and health
        self.stats = EmailIngestionStats()
        self.health = EmailServiceHealth()
        
        self.logger = logging.getLogger(__name__)

    # === High-Level API Methods ===
    
    def start(self, config_id: Optional[int] = None) -> EmailServiceStartResponse:
        """Start email ingestion with active config"""
        try:
            if self.is_running:
                return EmailServiceStartResponse(
                    success=False,
                    message="Email ingestion is already running",
                    is_running=True
                )
            
            # Load config (either specified config_id or active config)
            if config_id:
                self.current_config = self.config_service.get_config(config_id)
                if not self.current_config:
                    return EmailServiceStartResponse(
                        success=False,
                        message=f"Email config {config_id} not found",
                        is_running=False
                    )
                if not self.current_config.is_active:
                    return EmailServiceStartResponse(
                        success=False,
                        message=f"Email config {config_id} is not active",
                        is_running=False
                    )
            else:
                self.current_config = self.config_service.get_active_config()
                if not self.current_config:
                    return EmailServiceStartResponse(
                        success=False,
                        message="No active email config found",
                        is_running=False
                    )
            
            # Validate that email address is provided
            if not self.current_config.email_address:
                return EmailServiceStartResponse(
                    success=False,
                    message="Active config missing required email address",
                    is_running=False
                )
            
            # Initialize cursor for the active config
            connection_config = EmailIngestionConnectionConfig(
                email_address=self.current_config.email_address,
                folder_name=self.current_config.folder_name
            )
            
            # Create or get existing cursor
            cursor = self.cursor_service.initialize_cursor(connection_config)
            if not cursor:
                return EmailServiceStartResponse(
                    success=False,
                    message=f"Failed to initialize cursor for {self.current_config.folder_name}",
                    is_running=False
                )
            
            # Update config status to running
            assert self.current_config.id is not None
            self.config_service.update_runtime_status(self.current_config.id, True)
            
            # Connect to Outlook service
            try:
                # Connect to Outlook service
                connection_config = EmailIngestionConnectionConfig(
                    email_address=self.current_config.email_address,
                    folder_name=self.current_config.folder_name
                )
                outlook_result = self.outlook_service.connect(connection_config)
                
                if not outlook_result.get("success", False):
                    raise Exception(f"Outlook connection failed: {outlook_result.get('error', 'Unknown error')}")
                
                # Start background processing thread
                self.stop_event.clear()
                self.processing_thread = threading.Thread(
                    target=self._run_processing_loop,
                    name="EmailIngestionProcessing", 
                    daemon=True
                )
                self.processing_thread.start()
                
                self.is_connected = True
                self.is_running = True
                self.health.is_running = True
                self.health.is_connected = True
                self.health.config_loaded = True
                
                self.logger.debug(f"Email ingestion service started for config: {self.current_config.name}")
                self.logger.debug(f"Monitoring folder: {self.current_config.folder_name}")
                self.logger.debug(f"Cursor initialized with last processed: {cursor.last_processed_received_date}")
                
                return EmailServiceStartResponse(
                    success=True,
                    message="Email ingestion started successfully",
                    config_name=self.current_config.name,
                    config_id=self.current_config.id,
                    folder_name=self.current_config.folder_name,
                    cursor_id=cursor.id,
                    is_running=True,
                    is_connected=True
                )
                
            except Exception as e:
                self.logger.exception(f"Failed to connect to Outlook service: {e}")
                # Rollback the running status
                self.config_service.update_runtime_status(self.current_config.id, False)
                return EmailServiceStartResponse(
                    success=False,
                    message=f"Failed to connect to email service: {str(e)}",
                    is_running=False
                )
            
        except Exception as e:
            self.logger.exception(f"Error starting email ingestion: {e}")
            return EmailServiceStartResponse(
                success=False,
                is_running=False,
                message="Failed to start email ingestion"
            )
    
    def stop(self) -> EmailServiceStopResponse:
        """Stop email ingestion"""
        try:
            if not self.is_running:
                return EmailServiceStopResponse(
                    success=False,
                    message="Email ingestion is not running",
                    is_running=False
                )
            
            # Stop processing and cleanup
            try:
                # Update current config to not running
                if self.current_config:
                    assert self.current_config.id is not None
                    self.config_service.update_runtime_status(self.current_config.id, False)
                
                # Stop processing thread if running
                if self.processing_thread and self.processing_thread.is_alive():
                    self.stop_event.set()
                    self.processing_thread.join(timeout=5.0)
                
                # Disconnect from Outlook
                disconnect_result = self.outlook_service.disconnect()
                if not disconnect_result.get("success", False):
                    self.logger.warning(f"Outlook disconnect warning: {disconnect_result.get('error')}")
                
                # Reset service state
                self.is_running = False
                self.is_connected = False
                self.health.is_running = False
                self.health.is_connected = False
                self.stop_event.clear()
                
                config_name = self.current_config.name if self.current_config else "unknown"
                self.current_config = None
                self.processing_thread = None
                
                self.logger.info(f"Email ingestion service stopped for config: {config_name}")
                
                return EmailServiceStopResponse(
                    success=True,
                    message="Email ingestion stopped successfully",
                    is_running=False,
                    is_connected=False
                )
                
            except Exception as e:
                self.logger.exception(f"Error during ingestion stop cleanup: {e}")
                # Force state reset even if cleanup failed
                self.is_running = False
                self.is_connected = False
                self.health.is_running = False
                self.health.is_connected = False
                
                return EmailServiceStopResponse(
                    success=True,
                    message="Email ingestion stopped (with cleanup errors)",
                    is_running=False,
                    warning=f"Cleanup error: {str(e)}"
                )
            
        except Exception as e:
            self.logger.exception(f"Error stopping email ingestion: {e}")
            return EmailServiceStopResponse(
                success=False,
                message="Failed to stop email ingestion",
                is_running=False
            )
    
    def get_ingestion_status(self) -> EmailServiceStatusResponse:
        """Get comprehensive ingestion status"""
        # Create current config summary
        current_config_details = None
        if self.current_config:
            current_config_details = EmailConfigSummary(
                id=self.current_config.id,
                name=self.current_config.name,
                email_address=self.current_config.email_address,
                folder_name=self.current_config.folder_name
            )

        # Create connection status
        connection_status = EmailServiceConnectionStatus(
            is_connected=self.is_connected,
            last_error=getattr(self.health, 'last_error', None)
        )

        return EmailServiceStatusResponse(
            is_running=self.is_running,
            is_connected=self.is_connected,
            current_config=self.current_config.name if self.current_config else None,
            current_config_details=current_config_details,
            connection_status=connection_status,
            stats=self.stats,
            health=self.health
        )

    # === Internal Processing Methods ===
    
    def _run_processing_loop(self):
        """Main processing loop that runs in a separate thread"""
        self.logger.info("Email processing loop started")
        
        try:
            while not self.stop_event.is_set():
                try:
                    # Run processing cycle
                    self._process_emails_cycle()
                    
                    # Wait for next cycle (use poll interval from config)
                    poll_interval = self.current_config.poll_interval_seconds if self.current_config else 60
                    if self.stop_event.wait(poll_interval):
                        break  # Stop event was set during wait
                        
                except Exception as e:
                    self.logger.exception(f"Error in processing cycle: {e}")
                    self.health.last_error = str(e)
                    if not hasattr(self.stats, 'processing_errors'):
                        self.stats.processing_errors = 0
                    self.stats.processing_errors += 1
                    
                    # Wait before retrying on error
                    if self.stop_event.wait(30):
                        break
                        
        except Exception as fatal_error:
            self.logger.exception(f"Fatal error in processing loop: {fatal_error}")
            self.health.last_error = str(fatal_error)
            self.health.is_running = False
            self.health.is_connected = False
            if not hasattr(self.stats, 'processing_errors'):
                self.stats.processing_errors = 0
            self.stats.processing_errors += 1
            
        finally:
            self.logger.info("Email processing loop stopped")
    
    def _process_emails_cycle(self):
        """Single processing cycle - check for new emails and process them"""
        if not self.current_config or not self.is_running:
            return
            
        try:
            self.logger.debug("Starting email processing cycle")
            
            # Get cursor state
            assert self.current_config.email_address is not None and self.current_config.folder_name is not None
            cursor = self.cursor_service.get_cursor_state(
                self.current_config.email_address, 
                self.current_config.folder_name
            )
            
            if not cursor:
                self.logger.warning("No cursor found - skipping processing cycle")
                return
            
            # Determine date range for email retrieval
            # Look back from cursor position or last 24 hours if no cursor
            if cursor.last_processed_received_date:
                # Use cursor date without buffer - we'll handle duplicates by message ID
                start_date = cursor.last_processed_received_date
                self.logger.debug(f"Processing emails since cursor date: {start_date}")
            else:
                # No previous processing - look back based on max_backlog_hours
                hours_back = self.current_config.max_backlog_hours or 24
                start_date = datetime.now(timezone.utc) - timedelta(hours=hours_back)
                self.logger.debug(f"No cursor date - looking back {hours_back} hours from {start_date}")
            
            # Get emails from Outlook using cursor-based retrieval
            self.logger.info(f"Searching for emails from {start_date} onwards...")
            emails = self.outlook_service.get_recent_emails(
                limit=100,  # Process in batches
                start_date=start_date
            )
            self.logger.debug(f"Found {len(emails)} emails in date range")
            
            if not emails:
                self.logger.debug("No emails found in date range - cycle complete")
                return
                
            self.logger.info(f"Retrieved {len(emails)} emails from Outlook")
            
            # Process each email
            processed_count = 0
            latest_email_date = cursor.last_processed_received_date
            
            for i, email_data in enumerate(emails):
                try:
                    self.logger.debug(f"Email {i+1}/{len(emails)}: '{email_data.subject}' from {email_data.sender_email} at {email_data.received_time}")
                    
                    # Skip emails we've already processed
                    if cursor.last_processed_received_date:
                        # Ensure both datetimes are timezone-naive for comparison
                        email_time = email_data.received_time
                        cursor_time = cursor.last_processed_received_date
                        
                        # Remove timezone info if present for comparison
                        if hasattr(email_time, 'replace') and email_time.tzinfo is not None:
                            email_time = email_time.replace(tzinfo=None)
                        if hasattr(cursor_time, 'replace') and cursor_time.tzinfo is not None:
                            cursor_time = cursor_time.replace(tzinfo=None)
                        
                        if email_time <= cursor_time:
                            self.logger.debug(f"Skipping email {i+1} - already processed (received {email_time} <= cursor {cursor_time})")
                            continue
                    
                    # Apply filters
                    if self._process_single_email(email_data):
                        processed_count += 1
                        self.logger.debug(f"Email {i+1} processed successfully")
                    else:
                        self.logger.debug(f"Email {i+1} was filtered out or failed processing")
                    
                    # Track latest email date for cursor update
                    if not latest_email_date or email_data.received_time > latest_email_date:
                        latest_email_date = email_data.received_time
                        
                except Exception as e:
                    subject = getattr(email_data, 'subject', 'Unknown') or 'Unknown'
                    self.logger.exception(f"Error processing email: {subject}: {e}")
                    if not hasattr(self.stats, 'processing_errors'):
                        self.stats.processing_errors = 0
                    self.stats.processing_errors += 1
            
            # Update cursor with latest processed date
            if latest_email_date and latest_email_date != cursor.last_processed_received_date:
                # Create proper EmailData object for cursor update
                cursor_email_data = EmailData(
                    message_id=f"cycle_{int(datetime.now().timestamp())}",
                    subject="",
                    sender_email="system",
                    sender_name=None,
                    received_time=latest_email_date,
                    has_attachments=False,
                    attachment_count=0,
                    attachment_filenames=[],
                    has_pdf_attachments=False,
                    body_preview=None
                )

                self.cursor_service.update_cursor(
                    self.current_config.email_address,
                    self.current_config.folder_name,
                    cursor_email_data
                )
                self.logger.debug(f"Updated cursor to {latest_email_date}")
            
            # Update statistics
            if processed_count > 0:
                if not hasattr(self.stats, 'emails_processed'):
                    self.stats.emails_processed = 0
                self.stats.emails_processed += processed_count
                
                if not hasattr(self.stats, 'last_processed_at'):
                    self.stats.last_processed_at = None
                self.stats.last_processed_at = datetime.now(timezone.utc)
                
                self.logger.info(f"Processed {processed_count} emails in this cycle")
                
        except Exception as e:
            self.logger.exception(f"Error in email processing cycle: {e}")
            # Don't re-raise - let the loop continue with error handling
    
    def _process_single_email(self, email_data: EmailData) -> bool:
        """Process a single email with filtering and rule application"""
        try:
            self.logger.debug(f"Processing email: '{email_data.subject}' from {email_data.sender_email}")
            
            # Apply email filters
            if not self.current_config or not self.current_config.filter_rules:
                self.logger.debug("No filter rules configured - accepting all emails")
                return self._handle_matching_email(email_data)
            
            # Check each filter rule
            self.logger.debug(f"Applying {len(self.current_config.filter_rules)} filter rules")
            matches_all_rules = True
            for i, rule in enumerate(self.current_config.filter_rules):
                rule_result = self._apply_filter_rule(email_data, rule)
                self.logger.debug(f"Filter rule {i+1}: {rule.field} {rule.operation} '{rule.value}' = {rule_result}")
                if not rule_result:
                    matches_all_rules = False
                    break
            
            if matches_all_rules:
                self.logger.debug(f"Email matches all filters: {email_data.subject}")
                return self._handle_matching_email(email_data)
            else:
                self.logger.debug(f"Email filtered out by rules: {email_data.subject}")
                return False
                
        except Exception as e:
            self.logger.exception(f"Error processing single email: {e}")
            return False
    
    def _apply_filter_rule(self, email_data: EmailData, rule) -> bool:
        """Apply a single filter rule to an email"""
        try:
            field_value = None
            
            # Get the field value to check
            if rule.field == "sender_email":
                field_value = email_data.sender_email or ""
            elif rule.field == "subject":
                field_value = email_data.subject or ""
            elif rule.field == "has_attachments":
                # Special handling for boolean field
                expected_value = rule.value.lower() in ['true', '1', 'yes']
                return email_data.has_attachments == expected_value
            elif rule.field == "received_date":
                # Date field handling would need additional logic
                self.logger.warning(f"Date filtering not yet implemented for rule: {rule.field}")
                # For unimplemented features, be conservative and reject the email
                return False
            else:
                self.logger.warning(f"Unknown filter field: {rule.field}")
                # For unknown fields, be conservative and reject the email
                return False
            
            # Ensure field_value is a string and not None
            if not isinstance(field_value, str):
                field_value = str(field_value) if field_value is not None else ""
            
            # Apply case sensitivity
            if not rule.case_sensitive:
                field_value = field_value.lower()
                rule_value = rule.value.lower() if rule.value else ""
            else:
                rule_value = rule.value if rule.value else ""
            
            # Apply the operation
            if rule.operation == "contains":
                return rule_value in field_value
            elif rule.operation == "equals":
                return field_value == rule_value
            elif rule.operation == "starts_with":
                return field_value.startswith(rule_value)
            elif rule.operation == "ends_with":
                return field_value.endswith(rule_value)
            else:
                self.logger.warning(f"Unknown filter operation: {rule.operation}")
                # For unknown operations, be conservative and reject the email
                return False
                
        except Exception as e:
            self.logger.exception(f"Error applying filter rule: {e}")
            # On any error, be conservative and reject the email
            return False
    
    def _handle_matching_email(self, email_data: EmailData) -> bool:
        """Handle an email that passed all filters"""
        try:
            self.logger.debug(f"Handling matching email: {email_data.subject}")
            
            # Check if email already exists to avoid duplicates
            if self.email_repo.email_exists_by_message_id(email_data.message_id):
                self.logger.debug(f"Email already exists: {email_data.subject}")
                return True
            
            # Create domain object for email record
            assert self.current_config is not None
            email_record_create = EmailCreate(
                message_id=email_data.message_id,
                subject=email_data.subject,
                sender_email=email_data.sender_email,
                sender_name=email_data.sender_name,
                received_date=email_data.received_time,
                folder_name=self.current_config.folder_name,
                has_pdf_attachments=email_data.has_pdf_attachments,
                attachment_count=email_data.attachment_count
            )

            # Save email record to database
            email_record = self.email_repo.create_email_record(email_record_create)
            self.logger.info(f"Saved email record: {email_record.subject} (ID: {email_record.id})")
            
            # Process PDF attachments if present (using pre-extracted data)
            pdf_records = []
            if email_data.has_pdf_attachments:
                self.logger.debug(f"  Processing {len(email_data.pdf_attachments_data)} PDF attachments")
                try:
                    # Process each pre-extracted PDF attachment
                    for pdf_data in email_data.pdf_attachments_data:
                        pdf_record = self._process_extracted_pdf(pdf_data, email_record.id)
                        if pdf_record:
                            pdf_records.append(pdf_record)
                    
                    # Update statistics
                    for pdf_record in pdf_records:
                        if not pdf_record.get('duplicate', False):
                            self.stats.pdfs_found += 1
                    
                    self.logger.info(f"  Processed {len(pdf_records)} PDF records (including {sum(1 for p in pdf_records if p.get('duplicate', False))} duplicates)")
                    
                    # Update config statistics
                    if self.current_config and self.current_config.id:
                        self.config_service.increment_processing_stats(
                            self.current_config.id, 
                            emails=1, 
                            pdfs=len([p for p in pdf_records if not p.get('duplicate', False)])
                        )
                        
                except Exception as e:
                    self.logger.error(f"Error processing PDF attachments for email {email_record.id}: {e}")
                    # Continue processing even if PDF extraction fails
            else:
                # Update config statistics for emails without PDFs
                if self.current_config and self.current_config.id:
                    self.config_service.increment_processing_stats(
                        self.current_config.id, 
                        emails=1, 
                        pdfs=0
                    )
            
            return True
            
        except Exception as e:
            self.logger.exception(f"Error handling matching email: {e}")
            return False
    
    def _process_extracted_pdf(self, pdf_data: Dict[str, Any], email_id: int) -> Optional[Dict[str, Any]]:
        """
        Process pre-extracted PDF bytes from COM service
        
        Args:
            pdf_data: Dictionary with 'filename', 'size', 'content_bytes'
            email_id: Database ID of the email
            
        Returns:
            Dict with PDF processing results or None if failed
        """
        try:
            filename = pdf_data['filename']
            content_bytes = pdf_data['content_bytes']
            file_size = pdf_data['size']
            
            self.logger.debug(f"Processing extracted PDF: {filename} ({file_size} bytes)")
            
            # Validate PDF content
            if not self._validate_pdf_content(content_bytes):
                self.logger.warning(f"Invalid PDF content for: {filename}")
                return None
            
            # Store PDF using the shared PDF processing service with domain object
            store_request = PdfStoreRequest(
                original_filename=filename,
                email_id=email_id,
                filename=os.path.basename(filename),
                mime_type='application/pdf'
            )
            
            pdf_service = get_pdf_processing_service()
            if not pdf_service:
                logger.error("PDF processing service not available")
                return None

            pdf_file = pdf_service.store_pdf(content_bytes, store_request)
            assert pdf_file.id is not None
            pdf_id = pdf_file.id

            # Extract PDF objects for template matching
            try:
                logger.debug(f"Extracting PDF objects for {filename}")
                pdf_service.extract_pdf_objects(pdf_id)
            except Exception as extract_error:
                self.logger.error(f"Error during PDF object extraction for {filename}: {extract_error}")
                # Continue processing even if object extraction fails
            
            # Auto-trigger ETO processing by creating ETO run record
            eto_run_create = EtoRunCreate(
                email_id=email_id,
                pdf_file_id=pdf_id,
                status='not_started'
            )

            try:
                eto_run = self.eto_run_repo.create(eto_run_create)
                eto_run_id = eto_run.id if eto_run else None
                self.logger.debug(f"Created ETO run {eto_run_id} for PDF {pdf_id}")
            except Exception as eto_error:
                self.logger.error(f"Failed to create ETO run for PDF {pdf_id}: {eto_error}")
                # Don't fail the entire PDF processing if ETO run creation fails
                eto_run_id = None
            
            self.logger.info(f"Successfully processed PDF {filename} -> record {pdf_id}, ETO run {eto_run_id}")
            
            return {
                'id': pdf_id,
                'filename': pdf_file.filename,
                'file_size': pdf_file.file_size,
                'sha256_hash': pdf_file.sha256_hash,
                'duplicate': False,
                'eto_run_id': eto_run_id
            }
            
        except Exception as e:
            self.logger.error(f"Error processing extracted PDF {pdf_data.get('filename', 'unknown')}: {e}")
            return None
    
    def _validate_pdf_content(self, content: bytes) -> bool:
        """Validate that content is a valid PDF file"""
        try:
            # Check minimum file size
            if len(content) < 10:
                self.logger.debug("Content too small to be a valid PDF")
                return False
            
            # Check PDF magic bytes at start of file
            if not content.startswith(b'%PDF-'):
                self.logger.debug("Content does not start with PDF magic bytes")
                return False
            
            # Check for PDF version (should be something like %PDF-1.4)
            header = content[:10].decode('ascii', errors='ignore')
            if not header.startswith('%PDF-1.'):
                self.logger.debug(f"Invalid PDF version header: {header}")
                return False
            
            # Check for EOF marker (basic validation)
            content_str = content.decode('latin-1', errors='ignore')
            if '%%EOF' not in content_str:
                self.logger.debug("PDF missing EOF marker")
                return False
            
            self.logger.debug("PDF content validation passed")
            return True
            
        except Exception as e:
            self.logger.warning(f"Error validating PDF content: {e}")
            return False