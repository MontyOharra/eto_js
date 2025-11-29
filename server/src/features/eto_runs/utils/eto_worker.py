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
    Background worker for processing ETO runs with two-phase processing.

    Phase 1 (Template Matching):
    - Picks up sub-runs with status="not_started" AND no template
    - Runs template matching to identify which pages match which templates
    - Creates new sub-runs with status="matched" (have template) or "needs_template"

    Phase 2 (Extraction + Pipeline):
    - Picks up sub-runs with status="matched" (have template assigned)
    - Runs data extraction and pipeline execution
    - Updates status to "success" or "failure"

    Features:
    - Async polling loop
    - Two-phase processing in single loop
    - Concurrent batch processing
    - Pause/resume capability
    - Graceful shutdown
    """

    def __init__(
        self,
        # Phase 1 callbacks (Template Matching)
        process_template_matching_callback: Callable[[int], bool],
        get_pending_template_matching_callback: Callable[[int], List[EtoSubRun]],
        # Phase 2 callbacks (Extraction + Pipeline)
        process_extraction_pipeline_callback: Callable[[int], bool],
        get_pending_extraction_pipeline_callback: Callable[[int], List[EtoSubRun]],
        # Reset callback
        reset_run_callback: Callable[[int], None],
        # Configuration
        enabled: bool = True,
        max_concurrent_runs: int = 10,
        polling_interval: int = 2,
        shutdown_timeout: int = 30
    ):
        """
        Initialize ETO Worker with two-phase callbacks.

        Args:
            process_template_matching_callback: Callback for Phase 1 (template matching)
            get_pending_template_matching_callback: Gets sub-runs needing template matching
            process_extraction_pipeline_callback: Callback for Phase 2 (extraction + pipeline)
            get_pending_extraction_pipeline_callback: Gets sub-runs ready for extraction
            reset_run_callback: Callback to reset a run (service._reset_run_to_not_started)
            enabled: Whether worker is enabled
            max_concurrent_runs: Maximum concurrent runs to process per phase
            polling_interval: Seconds between polling cycles
            shutdown_timeout: Seconds to wait for graceful shutdown
        """
        # Configuration
        self.enabled = enabled
        self.max_concurrent_runs = max_concurrent_runs
        self.polling_interval = polling_interval
        self.shutdown_timeout = shutdown_timeout

        # Phase 1 callbacks (Template Matching)
        self.process_template_matching_callback = process_template_matching_callback
        self.get_pending_template_matching_callback = get_pending_template_matching_callback

        # Phase 2 callbacks (Extraction + Pipeline)
        self.process_extraction_pipeline_callback = process_extraction_pipeline_callback
        self.get_pending_extraction_pipeline_callback = get_pending_extraction_pipeline_callback

        # Reset callback
        self.reset_run_callback = reset_run_callback

        # State
        self.running = False
        self.paused = False
        self.worker_task: Optional[asyncio.Task] = None
        self.currently_processing: Set[int] = set()

        logger.debug(
            f"EtoWorker initialized (two-phase) - enabled: {enabled}, "
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
        # Get pending counts from service for both phases
        pending_template_matching_count = 0
        pending_extraction_count = 0
        try:
            pending_template_matching = self.get_pending_template_matching_callback(100)
            pending_template_matching_count = len(pending_template_matching)
        except Exception as e:
            logger.error(f"Error getting pending template matching count: {e}")

        try:
            pending_extraction = self.get_pending_extraction_pipeline_callback(100)
            pending_extraction_count = len(pending_extraction)
        except Exception as e:
            logger.error(f"Error getting pending extraction count: {e}")

        return {
            "worker_enabled": self.enabled,
            "worker_running": self.running,
            "worker_paused": self.paused,
            "max_concurrent_runs": self.max_concurrent_runs,
            "polling_interval": self.polling_interval,
            "pending_template_matching_count": pending_template_matching_count,
            "pending_extraction_count": pending_extraction_count,
            "pending_runs_count": pending_template_matching_count + pending_extraction_count,
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
        Process pending runs in two phases concurrently.

        Phase 1: Template Matching
        - Gets sub-runs with status="not_started" AND no template
        - Runs template matching and creates matched/unmatched sub-runs

        Phase 2: Extraction + Pipeline
        - Gets sub-runs with status="matched" (have template)
        - Runs extraction and pipeline execution
        """
        try:
            # ===== Phase 1: Template Matching =====
            pending_template_matching = self.get_pending_template_matching_callback(
                self.max_concurrent_runs
            )

            if pending_template_matching:
                logger.debug(
                    f"Phase 1 (Template Matching): Processing batch of "
                    f"{len(pending_template_matching)} sub-runs"
                )

                tasks = [
                    self._process_run_async(
                        run.id,
                        self.process_template_matching_callback,
                        "template_matching"
                    )
                    for run in pending_template_matching
                ]

                results = await asyncio.gather(*tasks, return_exceptions=True)
                self._log_batch_results(results, pending_template_matching, "Phase 1")

            # ===== Phase 2: Extraction + Pipeline =====
            pending_extraction = self.get_pending_extraction_pipeline_callback(
                self.max_concurrent_runs
            )

            if pending_extraction:
                logger.debug(
                    f"Phase 2 (Extraction + Pipeline): Processing batch of "
                    f"{len(pending_extraction)} sub-runs"
                )

                tasks = [
                    self._process_run_async(
                        run.id,
                        self.process_extraction_pipeline_callback,
                        "extraction_pipeline"
                    )
                    for run in pending_extraction
                ]

                results = await asyncio.gather(*tasks, return_exceptions=True)
                self._log_batch_results(results, pending_extraction, "Phase 2")

        except Exception as e:
            logger.error(f"Error processing pending runs batch: {e}", exc_info=True)

    def _log_batch_results(
        self,
        results: list,
        runs: List[EtoSubRun],
        phase_name: str
    ):
        """Log batch processing results."""
        successful = sum(1 for r in results if not isinstance(r, Exception) and r is True)
        failed = len(results) - successful

        if failed > 0:
            logger.warning(f"{phase_name} batch completed: {successful} successful, {failed} failed")
            for i, result in enumerate(results):
                if isinstance(result, Exception):
                    logger.error(f"{phase_name} sub-run {runs[i].id} failed: {result}")
        else:
            logger.debug(f"{phase_name} batch completed successfully: {successful} sub-runs processed")

    async def _process_run_async(
        self,
        run_id: int,
        process_callback: Callable[[int], bool],
        phase_name: str
    ) -> bool:
        """
        Async wrapper for processing a single run.
        Runs the synchronous callback in thread pool.

        Args:
            run_id: ETO sub-run ID to process
            process_callback: The callback to use for processing
            phase_name: Name of the phase for logging

        Returns:
            True if successful, False if failed
        """
        self.currently_processing.add(run_id)
        try:
            logger.debug(f"Starting async {phase_name} for sub-run {run_id}")

            # Run synchronous processing callback in thread pool
            loop = asyncio.get_event_loop()
            success = await loop.run_in_executor(
                None,
                process_callback,
                run_id
            )

            logger.debug(f"Completed async {phase_name} for sub-run {run_id}: success={success}")
            return success

        except Exception as e:
            logger.error(f"Error in async {phase_name} for sub-run {run_id}: {e}", exc_info=True)
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
