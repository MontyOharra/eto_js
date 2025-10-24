"""
Email Listener Thread
Worker thread that polls email provider and calls back to service for processing
"""
import logging
import threading
import time
from typing import Callable, Any
from datetime import datetime, timezone, timedelta

from shared.types.email_integrations import EmailMessage, EmailAttachment
from shared.types.email_configs import FilterRule
from features.email_ingestion.integrations.base_integration import BaseEmailIntegration

logger = logging.getLogger(__name__)


class EmailListenerThread(threading.Thread):
    """
    Thread for monitoring emails from a specific configuration.
    Retrieves emails using the integration and calls back to service for processing.
    """

    config_id: int
    integration: BaseEmailIntegration
    filter_rules: list[FilterRule]
    poll_interval: int
    process_callback: Callable[[int, EmailMessage, list[EmailAttachment]], None]
    error_callback: Callable[[int, Exception], None]
    check_complete_callback: Callable[[int, datetime], None]
    stop_event: threading.Event
    error_count: int
    max_errors: int
    last_check_time: datetime
    activation_time: datetime

    def __init__(
        self,
        config_id: int,
        integration: BaseEmailIntegration,
        filter_rules: list[FilterRule],
        poll_interval: int,
        process_callback: Callable[[int, EmailMessage, list[EmailAttachment]], None],
        error_callback: Callable[[int, Exception], None],
        check_complete_callback: Callable[[int, datetime], None],
        last_check_time: datetime | None = None
    ) -> None:
        """
        Initialize email listener thread

        Args:
            config_id: Email configuration ID
            integration: Email integration instance (already connected)
            filter_rules: List of filter rules to apply to emails
            poll_interval: Seconds between email checks
            process_callback: Function to call for each new email (config_id, email_msg, attachments)
            error_callback: Function to call when errors occur (config_id, error)
            check_complete_callback: Function to call after each check completes (config_id, check_time)
            last_check_time: Timestamp to resume from (None = start from now, for fresh activation)
        """
        super().__init__(name=f"EmailListener-{config_id}")
        self.config_id = config_id
        self.integration = integration
        self.filter_rules = filter_rules
        self.poll_interval = poll_interval
        self.process_callback = process_callback
        self.error_callback = error_callback
        self.check_complete_callback = check_complete_callback

        # Thread control
        self.stop_event = threading.Event()
        self.error_count = 0
        self.max_errors = 5

        # Track last check time for incremental retrieval
        # Use provided last_check_time (startup recovery) or current time (fresh activation)
        self.activation_time = datetime.now(timezone.utc)
        if last_check_time is not None:
            # Resume from database value (startup recovery)
            self.last_check_time = last_check_time
            logger.info(
                f"Listener for config {config_id} resuming from last_check_time: "
                f"{last_check_time.isoformat()}"
            )
        else:
            # Fresh activation - start from now
            self.last_check_time = self.activation_time
            logger.info(
                f"Listener for config {config_id} starting fresh from activation time: "
                f"{self.activation_time.isoformat()}"
            )

        logger.info(f"Initialized EmailListenerThread for config {config_id} with {poll_interval}s interval")

    def run(self) -> None:
        """Main thread loop"""
        logger.info(f"Starting email listener for config {self.config_id}")

        while not self.stop_event.is_set():
            try:
                # Check for new emails
                self._check_and_process_emails()

                # Reset error count on success
                self.error_count = 0

                # Wait for next check
                self.stop_event.wait(self.poll_interval)

            except Exception as e:
                self.error_count += 1
                logger.error(
                    f"Error in listener {self.config_id}: {e} (error #{self.error_count})",
                    exc_info=True
                )

                # Call error callback
                try:
                    self.error_callback(self.config_id, e)
                except Exception as callback_error:
                    logger.error(f"Error in error callback: {callback_error}")

                if self.error_count >= self.max_errors:
                    logger.critical(
                        f"Max errors reached for config {self.config_id}, stopping listener"
                    )
                    break

                # Exponential backoff on errors
                wait_time = min(60 * (2 ** self.error_count), 3600)  # Max 1 hour
                self.stop_event.wait(wait_time)

        logger.info(f"Stopped email listener for config {self.config_id}")

    def stop(self) -> None:
        """Signal thread to stop"""
        logger.info(f"Stopping listener for config {self.config_id}")
        self.stop_event.set()

    def _apply_filter_rules(self, emails: list[EmailMessage]) -> list[EmailMessage]:
        """Apply filter rules to emails"""
        if not self.filter_rules or len(self.filter_rules) == 0:
            logger.debug(f"No filter rules set for config {self.config_id} - processing all emails")
            return emails

        filtered_emails = []
        logger.debug(
            f"Applying {len(self.filter_rules)} filter rules to {len(emails)} emails"
        )

        for email in emails:
            email_passes = False

            for rule in self.filter_rules:
                try:
                    if self._check_filter_rule(email, rule):
                        email_passes = True
                        logger.debug(
                            f"Email {email.message_id[:20]}... passed filter: "
                            f"{rule.field} {rule.operation} '{rule.value}'"
                        )
                        break
                except Exception as e:
                    logger.warning(
                        f"Error applying filter rule {rule.field} {rule.operation} "
                        f"'{rule.value}': {e}"
                    )
                    continue

            if email_passes:
                filtered_emails.append(email)
                logger.debug(
                    f"Email {email.message_id[:20]}... from {email.sender_email} passed filters"
                )
            else:
                logger.debug(
                    f"Email {email.message_id[:20]}... from {email.sender_email} filtered out"
                )

        logger.info(
            f"After filters: {len(filtered_emails)}/{len(emails)} emails passed "
            f"(filtered out {len(emails) - len(filtered_emails)})"
        )

        return filtered_emails

    def _check_filter_rule(self, email: EmailMessage, rule: FilterRule) -> bool:
        """
        Check if an email passes a single filter rule.
        Different field types require different operation handling.
        """
        # String field operations (sender_email, subject)
        if rule.field in ['sender_email', 'subject']:
            field_value = email.sender_email if rule.field == 'sender_email' else email.subject

            if rule.operation == 'equals':
                if rule.case_sensitive:
                    return field_value == rule.value
                else:
                    return field_value.lower() == rule.value.lower()

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
            else:
                logger.warning(
                    f"Invalid operation '{rule.operation}' for string field '{rule.field}'"
                )
                return True  # Unknown operations pass by default

        # Boolean field operations (has_attachments)
        elif rule.field == 'has_attachments':
            field_value = email.has_attachments

            if rule.operation in ['equals', 'is']:
                # Convert string value to boolean
                # Accept: "true", "True", "1", "yes" as True
                # Accept: "false", "False", "0", "no" as False
                rule_bool = rule.value.lower() in ['true', '1', 'yes']
                return field_value == rule_bool
            else:
                logger.warning(
                    f"Invalid operation '{rule.operation}' for boolean field '{rule.field}'. "
                    f"Only 'equals' or 'is' are supported."
                )
                return True  # Unknown operations pass by default

        # DateTime field operations (received_date)
        elif rule.field == 'received_date':
            field_value = email.received_date

            try:
                # Parse the rule value as ISO datetime
                compare_date = datetime.fromisoformat(rule.value.replace('Z', '+00:00'))

                if rule.operation == 'before':
                    return field_value < compare_date
                elif rule.operation == 'after':
                    return field_value > compare_date
                elif rule.operation == 'equals':
                    # For datetime equality, compare just the date portion
                    return field_value.date() == compare_date.date()
                else:
                    logger.warning(
                        f"Invalid operation '{rule.operation}' for datetime field '{rule.field}'. "
                        f"Only 'before', 'after', or 'equals' are supported."
                    )
                    return True  # Unknown operations pass by default

            except Exception as e:
                logger.error(
                    f"Error parsing datetime value '{rule.value}' for rule: {e}. "
                    f"Passing email by default."
                )
                return True  # Parsing errors pass by default

        # Unknown field
        else:
            logger.warning(f"Unknown filter field: '{rule.field}'. Passing email by default.")
            return True  # Unknown fields pass by default

    def _check_and_process_emails(self) -> None:
        """Check for new emails and process them"""
        try:
            # Calculate time window for retrieval
            since_time = self.last_check_time

            # Add small overlap to avoid missing emails, but NOT for freshly activated configs
            if since_time:
                # Check if this is a fresh activation
                time_diff = abs((since_time - self.activation_time).total_seconds())
                if time_diff > 1:  # If more than 1 second difference, not a fresh activation
                    since_time = since_time - timedelta(seconds=30)
                    logger.debug(f"Config {self.config_id}: Applied 30s overlap (ongoing operation)")
                else:
                    logger.info(
                        f"Config {self.config_id}: Fresh activation detected, "
                        f"starting without overlap"
                    )

            logger.debug(f"Checking emails since {since_time} for config {self.config_id}")

            # Get recent emails from the integration
            emails = self.integration.get_recent_emails(
                since_datetime=since_time,
                limit=100,
                include_read=True  # Process all emails, let service handle duplicates
            )

            logger.info(f"Found {len(emails)} emails for config {self.config_id}")

            # Apply filter rules
            filtered_emails = self._apply_filter_rules(emails)

            # Process each filtered email
            for email_msg in filtered_emails:
                try:
                    email_start_time = time.time()
                    logger.info(
                        f"Starting to process email {email_msg.message_id[:20]}... "
                        f"from {email_msg.sender_email}"
                    )

                    # Use cached attachments for better performance
                    attachments = email_msg.cached_attachments
                    logger.info(f"Using {len(attachments)} pre-cached attachments")

                    # Call back to service for processing
                    callback_start_time = time.time()
                    logger.info(f"Starting email processing callback for {email_msg.message_id[:20]}...")

                    self.process_callback(self.config_id, email_msg, attachments)

                    callback_duration = time.time() - callback_start_time
                    total_duration = time.time() - email_start_time
                    logger.info(
                        f"Completed email {email_msg.message_id[:20]}... processing: "
                        f"callback={callback_duration:.2f}s, total={total_duration:.2f}s"
                    )

                    # Update last check time to email's received date if newer
                    if email_msg.received_date > self.last_check_time:
                        self.last_check_time = email_msg.received_date

                except Exception as e:
                    logger.error(
                        f"Error processing email {email_msg.message_id}: {e}",
                        exc_info=True
                    )
                    # Call error callback for processing errors
                    try:
                        self.error_callback(self.config_id, e)
                    except Exception as callback_error:
                        logger.error(f"Error in error callback: {callback_error}")
                    continue

            # Update last check time to now
            self.last_check_time = datetime.now(timezone.utc)

            # Notify service to update database
            try:
                self.check_complete_callback(self.config_id, self.last_check_time)
            except Exception as callback_error:
                logger.error(f"Error in check complete callback: {callback_error}")

        except Exception as e:
            logger.error(f"Error checking emails for config {self.config_id}: {e}", exc_info=True)
            raise

    def get_status(self) -> dict[str, Any]:
        """Get current status of the listener"""
        return {
            "config_id": self.config_id,
            "is_alive": self.is_alive(),
            "error_count": self.error_count,
            "last_check_time": self.last_check_time.isoformat() if self.last_check_time else None,
            "poll_interval": self.poll_interval
        }
