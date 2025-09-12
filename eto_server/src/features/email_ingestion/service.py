"""
Email Ingestion Service
Main orchestrator for email processing with automatic startup and downtime recovery
"""
import asyncio
import logging
import threading
import time
from typing import Dict, List, Any, Optional
from datetime import datetime, timedelta, timezone
from dataclasses import dataclass, field

from .config_service import EmailIngestionConfigurationService
from .filter_service import EmailIngestionFilterService
from .cursor_service import EmailIngestionCursorService
from .types import EmailIngestionConfig, IngestionStats, ServiceHealth, EmailData, EmailConnectionConfig
from .integrations.outlook_com_service import OutlookComService
from ...shared.database import get_connection_manager
from ...shared.database.repositories import EmailIngestionConfigRepository, EmailIngestionCursorRepository

logger = logging.getLogger(__name__)


class EmailIngestionService:
    """Main orchestrator for email processing with automatic startup and downtime recovery"""
    
    def __init__(self):
        self.connection_manager = get_connection_manager()
        assert self.connection_manager is not None
        
        # Repository dependencies
        self.config_repo = EmailIngestionConfigRepository(self.connection_manager)
        self.cursor_repo = EmailIngestionCursorRepository(self.connection_manager)
        
        # Service dependencies
        self.config_service = EmailIngestionConfigurationService()
        self.filter_service = EmailIngestionFilterService()
        self.cursor_service = EmailIngestionCursorService(self.cursor_repo)
        self.outlook_service = OutlookComService()
        
        # Service state
        self.is_running = False
        self.is_connected = False
        self.current_config: Optional[EmailIngestionConfig] = None
        self.processing_thread: Optional[threading.Thread] = None
        self.stop_event = threading.Event()
        
        # Statistics and health
        self.stats = IngestionStats()
        self.health = ServiceHealth()
        
        self.logger = logging.getLogger(__name__)

    # === High-Level API Methods ===
    
    def start_ingestion(self, config_id: Optional[int] = None) -> Dict[str, Any]:
        """Start email ingestion with active configuration"""
        try:
            if self.is_running:
                return {
                    "success": False,
                    "message": "Email ingestion is already running",
                    "is_running": True
                }
            
            # Load configuration (either specified config_id or active configuration)
            if config_id:
                self.current_config = self.config_service.get_configuration(config_id)
                if not self.current_config:
                    return {
                        "success": False,
                        "message": f"Email configuration {config_id} not found",
                        "is_running": False
                    }
                if not self.current_config.is_active:
                    return {
                        "success": False,
                        "message": f"Email configuration {config_id} is not active",
                        "is_running": False
                    }
            else:
                self.current_config = self.config_service.get_active_configuration()
                if not self.current_config:
                    return {
                        "success": False,
                        "message": "No active email configuration found",
                        "is_running": False
                    }
            
            # Validate that email address is provided
            if not self.current_config.email_address:
                return {
                    "success": False,
                    "message": "Active configuration missing required email address",
                    "is_running": False
                }
            
            # Initialize cursor for the active configuration
            connection_config = EmailConnectionConfig(
                email_address=self.current_config.email_address,
                folder_name=self.current_config.folder_name
            )
            
            # Create or get existing cursor
            cursor = asyncio.run(self.cursor_service.initialize_cursor(connection_config))
            if not cursor:
                return {
                    "success": False,
                    "message": f"Failed to initialize cursor for {self.current_config.folder_name}",
                    "is_running": False
                }
            
            # Update configuration status to running
            self.config_repo.update(self.current_config.id, {"is_running": True})
            
            # Connect to Outlook service
            try:
                # Connect to Outlook service
                connection_config = EmailConnectionConfig(
                    email_address=self.current_config.email_address,
                    folder_name=self.current_config.folder_name
                )
                outlook_result = asyncio.run(self.outlook_service.connect(connection_config))
                
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
                self.health.configuration_loaded = True
                
                self.logger.info(f"Email ingestion service started for config: {self.current_config.name}")
                self.logger.info(f"Monitoring folder: {self.current_config.folder_name}")
                self.logger.info(f"Cursor initialized with last processed: {cursor.last_processed_received_date}")
                
                return {
                    "success": True,
                    "message": "Email ingestion started successfully",
                    "config_name": self.current_config.name,
                    "config_id": self.current_config.id,
                    "folder_name": self.current_config.folder_name,
                    "cursor_id": cursor.id,
                    "is_running": True,
                    "is_connected": True
                }
                
            except Exception as e:
                self.logger.exception(f"Failed to connect to Outlook service: {e}")
                # Rollback the running status
                self.config_repo.update(self.current_config.id, {"is_running": False})
                return {
                    "success": False,
                    "message": f"Failed to connect to email service: {str(e)}",
                    "is_running": False
                }
            
        except Exception as e:
            self.logger.exception(f"Error starting email ingestion: {e}")
            return {
                "success": False,
                "error": str(e),
                "message": "Failed to start email ingestion"
            }
    
    def stop_ingestion(self) -> Dict[str, Any]:
        """Stop email ingestion"""
        try:
            if not self.is_running:
                return {
                    "success": False,
                    "message": "Email ingestion is not running",
                    "is_running": False
                }
            
            # Stop processing and cleanup
            try:
                # Update current configuration to not running
                if self.current_config:
                    self.config_repo.update(self.current_config.id, {"is_running": False})
                
                # Stop processing thread if running
                if self.processing_thread and self.processing_thread.is_alive():
                    self.stop_event.set()
                    self.processing_thread.join(timeout=5.0)
                
                # Disconnect from Outlook
                disconnect_result = asyncio.run(self.outlook_service.disconnect())
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
                
                return {
                    "success": True,
                    "message": "Email ingestion stopped successfully",
                    "is_running": False,
                    "is_connected": False
                }
                
            except Exception as e:
                self.logger.exception(f"Error during ingestion stop cleanup: {e}")
                # Force state reset even if cleanup failed
                self.is_running = False
                self.is_connected = False
                self.health.is_running = False
                self.health.is_connected = False
                
                return {
                    "success": True,
                    "message": "Email ingestion stopped (with cleanup errors)",
                    "is_running": False,
                    "warning": f"Cleanup error: {str(e)}"
                }
            
        except Exception as e:
            self.logger.exception(f"Error stopping email ingestion: {e}")
            return {
                "success": False,
                "error": str(e),
                "message": "Failed to stop email ingestion"
            }
    
    def get_ingestion_status(self) -> Dict[str, Any]:
        """Get current ingestion status"""
        return {
            "is_running": self.is_running,
            "is_connected": self.is_connected,
            "current_config": self.current_config.name if self.current_config else None,
            "stats": {
                "emails_processed": self.stats.emails_processed,
                "emails_filtered": self.stats.emails_filtered,
                "pdfs_extracted": self.stats.pdfs_extracted,
                "processing_errors": self.stats.processing_errors,
                "uptime_seconds": self.stats.uptime_seconds
            },
            "health": {
                "configuration_loaded": self.health.configuration_loaded,
                "last_error": self.health.last_error
            }
        }

    # === Internal Processing Methods ===
    
    def _run_processing_loop(self):
        """Main processing loop that runs in a separate thread"""
        self.logger.info("Email processing loop started")
        
        try:
            while not self.stop_event.is_set():
                try:
                    # Run async processing cycle
                    loop = asyncio.new_event_loop()
                    asyncio.set_event_loop(loop)
                    loop.run_until_complete(self._process_emails_cycle())
                    loop.close()
                    
                    # Wait for next cycle (use poll interval from config)
                    poll_interval = self.current_config.poll_interval_seconds if self.current_config else 60
                    if self.stop_event.wait(poll_interval):
                        break  # Stop event was set during wait
                        
                except Exception as e:
                    self.logger.exception(f"Error in processing cycle: {e}")
                    self.health.last_error = str(e)
                    
                    # Wait before retrying on error
                    if self.stop_event.wait(30):
                        break
                        
        except Exception as fatal_error:
            self.logger.exception(f"Fatal error in processing loop: {fatal_error}")
            self.health.last_error = str(fatal_error)
            
        finally:
            self.logger.info("Email processing loop stopped")
    
    async def _process_emails_cycle(self):
        """Single processing cycle - check for new emails and process them"""
        if not self.current_config or not self.is_running:
            return
            
        try:
            self.logger.debug("Starting email processing cycle")
            
            # Get cursor state
            cursor = await self.cursor_service.get_cursor_state(
                self.current_config.email_address, 
                self.current_config.folder_name
            )
            
            if not cursor:
                self.logger.warning("No cursor found - skipping processing cycle")
                return
            
            # Determine date range for email retrieval
            # Look back from cursor position or last 24 hours if no cursor
            if cursor.last_processed_received_date:
                start_date = cursor.last_processed_received_date
                self.logger.debug(f"Processing emails since cursor date: {start_date}")
            else:
                # No previous processing - look back based on max_backlog_hours
                from datetime import timedelta
                hours_back = self.current_config.max_backlog_hours or 24
                start_date = datetime.now(timezone.utc) - timedelta(hours=hours_back)
                self.logger.debug(f"No cursor date - looking back {hours_back} hours from {start_date}")
            
            # Get emails from Outlook
            emails_result = await self.outlook_service.get_emails_in_date_range(
                start_date=start_date,
                end_date=datetime.now(timezone.utc)
            )
            
            if not emails_result.get("success", False):
                self.logger.warning(f"Failed to retrieve emails: {emails_result.get('error')}")
                return
            
            emails = emails_result.get("emails", [])
            self.logger.info(f"Retrieved {len(emails)} emails from Outlook")
            
            # Process each email
            processed_count = 0
            latest_email_date = cursor.last_processed_received_date
            
            for email_data in emails:
                try:
                    # Skip emails we've already processed
                    if (cursor.last_processed_received_date and 
                        email_data.received_time <= cursor.last_processed_received_date):
                        continue
                    
                    # Apply filters
                    if await self._process_single_email(email_data):
                        processed_count += 1
                    
                    # Track latest email date for cursor update
                    if not latest_email_date or email_data.received_time > latest_email_date:
                        latest_email_date = email_data.received_time
                        
                except Exception as e:
                    self.logger.exception(f"Error processing email: {email_data.subject}: {e}")
                    self.stats.errors_encountered = getattr(self.stats, 'errors_encountered', 0) + 1
            
            # Update cursor with latest processed date
            if latest_email_date and latest_email_date != cursor.last_processed_received_date:
                await self.cursor_service.update_cursor(
                    self.current_config.email_address,
                    self.current_config.folder_name,
                    {
                        "message_id": f"cycle_{int(datetime.now().timestamp())}",
                        "received_date": latest_email_date
                    }
                )
                self.logger.debug(f"Updated cursor to {latest_email_date}")
            
            # Update statistics
            if processed_count > 0:
                self.stats.emails_processed = getattr(self.stats, 'emails_processed', 0) + processed_count
                self.stats.last_processing_time = datetime.now(timezone.utc)
                self.logger.info(f"Processed {processed_count} emails in this cycle")
                
        except Exception as e:
            self.logger.exception(f"Error in email processing cycle: {e}")
            raise
    
    async def _process_single_email(self, email_data: EmailData) -> bool:
        """Process a single email with filtering and rule application"""
        try:
            self.logger.debug(f"Processing email: {email_data.subject} from {email_data.sender_email}")
            
            # Apply email filters
            if not self.current_config or not self.current_config.filter_rules:
                self.logger.debug("No filter rules configured - accepting all emails")
                return await self._handle_matching_email(email_data)
            
            # Check each filter rule
            matches_all_rules = True
            for rule in self.current_config.filter_rules:
                if not self._apply_filter_rule(email_data, rule):
                    matches_all_rules = False
                    break
            
            if matches_all_rules:
                self.logger.info(f"Email matches filters: {email_data.subject}")
                return await self._handle_matching_email(email_data)
            else:
                self.logger.debug(f"Email filtered out: {email_data.subject}")
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
                field_value = email_data.sender_email
            elif rule.field == "subject":
                field_value = email_data.subject
            elif rule.field == "has_attachments":
                # Special handling for boolean field
                expected_value = rule.value.lower() in ['true', '1', 'yes']
                return email_data.has_attachments == expected_value
            elif rule.field == "received_date":
                # Date field handling would need additional logic
                self.logger.warning(f"Date filtering not yet implemented for rule: {rule.field}")
                return True
            else:
                self.logger.warning(f"Unknown filter field: {rule.field}")
                return True
            
            if field_value is None:
                return False
            
            # Apply the operation
            if not rule.case_sensitive:
                field_value = field_value.lower()
                rule_value = rule.value.lower()
            else:
                rule_value = rule.value
            
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
                return True
                
        except Exception as e:
            self.logger.exception(f"Error applying filter rule: {e}")
            return False
    
    async def _handle_matching_email(self, email_data: EmailData) -> bool:
        """Handle an email that passed all filters"""
        try:
            self.logger.info(f"Handling matching email: {email_data.subject}")
            
            # For now, just log the email details and count it as processed
            # In a full implementation, this would:
            # 1. Save email to database
            # 2. Download PDF attachments
            # 3. Create ETO runs
            # 4. Send to processing pipeline
            
            self.logger.info(f"  From: {email_data.sender_email}")
            self.logger.info(f"  Subject: {email_data.subject}")
            self.logger.info(f"  Received: {email_data.received_time}")
            self.logger.info(f"  Has attachments: {email_data.has_attachments}")
            
            if email_data.has_attachments:
                self.logger.info(f"  Attachment count: {email_data.attachment_count}")
                if email_data.has_pdf_attachments:
                    self.logger.info("  Contains PDF attachments - would process for ETO")
                    # Increment PDF stats
                    self.stats.pdfs_found = getattr(self.stats, 'pdfs_found', 0) + 1
            
            return True
            
        except Exception as e:
            self.logger.exception(f"Error handling matching email: {e}")
            return False