"""
ETO Worker
Background async worker for processing ETO runs
"""
import asyncio
import logging
from typing import Callable, Optional, List, Set, Dict, Any

from shared.types.eto_sub_runs import EtoSubRun

logger = logging.getLogger(__name__)


class EtoWorker:
    """
    Background worker for processing ETO runs.

    Runs async polling loop and delegates stage processing via callbacks.
    Similar to EmailListenerThread pattern but using asyncio instead of threading.

    Features:
    - Async polling loop
    - Concurrent batch processing
    - Pause/resume capability
    - Graceful shutdown
    - Stuck run cleanup
    """

    def __init__(
        self,
        process_run_callback: Callable[[int], bool],
        get_pending_runs_callback: Callable[[int], List[EtoSubRun]],
        reset_run_callback: Callable[[int], None],
        enabled: bool = True,
        max_concurrent_runs: int = 10,
        polling_interval: int = 2,
        shutdown_timeout: int = 30
    ):
        """
        Initialize ETO Worker.

        Args:
            process_run_callback: Callback to process a single run (service.process_run)
            get_pending_runs_callback: Callback to get pending runs (service.list_runs)
            reset_run_callback: Callback to reset a run (service._reset_run_to_not_started)
            enabled: Whether worker is enabled
            max_concurrent_runs: Maximum concurrent runs to process
            polling_interval: Seconds between polling cycles
            shutdown_timeout: Seconds to wait for graceful shutdown
        """
        # Configuration
        self.enabled = enabled
        self.max_concurrent_runs = max_concurrent_runs
        self.polling_interval = polling_interval
        self.shutdown_timeout = shutdown_timeout

        # Callbacks to service
        self.process_run_callback = process_run_callback
        self.get_pending_runs_callback = get_pending_runs_callback
        self.reset_run_callback = reset_run_callback

        # State
        self.running = False
        self.paused = False
        self.worker_task: Optional[asyncio.Task] = None
        self.currently_processing: Set[int] = set()

        logger.debug(
            f"EtoWorker initialized - enabled: {enabled}, "
            f"max_concurrent: {max_concurrent_runs}, polling_interval: {polling_interval}s"
        )

    async def startup(self) -> bool:
        """
        Start the background processing worker.

        Returns:
            True if worker started, False if disabled or already running
        """
        if not self.enabled:
            logger.info("ETO worker is disabled by configuration")
            return False

        if self.running:
            logger.warning("ETO worker is already running")
            return False

        self.running = True
        self.paused = False
        self.worker_task = asyncio.create_task(self._continuous_processing_loop())
        logger.info("ETO background worker started")
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
            logger.warning("ETO worker is not running")
            return False

        logger.info(f"Stopping ETO worker (graceful={graceful})...")
        self.running = False

        if graceful and self.worker_task:
            # Give current batch time to finish
            try:
                await asyncio.wait_for(self.worker_task, timeout=self.shutdown_timeout)
                logger.info("ETO worker stopped gracefully - current batch completed")
            except asyncio.TimeoutError:
                logger.warning(
                    f"ETO worker shutdown timeout after {self.shutdown_timeout}s - forcing stop"
                )
                self.worker_task.cancel()
                try:
                    await self.worker_task
                except asyncio.CancelledError:
                    pass
        elif self.worker_task:
            # Force immediate stop
            self.worker_task.cancel()
            try:
                await self.worker_task
            except asyncio.CancelledError:
                pass
            logger.info("ETO worker stopped immediately")

        # Reset any runs stuck in processing
        await self._reset_stuck_runs()
        self.worker_task = None
        return True

    def pause(self) -> bool:
        """
        Pause the worker (emergency stop without shutting down).

        Returns:
            True if paused successfully
        """
        if not self.running:
            logger.warning("Cannot pause - ETO worker is not running")
            return False

        self.paused = True
        logger.warning("ETO background worker PAUSED - processing stopped")
        return True

    def resume(self) -> bool:
        """
        Resume the worker from paused state.

        Returns:
            True if resumed successfully
        """
        if not self.running:
            logger.warning("Cannot resume - ETO worker is not running")
            return False

        self.paused = False
        logger.info("ETO background worker RESUMED - processing restarted")
        return True

    def get_status(self) -> Dict[str, Any]:
        """
        Get current worker status and metrics.

        Returns:
            Dictionary with worker state and statistics
        """
        # Get pending count from service
        pending_count = 0
        try:
            pending_runs = self.get_pending_runs_callback(100)  # Limit to 100 for count
            pending_count = len(pending_runs)
        except Exception as e:
            logger.error(f"Error getting pending count: {e}")

        return {
            "worker_enabled": self.enabled,
            "worker_running": self.running,
            "worker_paused": self.paused,
            "max_concurrent_runs": self.max_concurrent_runs,
            "polling_interval": self.polling_interval,
            "pending_runs_count": pending_count,
            "currently_processing_count": len(self.currently_processing),
            "worker_task_active": self.worker_task is not None and not self.worker_task.done()
        }

    # ==================== Worker Polling Loop ====================

    async def _continuous_processing_loop(self):
        """
        Main continuous processing loop - runs until stopped.
        Polls for pending runs every polling_interval seconds.
        """
        logger.info("ETO continuous processing loop started")

        while self.running:
            try:
                if self.paused:
                    # Worker is paused - don't process anything
                    await asyncio.sleep(self.polling_interval)
                    continue

                # Find and process pending runs
                await self._process_pending_runs_batch()

                # Wait before next cycle
                await asyncio.sleep(self.polling_interval)

            except asyncio.CancelledError:
                logger.info("ETO processing loop cancelled")
                break
            except Exception as e:
                logger.error(f"Error in ETO processing loop: {e}", exc_info=True)
                # Wait longer on error to avoid tight error loops
                await asyncio.sleep(self.polling_interval * 2)

        logger.info("ETO continuous processing loop stopped")

    async def _process_pending_runs_batch(self):
        """
        Process a batch of pending runs concurrently.
        Fetches up to max_concurrent_runs and processes them in parallel.
        """
        try:
            # Get pending runs from service
            pending_runs = self.get_pending_runs_callback(self.max_concurrent_runs)

            if not pending_runs:
                return  # No work to do

            logger.info(f"Processing batch of {len(pending_runs)} ETO sub-runs concurrently")

            # Process all runs concurrently
            tasks = [
                self._process_run_async(run.id)
                for run in pending_runs
            ]

            # Wait for all to complete
            results = await asyncio.gather(*tasks, return_exceptions=True)

            # Log batch results
            successful = sum(1 for r in results if not isinstance(r, Exception) and r is True)
            failed = len(results) - successful

            if failed > 0:
                logger.warning(f"Batch completed: {successful} successful, {failed} failed")
                # Log specific failures
                for i, result in enumerate(results):
                    if isinstance(result, Exception):
                        logger.error(f"Run {pending_runs[i].id} failed: {result}")
            else:
                logger.info(f"Batch completed successfully: {successful} sub-runs processed")

        except Exception as e:
            logger.error(f"Error processing pending runs batch: {e}", exc_info=True)

    async def _process_run_async(self, run_id: int) -> bool:
        """
        Async wrapper for processing a single run.
        Runs the synchronous process_run() callback in thread pool.

        Args:
            run_id: ETO run ID to process

        Returns:
            True if successful, False if failed
        """
        self.currently_processing.add(run_id)
        try:
            logger.debug(f"Starting async processing for ETO run {run_id}")

            # Run synchronous processing callback in thread pool
            loop = asyncio.get_event_loop()
            success = await loop.run_in_executor(
                None,
                self.process_run_callback,
                run_id
            )

            logger.debug(f"Completed async processing for ETO run {run_id}: success={success}")
            return success

        except Exception as e:
            logger.error(f"Error in async processing for ETO run {run_id}: {e}", exc_info=True)
            return False
        finally:
            self.currently_processing.discard(run_id)

    async def _reset_stuck_runs(self):
        """
        Reset any runs stuck in 'processing' status back to 'not_started'.
        Called during worker shutdown to clean up orphaned runs.
        """
        try:
            # Get processing runs via callback (would need to be added to service)
            # For now, just log - this functionality can be added later
            logger.info("Worker shutdown - stuck run cleanup would happen here")
            # TODO: Add get_processing_runs_callback to service and call reset_run_callback for each
        except Exception as e:
            logger.error(f"Error resetting stuck runs: {e}")
