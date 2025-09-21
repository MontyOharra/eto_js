"""
Email Ingestion Service
Main orchestrator for email processing with multi-config support
"""
import logging
import threading
from typing import Dict, List, Optional, Set
from datetime import datetime, timezone
from dataclasses import dataclass

from shared.services import get_pdf_processing_service, get_eto_processing_service
from shared.database import get_connection_manager
from shared.exceptions import ObjectNotFoundError, ValidationError
from shared.models.email_config import EmailConfig
from .cursor_service import EmailIngestionCursorService
from .integrations.outlook_com_service import OutlookComService
from shared.database.repositories import EmailRepository, EmailIngestionCursorRepository

logger = logging.getLogger(__name__)


@dataclass
class EmailListener:
    """Represents an active email listener for a specific configuration"""
    config_id: int
    config: EmailConfig
    thread: threading.Thread
    stop_event: threading.Event
    outlook_service: OutlookComService
    is_connected: bool = False
    last_error: Optional[str] = None
    emails_processed: int = 0
    pdfs_found: int = 0


class EmailIngestionService:
    """
    Main orchestrator for email processing with multi-config support.
    Manages multiple concurrent email listeners, each with their own cursor.
    """

    def __init__(self, connection_manager=None):
        # Infrastructure
        self.connection_manager = connection_manager or get_connection_manager()
        
        # Repositories (only what this service directly needs)
        self.cursor_repo = EmailIngestionCursorRepository(self.connection_manager)
        self.email_repo = EmailRepository(self.connection_manager)
        
        # Services
        self.cursor_service = EmailIngestionCursorService(self.cursor_repo)
        
        # Active listeners management
        self.active_listeners: Dict[int, EmailListener] = {}
        self.listeners_lock = threading.Lock()
        
        # Service state
        self.is_running = False
        self.logger = logging.getLogger(__name__)

    # === Listener Management ===
    
    def start_listener(self, config: EmailConfig) -> bool:
        """
        Start an email listener for a specific configuration.
        Creates cursor if needed and starts background processing thread.
        """
        with self.listeners_lock:
            # Check if already running
            if config.id in self.active_listeners:
                logger.warning(f"Listener for config {config.id} is already running")
                return False
            
            try:
                # Create cursor if it doesn't exist
                cursor = self.cursor_service.get_or_create_cursor(
                    config_id=config.id,
                    email_address=config.email_address,
                    folder_name=config.folder_name
                )
                
                # Create listener
                stop_event = threading.Event()
                outlook_service = OutlookComService()
                
                listener = EmailListener(
                    config_id=config.id,
                    config=config,
                    thread=None,  # Will be set after thread creation
                    stop_event=stop_event,
                    outlook_service=outlook_service
                )
                
                # Create and start processing thread
                thread = threading.Thread(
                    target=self._process_emails,
                    args=(listener,),
                    name=f"email-listener-{config.id}"
                )
                listener.thread = thread
                
                # Store and start
                self.active_listeners[config.id] = listener
                thread.start()
                
                logger.info(f"Started email listener for config {config.id} ({config.name})")
                return True
                
            except Exception as e:
                logger.error(f"Failed to start listener for config {config.id}: {e}")
                return False
    
    def stop_listener(self, config_id: int) -> bool:
        """Stop a specific email listener"""
        with self.listeners_lock:
            if config_id not in self.active_listeners:
                logger.warning(f"No active listener for config {config_id}")
                return False
            
            listener = self.active_listeners[config_id]
            
            # Signal stop
            listener.stop_event.set()
            
            # Wait for thread to finish (with timeout)
            listener.thread.join(timeout=10)
            
            if listener.thread.is_alive():
                logger.error(f"Listener thread for config {config_id} did not stop gracefully")
            
            # Disconnect Outlook
            if listener.outlook_service:
                listener.outlook_service.disconnect()
            
            # Remove from active listeners
            del self.active_listeners[config_id]
            
            logger.info(f"Stopped email listener for config {config_id}")
            return True
    
    def restart_listener(self, config: EmailConfig) -> bool:
        """Restart a listener with updated configuration"""
        # Stop if running
        if config.id in self.active_listeners:
            self.stop_listener(config.id)
        
        # Start with new config
        return self.start_listener(config)
    
    def stop_all_listeners(self):
        """Stop all active email listeners"""
        config_ids = list(self.active_listeners.keys())
        for config_id in config_ids:
            self.stop_listener(config_id)
    
    def get_active_listener_ids(self) -> Set[int]:
        """Get IDs of all configs with active listeners"""
        with self.listeners_lock:
            return set(self.active_listeners.keys())
    
    def is_listener_running(self, config_id: int) -> bool:
        """Check if a specific config has an active listener"""
        with self.listeners_lock:
            return config_id in self.active_listeners
    
    # === Cursor Management ===
    
    def create_cursor_for_config(self, config_id: int, email_address: str, folder_name: str):
        """Create a cursor for a new configuration"""
        return self.cursor_service.create_cursor(
            config_id=config_id,
            email_address=email_address,
            folder_name=folder_name
        )
    
    def delete_cursor_for_config(self, config_id: int):
        """Delete cursor associated with a configuration"""
        # Stop listener first if running
        if self.is_listener_running(config_id):
            raise ValidationError(f"Cannot delete cursor for active config {config_id}. Stop listener first.")
        
        return self.cursor_service.delete_cursor_by_config(config_id)
    
    def get_cursor_stats(self, config_id: int):
        """Get cursor statistics for a configuration"""
        return self.cursor_service.get_cursor_stats_by_config(config_id)
    
    # === Config Activation Management ===
    
    def activate_config(self, config: EmailConfig):
        """
        Activate a configuration - starts its listener.
        Does NOT handle deactivation of other configs (that's ConfigService's job).
        """
        if not config.is_active:
            raise ValidationError(f"Cannot activate inactive config {config.id}")
        
        return self.start_listener(config)
    
    def deactivate_config(self, config_id: int):
        """Deactivate a configuration - stops its listener"""
        return self.stop_listener(config_id)
    
    # === Status and Statistics ===
    
    def get_service_status(self) -> Dict:
        """Get overall service status"""
        with self.listeners_lock:
            return {
                "is_running": len(self.active_listeners) > 0,
                "active_listeners": len(self.active_listeners),
                "listener_details": [
                    {
                        "config_id": listener.config_id,
                        "config_name": listener.config.name,
                        "email_address": listener.config.email_address,
                        "folder_name": listener.config.folder_name,
                        "is_connected": listener.is_connected,
                        "emails_processed": listener.emails_processed,
                        "pdfs_found": listener.pdfs_found,
                        "last_error": listener.last_error
                    }
                    for listener in self.active_listeners.values()
                ]
            }
    
    # === Email Processing (Private) ===
    
    def _process_emails(self, listener: EmailListener):
        """
        Background thread function for processing emails.
        Runs continuously until stop_event is set.
        """
        config = listener.config
        
        try:
            # Connect to Outlook
            if not listener.outlook_service.connect(config.email_address):
                listener.last_error = "Failed to connect to Outlook"
                logger.error(f"Failed to connect to Outlook for config {config.id}")
                return
            
            listener.is_connected = True
            logger.info(f"Connected to Outlook for config {config.id}")
            
            # Get PDF and ETO services
            pdf_service = get_pdf_processing_service()
            eto_service = get_eto_processing_service()
            
            # Main processing loop
            while not listener.stop_event.is_set():
                try:
                    # Get cursor state
                    cursor = self.cursor_service.get_cursor_by_config(config.id)
                    if not cursor:
                        logger.error(f"No cursor found for config {config.id}")
                        break
                    
                    # Fetch emails since last processed
                    emails = listener.outlook_service.fetch_emails_since(
                        folder_name=config.folder_name,
                        since_date=cursor.last_processed_received_date
                    )
                    
                    # Apply filter rules if configured
                    if config.filter_rules:
                        emails = self._apply_filter_rules(emails, config.filter_rules)
                    
                    # Process each email
                    for email_data in emails:
                        if listener.stop_event.is_set():
                            break
                        
                        # Skip if we've already processed this message
                        if email_data['message_id'] == cursor.last_processed_message_id:
                            continue
                        
                        # Process email (extract PDFs, etc.)
                        pdf_count = self._process_single_email(email_data, config, pdf_service, eto_service)
                        
                        # Update statistics
                        listener.emails_processed += 1
                        listener.pdfs_found += pdf_count
                        
                        # Update cursor
                        self.cursor_service.update_cursor(
                            config_id=config.id,
                            last_message_id=email_data['message_id'],
                            last_received_date=email_data['received_time'],
                            increment_emails=1,
                            increment_pdfs=pdf_count
                        )
                    
                    # Wait before next poll
                    listener.stop_event.wait(config.poll_interval_seconds)
                    
                except Exception as e:
                    listener.last_error = str(e)
                    logger.error(f"Error processing emails for config {config.id}: {e}")
                    
                    # Wait before retry
                    retry_wait = min(config.error_retry_attempts * 10, 300)  # Max 5 minutes
                    listener.stop_event.wait(retry_wait)
            
        finally:
            # Cleanup
            listener.is_connected = False
            if listener.outlook_service:
                listener.outlook_service.disconnect()
            logger.info(f"Email processing thread stopped for config {config.id}")
    
    def _process_single_email(self, email_data: Dict, config: EmailConfig, pdf_service, eto_service) -> int:
        """Process a single email and return number of PDFs found"""
        pdf_count = 0
        
        try:
            # Store email record
            email_record = {
                'message_id': email_data['message_id'],
                'subject': email_data['subject'],
                'sender': email_data['sender'],
                'received_time': email_data['received_time'],
                'has_attachments': email_data.get('has_attachments', False),
                'config_id': config.id,
                'folder_name': config.folder_name
            }
            
            # Store in repository
            # Note: EmailRepository would need to be updated to handle this
            # For now, we'll skip the actual storage
            # self.email_repo.create(email_record)
            
            # Extract and process PDFs if attachments exist
            if email_data.get('has_attachments'):
                attachments = email_data.get('attachments', [])
                for attachment in attachments:
                    if attachment.get('filename', '').lower().endswith('.pdf'):
                        # Process PDF through PDF service
                        # This would involve extracting the attachment and storing it
                        pdf_count += 1
                        
                        # Note: Actual PDF processing would go here
                        # pdf_service.process_pdf(attachment_data)
            
            logger.debug(f"Processed email {email_data['message_id']}: {pdf_count} PDFs found")
            
        except Exception as e:
            logger.error(f"Error processing email {email_data.get('message_id')}: {e}")
        
        return pdf_count
    
    def _apply_filter_rules(self, emails: List[Dict], filter_rules: List[Dict]) -> List[Dict]:
        """Apply filter rules to email list"""
        filtered = []
        
        for email in emails:
            passes_filters = True
            
            for rule in filter_rules:
                field = rule.get('field')
                operation = rule.get('operation')
                value = rule.get('value')
                case_sensitive = rule.get('case_sensitive', False)
                
                email_value = email.get(field, '')
                
                if not case_sensitive:
                    email_value = str(email_value).lower()
                    value = str(value).lower()
                
                # Apply operation
                if operation == 'contains':
                    if value not in str(email_value):
                        passes_filters = False
                        break
                elif operation == 'equals':
                    if str(email_value) != str(value):
                        passes_filters = False
                        break
                elif operation == 'starts_with':
                    if not str(email_value).startswith(str(value)):
                        passes_filters = False
                        break
                elif operation == 'ends_with':
                    if not str(email_value).endswith(str(value)):
                        passes_filters = False
                        break
            
            if passes_filters:
                filtered.append(email)
        
        return filtered
    
    # === Initialization and Cleanup ===
    
    def initialize(self):
        """Initialize the service (called on app startup)"""
        logger.info("Email ingestion service initialized with multi-config support")
    
    def shutdown(self):
        """Shutdown the service (called on app shutdown)"""
        logger.info("Shutting down email ingestion service...")
        self.stop_all_listeners()
        logger.info("Email ingestion service shutdown complete")