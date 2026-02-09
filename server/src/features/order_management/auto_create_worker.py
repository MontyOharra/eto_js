"""
Auto-Create Worker

Background async worker that automatically approves create-type pending actions
in "ready" status when the auto_create_enabled setting is active.

Follows the EtoWorker async pattern: asyncio.create_task polling loop with
graceful shutdown, integrated into app lifecycle through OrderManagementService.
"""
import asyncio
import logging
from collections.abc import Callable
from datetime import datetime
from typing import Any

from shared.types.pending_actions import PendingAction, ExecuteResult

logger = logging.getLogger(__name__)


class AutoCreateWorker:
    """
    Background worker that auto-approves ready create actions.

    Checks the auto_create_enabled setting each cycle. When enabled, queries
    for eligible actions (creates in "ready" status created after the setting
    was enabled) and approves them sequentially.

    Sequential processing is required because the HTC Access DB doesn't
    handle concurrent writes.
    """

    def __init__(
        self,
        get_eligible_actions: Callable[[datetime], list[PendingAction]],
        approve_action: Callable[[int, datetime | None, str | None], ExecuteResult],
        get_auto_create_settings: Callable[[], tuple[bool, datetime | None]],
        polling_interval: int = 10,
        shutdown_timeout: int = 30,
    ):
        """
        Initialize with callback dependencies.

        Args:
            get_eligible_actions: Returns ready create actions after given timestamp
            approve_action: Approves a single action (action_id, detail_viewed_at, approver_user_id)
            get_auto_create_settings: Returns (enabled, enabled_at) tuple
            polling_interval: Seconds between polling cycles when idle
            shutdown_timeout: Seconds to wait for graceful shutdown
        """
        self.get_eligible_actions = get_eligible_actions
        self.approve_action = approve_action
        self.get_auto_create_settings = get_auto_create_settings
        self.polling_interval = polling_interval
        self.shutdown_timeout = shutdown_timeout

        # State
        self.running = False
        self.processing = False
        self.worker_task: asyncio.Task[None] | None = None

        # Stats
        self.total_approved = 0
        self.total_failed = 0
        self.total_skipped = 0

        logger.debug(
            f"AutoCreateWorker initialized - polling_interval: {polling_interval}s"
        )

    async def startup(self) -> bool:
        """
        Start the background processing worker.

        Returns:
            True if worker started, False if already running
        """
        if self.running:
            logger.warning("Auto-create worker is already running")
            return False

        self.running = True
        self.worker_task = asyncio.create_task(self._polling_loop())
        logger.info("Auto-create background worker started")
        return True

    async def shutdown(self, graceful: bool = True) -> bool:
        """
        Stop the background processing worker.

        Args:
            graceful: If True, wait for current action to complete

        Returns:
            True if stopped successfully
        """
        if not self.running:
            logger.warning("Auto-create worker is not running")
            return False

        logger.info(f"Stopping auto-create worker (graceful={graceful})...")
        self.running = False

        if graceful and self.worker_task:
            try:
                await asyncio.wait_for(self.worker_task, timeout=self.shutdown_timeout)
                logger.info("Auto-create worker stopped gracefully")
            except asyncio.TimeoutError:
                logger.warning(
                    f"Auto-create worker shutdown timeout after {self.shutdown_timeout}s - forcing stop"
                )
                self.worker_task.cancel()
                try:
                    await self.worker_task
                except asyncio.CancelledError:
                    pass
        elif self.worker_task:
            self.worker_task.cancel()
            try:
                await self.worker_task
            except asyncio.CancelledError:
                pass
            logger.info("Auto-create worker stopped immediately")

        self.worker_task = None
        return True

    def get_status(self) -> dict[str, Any]:
        """Get current worker status and statistics."""
        return {
            "worker_running": self.running,
            "worker_processing": self.processing,
            "polling_interval": self.polling_interval,
            "total_approved": self.total_approved,
            "total_failed": self.total_failed,
            "total_skipped": self.total_skipped,
            "worker_task_active": self.worker_task is not None and not self.worker_task.done(),
        }

    # ==================== Polling Loop ====================

    async def _polling_loop(self):
        """
        Main polling loop - runs until stopped.

        Each cycle:
        1. Read auto_create settings
        2. If disabled or no enabled_at, sleep and continue
        3. Query eligible actions (ready creates after enabled_at)
        4. Approve each sequentially (HTC can't handle concurrent writes)
        5. Sleep shorter if items were processed, full interval otherwise
        """
        logger.info("Auto-create polling loop started")

        while self.running:
            try:
                items_processed = await self._process_cycle()

                # Sleep shorter if we processed items (more may be waiting)
                sleep_time = 2 if items_processed > 0 else self.polling_interval
                await asyncio.sleep(sleep_time)

            except asyncio.CancelledError:
                logger.info("Auto-create polling loop cancelled")
                break
            except Exception as e:
                logger.error(f"Error in auto-create polling loop: {e}", exc_info=True)
                await asyncio.sleep(self.polling_interval * 2)

        logger.info("Auto-create polling loop stopped")

    async def _process_cycle(self) -> int:
        """
        Run one polling cycle.

        Returns:
            Number of actions processed this cycle
        """
        loop = asyncio.get_event_loop()

        # 1. Check settings
        try:
            enabled, enabled_at = await loop.run_in_executor(
                None, self.get_auto_create_settings
            )
        except Exception as e:
            logger.error(f"Failed to read auto-create settings: {e}")
            return 0

        if not enabled or enabled_at is None:
            return 0

        # 2. Get eligible actions
        try:
            actions = await loop.run_in_executor(
                None, self.get_eligible_actions, enabled_at
            )
        except Exception as e:
            logger.error(f"Failed to get eligible auto-create actions: {e}")
            return 0

        if not actions:
            return 0

        logger.info(f"Auto-create: found {len(actions)} eligible action(s)")

        # 3. Process sequentially
        self.processing = True
        processed = 0
        try:
            for action in actions:
                if not self.running:
                    logger.info("Auto-create: shutdown requested, stopping mid-batch")
                    break

                try:
                    result: ExecuteResult = await loop.run_in_executor(
                        None,
                        self.approve_action,
                        action.id,
                        None,  # detail_viewed_at - not needed for creates
                        "system:auto-create",  # approver_user_id
                    )

                    if result.success:
                        self.total_approved += 1
                        logger.info(
                            f"Auto-create: approved action {action.id} "
                            f"(customer={action.customer_id}, hawb='{action.hawb}')"
                        )
                    elif result.requires_review:
                        self.total_skipped += 1
                        logger.warning(
                            f"Auto-create: action {action.id} requires review "
                            f"({result.review_reason}) - skipping for manual handling"
                        )
                    else:
                        self.total_failed += 1
                        logger.error(
                            f"Auto-create: action {action.id} failed: {result.error_message}"
                        )

                    processed += 1

                except Exception as e:
                    self.total_failed += 1
                    logger.error(
                        f"Auto-create: exception approving action {action.id}: {e}",
                        exc_info=True,
                    )
                    processed += 1
        finally:
            self.processing = False

        if processed > 0:
            logger.info(
                f"Auto-create cycle complete: {processed} processed "
                f"(approved={self.total_approved}, failed={self.total_failed}, "
                f"skipped={self.total_skipped} total)"
            )

        return processed
