"""
Email Listener Thread
Worker thread that polls email provider and calls back to service for processing
"""
import logging
import threading
import time
from typing import Optional, Callable, Any
from datetime import datetime, timezone, timedelta

from shared.types import EmailConfig, EmailMessage, EmailAttachment
from features.email_ingestion.integrations.base_integration import BaseEmailIntegration
from shared.utils import DateTimeUtils

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
        # Ensure timezone consistency: convert DB time to UTC-aware
        if config.last_check_time:
            if config.last_check_time.tzinfo is None:
                # Assume naive datetimes from DB are UTC
                self.last_check_time = config.last_check_time.replace(tzinfo=timezone.utc)
            else:
                self.last_check_time = config.last_check_time.astimezone(timezone.utc)
        else:
            self.last_check_time = DateTimeUtils.utc_now()

        # Store activation time for fresh activation detection
        # This is the time when this listener thread was created (activation time)
        self.activation_time = DateTimeUtils.utc_now()
        
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

    def _apply_filter_rules(self, emails):
        """Apply filter rules to emails"""
        if not self.config.filter_rules or len(self.config.filter_rules) == 0:
            logger.debug(f"No filter rules set for config {self.config.id} - processing all emails")
            return emails

        filtered_emails = []
        logger.debug(f"Applying {len(self.config.filter_rules)} filter rules to {len(emails)} emails")

        for email in emails:
            email_passes = False

            for rule in self.config.filter_rules:
                try:
                    if self._check_filter_rule(email, rule):
                        email_passes = True
                        logger.debug(f"Email {email.message_id[:20]}... passed filter: {rule.field} {rule.operation} '{rule.value}'")
                        break
                except Exception as e:
                    logger.warning(f"Error applying filter rule {rule.field} {rule.operation} '{rule.value}': {e}")
                    continue

            if email_passes:
                filtered_emails.append(email)
                logger.debug(f"Email {email.message_id[:20]}... from {email.sender_email} passed filters")
            else:
                logger.debug(f"Email {email.message_id[:20]}... from {email.sender_email} filtered out")

        return filtered_emails

    def _check_filter_rule(self, email, rule):
        """Check if an email passes a single filter rule"""
        field_value = None

        # Get the field value from the email
        if rule.field == 'sender_email':
            field_value = email.sender_email
        elif rule.field == 'subject':
            field_value = email.subject
        elif rule.field == 'has_attachments':
            field_value = email.has_attachments
        elif rule.field == 'received_date':
            field_value = email.received_date
        else:
            logger.warning(f"Unknown filter field: {rule.field}")
            return True  # Unknown fields pass by default

        # Apply the operation
        if rule.operation == 'equals':
            if rule.field in ['sender_email', 'subject']:
                if rule.case_sensitive:
                    return field_value == rule.value
                else:
                    return field_value.lower() == rule.value.lower()
            else:
                return str(field_value) == rule.value

        elif rule.operation == 'contains':
            if rule.case_sensitive:
                return rule.value in field_value
            else:
                return rule.value.lower() in field_value.lower()

        elif rule.operation == 'starts_with':
            if rule.case_sensitive:
                return field_value.startswith(rule.value)
            else:
                return field_value.lower().startswith(rule.value.lower())

        elif rule.operation == 'ends_with':
            if rule.case_sensitive:
                return field_value.endswith(rule.value)
            else:
                return field_value.lower().endswith(rule.value.lower())

        elif rule.operation == 'before':
            if rule.field == 'received_date':
                try:
                    compare_date = datetime.fromisoformat(rule.value.replace('Z', '+00:00'))
                    return field_value < compare_date
                except:
                    return True

        elif rule.operation == 'after':
            if rule.field == 'received_date':
                try:
                    compare_date = datetime.fromisoformat(rule.value.replace('Z', '+00:00'))
                    return field_value > compare_date
                except:
                    return True

        logger.warning(f"Unknown filter operation: {rule.operation}")
        return True  # Unknown operations pass by default
    
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

            # Apply filter rules
            filtered_emails = self._apply_filter_rules(emails)
            logger.info(f"After filters: {len(filtered_emails)}/{len(emails)} emails passed (filtered out {len(emails) - len(filtered_emails)})")

            # Process each filtered email
            for email_msg in filtered_emails:
                try:
                    email_start_time = time.time()
                    logger.info(f"Starting to process email {email_msg.message_id[:20]}... from {email_msg.sender_email}")

                    # Use cached attachments for better performance
                    attachments = email_msg.cached_attachments
                    logger.info(f"Using {len(attachments)} pre-cached attachments")

                    # Call back to service for processing
                    callback_start_time = time.time()
                    logger.info(f"Starting email processing callback for {email_msg.message_id[:20]}...")

                    self.process_callback(email_msg, attachments)

                    callback_duration = time.time() - callback_start_time
                    total_duration = time.time() - email_start_time
                    logger.info(f"Completed email {email_msg.message_id[:20]}... processing: "
                               f"callback={callback_duration:.2f}s, total={total_duration:.2f}s")
                    
                    # Update last check time to email's received date if newer
                    if email_msg.received_date > self.last_check_time:
                        self.last_check_time = email_msg.received_date
                    
                except Exception as e:
                    logger.error(f"Error processing email {email_msg.message_id}: {e}")
                    continue
            
            # Update last check time to now
            self.last_check_time = DateTimeUtils.utc_now()
            
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