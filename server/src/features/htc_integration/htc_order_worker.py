"""
HTC Order Worker
Background async worker for creating HTC orders from ready pending orders
"""
import asyncio
import logging
from datetime import datetime, timezone
from typing import Callable, Optional, List, Set, TYPE_CHECKING

if TYPE_CHECKING:
    from shared.types.pending_orders import PendingOrder

logger = logging.getLogger(__name__)


class HtcOrderWorker:
    """
    Background worker for creating HTC orders from pending orders.

    Monitors pending orders with status='ready' and attempts to create
    them in HTC. Handles success/failure status updates.

    Status flow:
    - ready -> processing (picked up by worker)
    - processing -> created (HTC order created successfully)
    - processing -> failed (HTC creation failed, stores error message)

    Features:
    - Async polling loop
    - Concurrent batch processing
    - Pause/resume capability
    - Graceful shutdown
    - Error tracking with messages
    """

    def __init__(
        self,
        # Callbacks
        get_ready_pending_orders_callback: Callable[[int], List['PendingOrder']],
        create_htc_order_callback: Callable[[int], float],
        mark_processing_callback: Callable[[int], None],
        mark_created_callback: Callable[[int, float], None],
        mark_failed_callback: Callable[[int, str], None],
        # Configuration
        enabled: bool = True,
        max_concurrent: int = 5,
        polling_interval: int = 5,
        shutdown_timeout: int = 30
    ):
        """
        Initialize HTC Order Worker.

        Args:
            get_ready_pending_orders_callback: Gets pending orders with status='ready'
            create_htc_order_callback: Creates HTC order, returns order number
            mark_processing_callback: Sets status to 'processing'
            mark_created_callback: Sets status to 'created' with order number
            mark_failed_callback: Sets status to 'failed' with error message
            enabled: Whether worker is enabled
            max_concurrent: Maximum concurrent orders to process
            polling_interval: Seconds between polling cycles
            shutdown_timeout: Seconds to wait for graceful shutdown
        """
        # Configuration
        self.enabled = enabled
        self.max_concurrent = max_concurrent
        self.polling_interval = polling_interval
        self.shutdown_timeout = shutdown_timeout

        # Callbacks
        self.get_ready_pending_orders_callback = get_ready_pending_orders_callback
        self.create_htc_order_callback = create_htc_order_callback
        self.mark_processing_callback = mark_processing_callback
        self.mark_created_callback = mark_created_callback
        self.mark_failed_callback = mark_failed_callback

        # State
        self.running = False
        self.paused = False
        self.worker_task: Optional[asyncio.Task] = None
        self.currently_processing: Set[int] = set()

        logger.debug(
            f"HtcOrderWorker initialized - enabled: {enabled}, "
            f"max_concurrent: {max_concurrent}, polling_interval: {polling_interval}s"
        )

    async def startup(self) -> bool:
        """
        Start the background processing worker.

        Returns:
            True if worker started, False if disabled or already running
        """
        if not self.enabled:
            logger.info("HTC order worker is disabled by configuration")
            return False

        if self.running:
            logger.warning("HTC order worker is already running")
            return False

        self.running = True
        self.paused = False
        self.worker_task = asyncio.create_task(self._processing_loop())
        logger.info("HTC order background worker started")
        return True

    async def shutdown(self, graceful: bool = True) -> bool:
        """
        Stop the background processing worker.

        Args:
            graceful: If True, wait for current batch to complete

        Returns:
            True if stopped successfully
        """
        if not self.running:
            logger.warning("HTC order worker is not running")
            return False

        logger.info(f"Stopping HTC order worker (graceful={graceful})...")
        self.running = False

        if graceful and self.worker_task:
            try:
                await asyncio.wait_for(self.worker_task, timeout=self.shutdown_timeout)
                logger.info("HTC order worker stopped gracefully - current batch completed")
            except asyncio.TimeoutError:
                logger.warning(
                    f"HTC order worker shutdown timeout after {self.shutdown_timeout}s - forcing stop"
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

        self.worker_task = None
        logger.info("HTC order worker stopped")
        return True

    def pause(self) -> bool:
        """Pause the worker (stops picking up new orders)."""
        if not self.running:
            return False
        self.paused = True
        logger.info("HTC order worker paused")
        return True

    def resume(self) -> bool:
        """Resume the worker after pause."""
        if not self.running:
            return False
        self.paused = False
        logger.info("HTC order worker resumed")
        return True

    async def _processing_loop(self) -> None:
        """Main processing loop - polls for ready orders and processes them."""
        logger.info("HTC order processing loop started")

        while self.running:
            try:
                if not self.paused:
                    await self._process_batch()

                # Wait before next poll
                await asyncio.sleep(self.polling_interval)

            except asyncio.CancelledError:
                logger.info("HTC order processing loop cancelled")
                break
            except Exception as e:
                logger.error(f"Error in HTC order processing loop: {e}", exc_info=True)
                # Continue running after errors
                await asyncio.sleep(self.polling_interval)

        logger.info("HTC order processing loop stopped")

    async def _process_batch(self) -> None:
        """Process a batch of ready pending orders."""
        # Calculate how many we can process
        available_slots = self.max_concurrent - len(self.currently_processing)
        if available_slots <= 0:
            return

        # Get ready pending orders
        try:
            ready_orders = await asyncio.get_event_loop().run_in_executor(
                None,
                self.get_ready_pending_orders_callback,
                available_slots
            )
        except Exception as e:
            logger.error(f"Error getting ready pending orders: {e}")
            return

        if not ready_orders:
            return

        logger.info(f"Found {len(ready_orders)} ready pending orders to process")

        # Process each order
        tasks = []
        for order in ready_orders:
            # Skip if already being processed
            if order.id in self.currently_processing:
                continue

            self.currently_processing.add(order.id)
            task = asyncio.create_task(self._process_order(order.id))
            tasks.append(task)

        # Wait for all tasks to complete
        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)

    async def _process_order(self, pending_order_id: int) -> None:
        """
        Process a single pending order - create HTC order.

        Args:
            pending_order_id: ID of the pending order to process
        """
        try:
            logger.info(f"Processing pending order {pending_order_id}")

            # Mark as processing
            await asyncio.get_event_loop().run_in_executor(
                None,
                self.mark_processing_callback,
                pending_order_id
            )

            # Create HTC order
            htc_order_number = await asyncio.get_event_loop().run_in_executor(
                None,
                self.create_htc_order_callback,
                pending_order_id
            )

            # Mark as created
            await asyncio.get_event_loop().run_in_executor(
                None,
                self.mark_created_callback,
                pending_order_id,
                htc_order_number
            )

            logger.info(
                f"Pending order {pending_order_id} created in HTC as order {htc_order_number}"
            )

        except Exception as e:
            error_message = str(e)
            logger.error(
                f"Failed to create HTC order for pending order {pending_order_id}: {error_message}"
            )

            # Mark as failed with error message
            try:
                await asyncio.get_event_loop().run_in_executor(
                    None,
                    self.mark_failed_callback,
                    pending_order_id,
                    error_message
                )
            except Exception as mark_error:
                logger.error(
                    f"Failed to mark pending order {pending_order_id} as failed: {mark_error}"
                )

        finally:
            self.currently_processing.discard(pending_order_id)

    def get_status(self) -> dict:
        """Get current worker status."""
        return {
            "enabled": self.enabled,
            "running": self.running,
            "paused": self.paused,
            "currently_processing": list(self.currently_processing),
            "processing_count": len(self.currently_processing),
            "max_concurrent": self.max_concurrent,
            "polling_interval": self.polling_interval,
        }
