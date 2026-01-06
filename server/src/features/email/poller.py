"""
Email Poller Worker

Background worker that polls a single email ingestion config for new emails.
Applies two-stage filtering:
1. Filter rules (user-defined filters like sender, subject, etc.)
2. Deduplication (skip emails already processed for this account)
"""
import logging
import threading
from typing import TYPE_CHECKING, Callable

from shared.database.repositories.email import EmailRepository
from shared.types.email_ingestion_configs import EmailIngestionConfig
from shared.exceptions import PermanentEmailError, TransientEmailError
from shared.types.email_integrations import EmailMessage
from features.email.utils.filter_rules import apply_filter_rules
from features.email.utils.deduplication import filter_duplicate_emails

if TYPE_CHECKING:
    from features.email.service import EmailService

logger = logging.getLogger(__name__)


class PollerWorker:
    """
    Background worker that polls a single ingestion config for new emails.

    Each PollerWorker runs in its own thread and polls at the interval
    specified in the config. Uses the service's get_emails_since_uid()
    method which routes to the appropriate integration.

    Error Handling:
    - Permanent errors (e.g., folder doesn't exist): Deactivate immediately
    - Transient errors (e.g., connection issues): Retry up to MAX_CONSECUTIVE_ERRORS
      times before deactivating
    """

    # Number of consecutive transient errors before auto-deactivating
    MAX_CONSECUTIVE_ERRORS = 3

    def __init__(
        self,
        config: EmailIngestionConfig,
        service: "EmailService",
        email_repository: EmailRepository,
        on_emails_received: Callable[[EmailIngestionConfig, list[EmailMessage]], None] | None = None,
    ):
        """
        Initialize poller worker.

        Args:
            config: Ingestion config to poll
            service: Email service instance (for get_emails_since_uid)
            email_repository: Repository for deduplication checks
            on_emails_received: Callback when emails are received (optional)
        """
        self.config = config
        self.service = service
        self.email_repository = email_repository
        self.on_emails_received = on_emails_received

        self._running = False
        self._thread: threading.Thread | None = None
        self._stop_event = threading.Event()

        # Track last processed UID (start from config's stored value)
        self._last_processed_uid = config.last_processed_uid or 0

        # Track consecutive errors for auto-deactivation
        self._consecutive_errors = 0

        self.logger = logging.getLogger(f"{__name__}.Poller-{config.id}")

    @property
    def is_running(self) -> bool:
        """Check if poller is currently running."""
        return self._running and self._thread is not None and self._thread.is_alive()

    def start(self) -> None:
        """Start the polling thread."""
        if self._running:
            self.logger.warning(f"Poller for config {self.config.id} is already running")
            return

        self.logger.info(
            f"Starting poller for config {self.config.id} "
            f"(folder={self.config.folder_name}, interval={self.config.poll_interval_seconds}s)"
        )

        self._running = True
        self._stop_event.clear()

        self._thread = threading.Thread(
            target=self._poll_loop,
            daemon=True,
            name=f"email-poller-{self.config.id}",
        )
        self._thread.start()

    def stop(self, timeout: float = 10.0) -> None:
        """
        Stop the polling thread.

        Args:
            timeout: Max seconds to wait for thread to stop
        """
        if not self._running:
            return

        self.logger.info(f"Stopping poller for config {self.config.id}")

        self._running = False
        self._stop_event.set()

        if self._thread is not None:
            self._thread.join(timeout=timeout)
            if self._thread.is_alive():
                self.logger.warning(f"Poller thread for config {self.config.id} did not stop cleanly")
            self._thread = None

        self.logger.info(f"Poller for config {self.config.id} stopped")

    def _poll_loop(self) -> None:
        """Main polling loop - runs in background thread."""
        self.logger.info(f"[POLLER {self.config.id}] Poll loop STARTED for folder '{self.config.folder_name}'")

        poll_count = 0
        while self._running:
            poll_count += 1
            try:
                self._poll_once(poll_count)
                # Reset error count on successful poll
                self._consecutive_errors = 0

            except PermanentEmailError as e:
                # Permanent error - deactivate immediately
                self.logger.error(
                    f"[POLLER {self.config.id}] Poll #{poll_count} PERMANENT ERROR: {e}"
                )
                self._deactivate_with_error(str(e))
                break

            except TransientEmailError as e:
                # Transient error (connection issues) - do NOT count toward deactivation
                # The connection has been cleared and will reconnect on next attempt
                self.logger.warning(
                    f"[POLLER {self.config.id}] Poll #{poll_count} TRANSIENT ERROR (will retry): {e}"
                )
                # Don't increment _consecutive_errors - just log and continue
                # The connection will be re-established on the next poll cycle

            except Exception as e:
                # Unexpected error - treat as transient
                self._consecutive_errors += 1
                self.logger.error(
                    f"[POLLER {self.config.id}] Poll #{poll_count} UNEXPECTED ERROR "
                    f"({self._consecutive_errors}/{self.MAX_CONSECUTIVE_ERRORS}): {e}",
                    exc_info=True
                )

                if self._consecutive_errors >= self.MAX_CONSECUTIVE_ERRORS:
                    self._deactivate_with_error(
                        f"Too many consecutive errors ({self.MAX_CONSECUTIVE_ERRORS}): {e}"
                    )
                    break
                else:
                    self._record_error(str(e))

            # Sleep for poll interval, but check stop event frequently
            # This allows faster shutdown
            if self._running:
                self.logger.debug(
                    f"[POLLER {self.config.id}] Sleeping {self.config.poll_interval_seconds}s until next poll..."
                )
            for _ in range(self.config.poll_interval_seconds):
                if self._stop_event.wait(timeout=1.0):
                    break

        self.logger.info(f"[POLLER {self.config.id}] Poll loop ENDED after {poll_count} poll(s)")

    def _poll_once(self, poll_number: int = 0) -> None:
        """Execute a single poll cycle."""
        self.logger.info(
            f"[POLLER {self.config.id}] Poll #{poll_number} - "
            f"Checking folder '{self.config.folder_name}' (since UID {self._last_processed_uid})"
        )

        # Fetch new emails via service (protocol-agnostic)
        emails = self.service.get_emails_since_uid(
            config=self.config,
            since_uid=self._last_processed_uid,
        )

        if emails:
            self.logger.info(
                f"[POLLER {self.config.id}] Poll #{poll_number} - "
                f"FOUND {len(emails)} new email(s) (UIDs {emails[0].uid}-{emails[-1].uid})"
            )

            # Log email subjects for visibility
            for email in emails[:5]:  # Show first 5
                self.logger.info(
                    f"[POLLER {self.config.id}]   - UID {email.uid}: {email.subject[:50]}..."
                    if len(email.subject) > 50 else
                    f"[POLLER {self.config.id}]   - UID {email.uid}: {email.subject}"
                )
            if len(emails) > 5:
                self.logger.info(f"[POLLER {self.config.id}]   ... and {len(emails) - 5} more")

            # Stage 1: Apply filter rules
            # This avoids downloading attachments for emails that don't match filters
            filtered_emails = apply_filter_rules(
                emails=emails,
                filter_rules=self.config.filter_rules,
                config_id=self.config.id,
            )

            # Stage 2: Deduplication
            # Skip emails already processed for this account (handles folder moves)
            if filtered_emails:
                # Fetch existing message IDs for this account
                message_ids = [e.message_id for e in filtered_emails if e.message_id]
                existing_ids = self.email_repository.get_existing_message_ids(
                    self.config.account_id, message_ids
                )
                new_emails = filter_duplicate_emails(
                    emails=filtered_emails,
                    existing_message_ids=existing_ids,
                    context=f"config {self.config.id}",
                )
            else:
                new_emails = []

            # Call callback only with new (non-duplicate) emails
            if new_emails and self.on_emails_received:
                try:
                    self.on_emails_received(self.config, new_emails)
                except Exception as e:
                    self.logger.error(f"[POLLER {self.config.id}] Error in on_emails_received callback: {e}")

            # Always update UID based on ALL fetched emails (not just filtered)
            # This ensures we don't re-fetch filtered-out emails next poll
            highest_uid = max(email.uid for email in emails)
            self._last_processed_uid = highest_uid

            # Persist the UID update
            self._update_last_processed_uid(highest_uid)
            self.logger.info(f"[POLLER {self.config.id}] Updated last_processed_uid to {highest_uid}")

        else:
            self.logger.info(f"[POLLER {self.config.id}] Poll #{poll_number} - No new emails")

        # Update last check time
        self._update_last_check_time()

    def _update_last_processed_uid(self, uid: int) -> None:
        """Persist the last processed UID to database."""
        try:
            self.service.update_config_uid(self.config.id, uid)
        except Exception as e:
            self.logger.error(f"Failed to update last_processed_uid: {e}")

    def _update_last_check_time(self) -> None:
        """Persist the last check time to database."""
        try:
            self.service.update_config_last_check(self.config.id)
        except Exception as e:
            self.logger.error(f"Failed to update last_check_time: {e}")

    def _record_error(self, error_message: str) -> None:
        """Record poll error in database."""
        try:
            self.service.record_config_error(self.config.id, error_message)
        except Exception as e:
            self.logger.error(f"Failed to record error: {e}")

    def _deactivate_with_error(self, error_message: str) -> None:
        """
        Record error and request deactivation from service.

        Called when we encounter a permanent error or exceed the retry limit
        for transient errors.
        """
        self.logger.error(
            f"[POLLER {self.config.id}] AUTO-DEACTIVATING due to: {error_message}"
        )

        try:
            self.service.deactivate_config_with_error(self.config.id, error_message)
        except Exception as e:
            self.logger.error(f"Failed to deactivate config: {e}")

        # Stop the poll loop
        self._running = False
        self._stop_event.set()
