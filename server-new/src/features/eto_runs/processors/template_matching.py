"""
Template Matching Processor
Stage 1: Matches PDF to best template using PDF objects
"""
import logging
from datetime import datetime, timezone
from typing import TYPE_CHECKING

from shared.database.repositories.eto_run import EtoRunRepository
from shared.database.repositories.eto_run_template_matching import EtoRunTemplateMatchingRepository
from shared.types.eto_runs import EtoRunUpdate
from shared.types.eto_run_template_matchings import (
    EtoRunTemplateMatchingCreate,
    EtoRunTemplateMatchingUpdate,
)
from shared.exceptions.service import ServiceError
from shared.events.eto_events import eto_event_manager

if TYPE_CHECKING:
    from features.pdf_files.service import PdfFilesService
    from features.pdf_templates.service import PdfTemplateService

logger = logging.getLogger(__name__)


class TemplateMatchingProcessor:
    """
    Stage 1: Template Matching Processor

    Matches PDF to best template using PDF objects.

    Process:
    1. Update run processing_step to "template_matching"
    2. Create template_matching record with status="processing"
    3. Get PDF objects from PDF file
    4. Call PDF template service to match PDF
    5. Update template_matching record with result
    6. If no match: update run status to "needs_template"
    """

    def __init__(
        self,
        eto_run_repo: EtoRunRepository,
        template_matching_repo: EtoRunTemplateMatchingRepository,
        pdf_files_service: 'PdfFilesService',
        pdf_template_service: 'PdfTemplateService'
    ):
        """
        Initialize Template Matching Processor.

        Args:
            eto_run_repo: ETO run repository
            template_matching_repo: Template matching repository
            pdf_files_service: Service for PDF file access
            pdf_template_service: Service for template matching
        """
        self.eto_run_repo = eto_run_repo
        self.template_matching_repo = template_matching_repo
        self.pdf_files_service = pdf_files_service
        self.pdf_template_service = pdf_template_service

    def execute(self, run_id: int) -> bool:
        """
        Execute template matching stage.

        Args:
            run_id: ETO run ID

        Returns:
            True if match found and successful, False if no match or needs_template

        Raises:
            Exception: If unexpected error occurs (caught by orchestrator)
        """
        logger.monitor(f"Run {run_id}: Executing template matching stage")  # type: ignore

        # Step 1: Update run processing_step
        self.eto_run_repo.update(
            run_id,
            EtoRunUpdate(processing_step="template_matching")
        )
        logger.debug(f"Run {run_id}: Updated processing_step to template_matching")

        # Broadcast processing step change
        eto_event_manager.broadcast_sync(
            "run_updated",
            {
                "id": run_id,
                "processing_step": "template_matching",
            }
        )

        # Step 2: Create template_matching record with status="processing"
        started_at = datetime.now(timezone.utc)
        template_matching = self.template_matching_repo.create(
            EtoRunTemplateMatchingCreate(eto_run_id=run_id)
        )
        logger.debug(f"Run {run_id}: Created template_matching record {template_matching.id}")

        # Step 2b: Update with started_at timestamp
        template_matching = self.template_matching_repo.update(
            template_matching.id,
            EtoRunTemplateMatchingUpdate(started_at=started_at)
        )
        logger.debug(f"Run {run_id}: Set template_matching started_at")

        try:
            # Step 3: Get PDF objects from PDF file
            run = self.eto_run_repo.get_by_id(run_id)
            if not run:
                raise ServiceError(f"Run {run_id} not found")

            pdf_objects = self.pdf_files_service.get_pdf_objects(run.pdf_file_id)
            logger.debug(f"Run {run_id}: Retrieved PDF objects from file {run.pdf_file_id}")

            # Step 4: Call template matching service
            match_result = self.pdf_template_service.match_template(pdf_objects)

            # Step 5: Handle match result
            if match_result is None:
                # No template matched
                logger.monitor(f"Run {run_id}: No template match found")  # type: ignore

                # Update template_matching record to failure
                self.template_matching_repo.update(
                    template_matching.id,
                    EtoRunTemplateMatchingUpdate(
                        status="failure",
                        completed_at=datetime.now(timezone.utc)
                    )
                )

                # Update run status to "needs_template"
                completed_at = datetime.now(timezone.utc)
                self.eto_run_repo.update(
                    run_id,
                    EtoRunUpdate(
                        status="needs_template",
                        completed_at=completed_at,
                        error_type="NoTemplateMatch",
                        error_message="No matching template found for this PDF"
                    )
                )

                # Broadcast status change
                eto_event_manager.broadcast_sync(
                    "run_updated",
                    {
                        "id": run_id,
                        "status": "needs_template",
                        "completed_at": completed_at.isoformat(),
                        "error_type": "NoTemplateMatch",
                        "error_message": "No matching template found for this PDF"
                    }
                )

                logger.warning(f"Run {run_id}: Set status to needs_template - no template match")
                return False

            # Match found!
            template_id, version_id = match_result
            logger.monitor(f"Run {run_id}: Template match found - template {template_id}, version {version_id}")  # type: ignore

            # Update template_matching record to success
            self.template_matching_repo.update(
                template_matching.id,
                EtoRunTemplateMatchingUpdate(
                    status="success",
                    matched_template_version_id=version_id,
                    completed_at=datetime.now(timezone.utc)
                )
            )

            logger.monitor(f"Run {run_id}: Template matching completed successfully")  # type: ignore
            return True

        except Exception as e:
            # Error during template matching
            logger.error(f"Run {run_id}: Template matching error: {e}", exc_info=True)

            # Update template_matching record to failure
            self.template_matching_repo.update(
                template_matching.id,
                EtoRunTemplateMatchingUpdate(
                    status="failure",
                    completed_at=datetime.now(timezone.utc)
                )
            )

            # Re-raise to be caught by process_run's error handling
            raise
