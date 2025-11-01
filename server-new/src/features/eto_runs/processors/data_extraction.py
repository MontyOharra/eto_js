"""
Data Extraction Processor
Stage 2: Extracts field values from PDF using matched template
"""
import json
import logging
from datetime import datetime, timezone

from shared.database.repositories.eto_run import EtoRunRepository
from shared.database.repositories.eto_run_extraction import EtoRunExtractionRepository
from shared.types.eto_runs import EtoRunUpdate
from shared.types.eto_run_extractions import (
    EtoRunExtractionCreate,
    EtoRunExtractionUpdate,
)
from shared.events.eto_events import eto_event_manager

logger = logging.getLogger(__name__)


class DataExtractionProcessor:
    """
    Stage 2: Data Extraction Processor

    Extracts field values from PDF using matched template.

    Process:
    1. Update run processing_step to "data_extraction"
    2. Create extraction record with status="processing"
    3. Get matched template and extraction field configuration
    4. Extract data from PDF using template configuration
    5. Update extraction record with extracted data

    NOTE: Currently generates FAKE data for testing.
    TODO: Implement real extraction using template configuration.
    """

    def __init__(
        self,
        eto_run_repo: EtoRunRepository,
        extraction_repo: EtoRunExtractionRepository
    ):
        """
        Initialize Data Extraction Processor.

        Args:
            eto_run_repo: ETO run repository
            extraction_repo: Extraction repository
        """
        self.eto_run_repo = eto_run_repo
        self.extraction_repo = extraction_repo

    def execute(self, run_id: int) -> bool:
        """
        Execute data extraction stage (STUB - FAKE DATA).

        Creates extraction record with FAKE data to allow end-to-end testing
        of template matching stage.

        Args:
            run_id: ETO run ID

        Returns:
            True (always succeeds with fake data)

        Raises:
            Exception: If unexpected error occurs
        """
        logger.monitor(f"Run {run_id}: Executing data extraction stage (STUB - FAKE DATA)")  # type: ignore

        # Step 1: Update run processing_step
        self.eto_run_repo.update(
            run_id,
            EtoRunUpdate(processing_step="data_extraction")
        )
        logger.debug(f"Run {run_id}: Updated processing_step to data_extraction")

        # Broadcast processing step change
        eto_event_manager.broadcast_sync(
            "run_updated",
            {
                "id": run_id,
                "processing_step": "data_extraction",
            }
        )

        # Step 2: Create extraction record
        extraction = self.extraction_repo.create(
            EtoRunExtractionCreate(eto_run_id=run_id)
        )
        logger.debug(f"Run {run_id}: Created extraction record {extraction.id}")

        # Step 3: Generate fake extracted data
        # TODO: Replace with real extraction logic:
        # 1. Get matched template version from template_matching stage
        # 2. Get template's extraction_fields configuration
        # 3. Call PDF extraction service with PDF objects + extraction_fields
        # 4. Store real extracted data
        fake_extracted_data = {
            "invoice_number": "FAKE-INV-12345",
            "invoice_date": "2025-10-29",
            "vendor_name": "Test Vendor Inc.",
            "total_amount": "1234.56",
            "line_items": [
                {"description": "Test Item 1", "quantity": "2", "price": "500.00"},
                {"description": "Test Item 2", "quantity": "1", "price": "234.56"}
            ]
        }

        # Step 4: Update extraction record with fake data
        self.extraction_repo.update(
            extraction.id,
            EtoRunExtractionUpdate(
                status="success",
                extracted_data=json.dumps(fake_extracted_data),
                started_at=datetime.now(timezone.utc),
                completed_at=datetime.now(timezone.utc)
            )
        )

        logger.monitor(f"Run {run_id}: Data extraction completed (STUB - FAKE DATA)")  # type: ignore
        return True
