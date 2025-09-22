"""
Email Listener Thread
Worker thread that polls email provider and calls back to service for processing
"""
import logging
import threading
from typing import Optional, Callable, Any
from datetime import datetime, timezone, timedelta

from shared.models import EmailConfig, EmailMessage, EmailAttachment
from features.email_ingestion.integrations.base_integration import BaseEmailIntegration

logger = logging.getLogger(__name__)


class EmailListenerThread(threading.Thread):
    """
    Thread for monitoring emails from a specific configuration.
    Retrieves emails using the integration and calls back to service for processing.
    """
    
    def __init__(self, 
                 config: EmailConfig,
                 integration: BaseEmailIntegration,
                 process_callback: Callable[[EmailMessage, list[EmailAttachment]], None]):
        """
        Initialize email listener thread
        
        Args:
            config: Email configuration with settings
            integration: Email integration instance (already connected)
            process_callback: Function to call for each new email found
        """
        super().__init__(name=f"EmailListener-{config.id}")
        self.config = config
        self.integration = integration
        self.process_callback = process_callback
        
        # Use poll interval from config
        self.check_interval = config.poll_interval_seconds
        
        # Thread control
        self.stop_event = threading.Event()
        self.error_count = 0
        self.max_errors = 5
        
        # Track last check time for incremental retrieval
        self.last_check_time = config.last_check_time or datetime.now(timezone.utc)

        # Store activation time for fresh activation detection
        # This is the time when this listener thread was created (activation time)
        self.activation_time = datetime.now(timezone.utc)
        
        logger.info(f"Initialized EmailListenerThread for config {config.id} "
                   f"with {self.check_interval}s interval")
    
    def run(self):
        """Main thread loop"""
        logger.info(f"Starting email listener for config {self.config.id}")
        
        while not self.stop_event.is_set():
            try:
                # Check for new emails
                self._check_and_process_emails()
                
                # Reset error count on success
                self.error_count = 0
                
                # Wait for next check
                self.stop_event.wait(self.check_interval)
                
            except Exception as e:
                self.error_count += 1
                logger.error(f"Error in listener {self.config.id}: {e} "
                           f"(error #{self.error_count})")
                
                if self.error_count >= self.max_errors:
                    logger.critical(f"Max errors reached for config {self.config.id}, "
                                  f"stopping listener")
                    break
                
                # Exponential backoff on errors
                wait_time = min(60 * (2 ** self.error_count), 3600)  # Max 1 hour
                self.stop_event.wait(wait_time)
        
        logger.info(f"Stopped email listener for config {self.config.id}")
    
    def stop(self):
        """Signal thread to stop"""
        logger.info(f"Stopping listener for config {self.config.id}")
        self.stop_event.set()
    
    def _check_and_process_emails(self):
        """Check for new emails and process them"""
        try:
            # Calculate time window for retrieval
            since_time = self.last_check_time

            # Add small overlap to avoid missing emails, but NOT for freshly activated configs
            # Use thread's activation time to detect if this is a fresh start
            if since_time:
                # Check if this is a fresh activation (last_check_time close to thread activation time)
                time_diff = abs((since_time - self.activation_time).total_seconds())
                if time_diff > 1:  # If more than 1 second difference, it's not a fresh activation
                    since_time = since_time - timedelta(seconds=30)
                    logger.debug(f"Config {self.config.id}: Applied 30s overlap (ongoing operation)")
                else:
                    logger.info(f"Config {self.config.id}: Fresh activation detected, starting without overlap to skip deactivation-period emails")
            
            logger.debug(f"Checking emails since {since_time} for config {self.config.id}")
            
            # Get recent emails from the integration
            emails = self.integration.get_recent_emails(
                folder_name=self.config.folder_name,
                since_datetime=since_time,
                limit=100,
                include_read=True  # Process all emails, let service handle duplicates
            )
            
            logger.info(f"Found {len(emails)} emails for config {self.config.id}")
            
            # Process each email
            for email_msg in emails:
                try:
                    # Get attachments if the email has them
                    attachments = []
                    if email_msg.has_attachments:
                        try:
                            attachments = self.integration.get_attachments(
                                email_msg.message_id,
                                self.config.folder_name
                            )
                            logger.debug(f"Retrieved {len(attachments)} attachments "
                                       f"for email {email_msg.message_id}")
                        except Exception as e:
                            logger.warning(f"Failed to get attachments for "
                                         f"{email_msg.message_id}: {e}")
                    
                    # Call back to service for processing
                    self.process_callback(email_msg, attachments)
                    
                    # Update last check time to email's received date if newer
                    if email_msg.received_date > self.last_check_time:
                        self.last_check_time = email_msg.received_date
                    
                except Exception as e:
                    logger.error(f"Error processing email {email_msg.message_id}: {e}")
                    continue
            
            # Update last check time to now
            self.last_check_time = datetime.now(timezone.utc)
            
        except Exception as e:
            logger.error(f"Error checking emails for config {self.config.id}: {e}")
            raise
    
    def get_status(self) -> dict:
        """Get current status of the listener"""
        return {
            "config_id": self.config.id,
            "is_alive": self.is_alive(),
            "error_count": self.error_count,
            "last_check_time": self.last_check_time.isoformat() if self.last_check_time else None,
            "check_interval": self.check_interval
        }