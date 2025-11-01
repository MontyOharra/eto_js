"""
Data Transformation Processor
Stage 3: Executes pipeline with extracted data
"""
import json
import logging
from datetime import datetime, timezone

from shared.database.repositories.eto_run import EtoRunRepository
from shared.database.repositories.eto_run_pipeline_execution import EtoRunPipelineExecutionRepository
from shared.types.eto_runs import EtoRunUpdate
from shared.types.eto_run_pipeline_executions import (
    EtoRunPipelineExecutionCreate,
    EtoRunPipelineExecutionUpdate,
)
from shared.events.eto_events import eto_event_manager

logger = logging.getLogger(__name__)


class DataTransformationProcessor:
    """
    Stage 3: Pipeline Execution Processor

    Executes pipeline with extracted data.

    Process:
    1. Update run processing_step to "data_transformation"
    2. Create pipeline_execution record with status="processing"
    3. Get matched template and pipeline definition
    4. Get extracted data from extraction stage
    5. Execute pipeline with extracted data
    6. Update pipeline_execution record with results

    NOTE: Currently generates FAKE data for testing.
    TODO: Implement real pipeline execution using pipeline_execution_service.
    """

    def __init__(
        self,
        eto_run_repo: EtoRunRepository,
        pipeline_execution_repo: EtoRunPipelineExecutionRepository
    ):
        """
        Initialize Data Transformation Processor.

        Args:
            eto_run_repo: ETO run repository
            pipeline_execution_repo: Pipeline execution repository
        """
        self.eto_run_repo = eto_run_repo
        self.pipeline_execution_repo = pipeline_execution_repo

    def execute(self, run_id: int) -> bool:
        """
        Execute data transformation stage (STUB - FAKE DATA).

        Creates pipeline execution record with FAKE data to allow end-to-end
        testing of template matching stage.

        Args:
            run_id: ETO run ID

        Returns:
            True (always succeeds with fake data)

        Raises:
            Exception: If unexpected error occurs
        """
        logger.monitor(f"Run {run_id}: Executing data transformation stage (STUB - FAKE DATA)")  # type: ignore

        # Step 1: Update run processing_step
        self.eto_run_repo.update(
            run_id,
            EtoRunUpdate(processing_step="data_transformation")
        )
        logger.debug(f"Run {run_id}: Updated processing_step to data_transformation")

        # Broadcast processing step change
        eto_event_manager.broadcast_sync(
            "run_updated",
            {
                "id": run_id,
                "processing_step": "data_transformation",
            }
        )

        # Step 2: Create pipeline_execution record
        pipeline_execution = self.pipeline_execution_repo.create(
            EtoRunPipelineExecutionCreate(
                eto_run_id=run_id,
                started_at=datetime.now(timezone.utc)
            )
        )
        logger.debug(f"Run {run_id}: Created pipeline_execution record {pipeline_execution.id}")

        # Step 3: Generate fake executed actions
        # TODO: Replace with real pipeline execution:
        # 1. Get matched template version from template_matching stage
        # 2. Get extracted data from extraction stage
        # 3. Get template's pipeline definition
        # 4. Call pipeline_execution_service.execute_pipeline() with extracted data
        # 5. Store real execution results and step-by-step trace
        fake_executed_actions = {
            "steps_executed": [
                {"step": "validate_invoice", "status": "success", "output": "Invoice validated"},
                {"step": "transform_format", "status": "success", "output": "Format transformed"},
                {"step": "calculate_totals", "status": "success", "output": "Totals calculated"}
            ],
            "total_steps": 3,
            "successful_steps": 3,
            "failed_steps": 0
        }

        # Step 4: Update pipeline_execution record with fake data
        self.pipeline_execution_repo.update(
            pipeline_execution.id,
            EtoRunPipelineExecutionUpdate(
                status="success",
                executed_actions=json.dumps(fake_executed_actions),
                completed_at=datetime.now(timezone.utc)
            )
        )

        logger.monitor(f"Run {run_id}: Data transformation completed (STUB - FAKE DATA)")  # type: ignore
        return True
