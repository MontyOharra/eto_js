"""
ETO Run Repository - New Implementation
Data access layer for EtoRunModel operations based on eto_processing models
"""

import json
import logging
from typing import Optional, List, Dict, Any
from datetime import datetime, timezone
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy import func, case, update, delete

from shared.database.repositories.base import BaseRepository
from shared.database.models import EtoRunModel
from shared.exceptions import RepositoryError, ObjectNotFoundError, ValidationError
from shared.models import (
    EtoRun, EtoRunCreate, EtoRunSummary, EtoRunStatus, EtoProcessingStep, EtoErrorType,
    EtoRunTemplateMatchUpdate, EtoRunDataExtractionUpdate, EtoRunTransformationUpdate,
    EtoRunOrderUpdate, EtoRunResetResult
)
from shared.utils import DateTimeUtils


logger = logging.getLogger(__name__)


def _calculate_duration_ms(current_time: datetime, started_at: datetime) -> int:
    """
    Calculate duration in milliseconds, handling timezone-aware vs timezone-naive datetime objects

    Args:
        current_time: Current time (typically timezone-aware)
        started_at: Start time (may be timezone-naive after DB round-trip)

    Returns:
        Duration in milliseconds as integer
    """
    # Ensure both datetimes are timezone-aware for comparison using DateTimeUtils
    started_at = DateTimeUtils.ensure_utc_aware(started_at)
    current_time = DateTimeUtils.ensure_utc_aware(current_time)

    duration_seconds = (current_time - started_at).total_seconds()
    return int(duration_seconds * 1000)


class EtoRunRepository(BaseRepository[EtoRunModel]):
    """Repository for EtoRunModel operations using eto_processing models"""

    @property
    def model_class(self):
        return EtoRunModel

    def _convert_to_domain_object(self, eto_run_model: EtoRunModel) -> EtoRun:
        """Convert database model to domain object"""
        return EtoRun.from_db_model(eto_run_model)

    # ========== Basic CRUD Operations ==========

    def create(self, eto_run_create: EtoRunCreate) -> EtoRun:
        """
        Create a new ETO run with default values
        Only pdf_file_id is required - all other fields have defaults
        """
        try:
            with self.connection_manager.session_scope() as session:
                # Create model with defaults
                model_data = eto_run_create.model_dump_for_db()

                # Ensure default status is set
                model_data['status'] = EtoRunStatus.NOT_STARTED.value

                # Create and save model
                model = self.model_class(**model_data)
                session.add(model)
                session.flush()  # Get ID

                logger.debug(f"Created ETO run {model.id} for PDF {eto_run_create.pdf_file_id}")

                return self._convert_to_domain_object(model)

        except SQLAlchemyError as e:
            logger.error(f"Error creating ETO run for PDF {eto_run_create.pdf_file_id}: {e}")
            raise RepositoryError(f"Failed to create ETO run: {e}") from e

    def get_by_id(self, eto_run_id: int) -> Optional[EtoRun]:
        """Get ETO run by ID"""
        try:
            with self.connection_manager.session_scope() as session:
                model = session.get(self.model_class, eto_run_id)

                if model:
                    logger.debug(f"Retrieved ETO run {eto_run_id}")
                    return self._convert_to_domain_object(model)
                return None

        except SQLAlchemyError as e:
            logger.error(f"Error getting ETO run {eto_run_id}: {e}")
            raise RepositoryError(f"Failed to get ETO run: {e}") from e

    def get_by_pdf_file_id(self, pdf_file_id: int) -> List[EtoRun]:
        """Get all ETO runs for a specific PDF file"""
        try:
            with self.connection_manager.session_scope() as session:
                models = (
                    session.query(self.model_class)
                    .filter(self.model_class.pdf_file_id == pdf_file_id)
                    .order_by(self.model_class.created_at.desc())
                    .all()
                )

                logger.debug(f"Retrieved {len(models)} ETO runs for PDF {pdf_file_id}")
                return [self._convert_to_domain_object(model) for model in models]

        except SQLAlchemyError as e:
            logger.error(f"Error getting ETO runs for PDF {pdf_file_id}: {e}")
            raise RepositoryError(f"Failed to get ETO runs for PDF: {e}") from e

    # ========== User Dashboard Functionality ==========

    def get_runs_by_status(self, status: EtoRunStatus, limit: Optional[int] = None) -> List[EtoRunSummary]:
        """Get ETO runs by status for dashboard display"""
        try:
            with self.connection_manager.session_scope() as session:
                query = (
                    session.query(self.model_class)
                    .filter(self.model_class.status == status.value)
                    .order_by(self.model_class.created_at.desc())
                )

                if limit:
                    query = query.limit(limit)

                models = query.all()

                # Convert to summaries for efficient dashboard display
                summaries = [
                    EtoRunSummary.from_eto_run(self._convert_to_domain_object(model))
                    for model in models
                ]

                logger.debug(f"Retrieved {len(summaries)} ETO runs with status {status.value}")
                return summaries

        except SQLAlchemyError as e:
            logger.error(f"Error getting ETO runs by status {status.value}: {e}")
            raise RepositoryError(f"Failed to get ETO runs by status: {e}") from e

    def get_all_runs_grouped_by_status(self) -> Dict[str, List[EtoRunSummary]]:
        """Get all runs grouped by status for dashboard"""
        try:
            with self.connection_manager.session_scope() as session:
                models = (
                    session.query(self.model_class)
                    .order_by(self.model_class.status, self.model_class.created_at.desc())
                    .all()
                )

                # Group by status
                grouped_runs = {}
                for model in models:
                    domain_obj = self._convert_to_domain_object(model)
                    summary = EtoRunSummary.from_eto_run(domain_obj)

                    status_key = model.status
                    if status_key not in grouped_runs:
                        grouped_runs[status_key] = []
                    grouped_runs[status_key].append(summary)

                logger.debug(f"Retrieved {len(models)} ETO runs grouped by status")
                return grouped_runs

        except SQLAlchemyError as e:
            logger.error(f"Error getting ETO runs grouped by status: {e}")
            raise RepositoryError(f"Failed to get ETO runs grouped by status: {e}") from e

    # ========== User Reprocessing Functionality ==========

    def reset_single_run_for_reprocessing(self, eto_run_id: int) -> EtoRun:
        """Reset individual run to not_started status for reprocessing"""
        try:
            with self.connection_manager.session_scope() as session:
                model = session.get(self.model_class, eto_run_id)

                if not model:
                    raise ObjectNotFoundError("EtoRun", eto_run_id)

                # Check if run can be reprocessed
                current_status = EtoRunStatus(model.status)
                if not current_status in [EtoRunStatus.FAILURE, EtoRunStatus.NEEDS_TEMPLATE]:
                    raise ValidationError(f"Cannot reprocess ETO run {eto_run_id}: status is {current_status.value}")

                # Reset all processing fields to defaults
                self._reset_processing_fields(model)

                logger.info(f"Reset ETO run {eto_run_id} for reprocessing")
                return self._convert_to_domain_object(model)

        except SQLAlchemyError as e:
            logger.error(f"Error resetting ETO run {eto_run_id} for reprocessing: {e}")
            raise RepositoryError(f"Failed to reset ETO run for reprocessing: {e}") from e

    def reset_failed_runs_for_reprocessing(self) -> EtoRunResetResult:
        """Reset all failed runs to not_started status"""
        return self._bulk_reset_runs([EtoRunStatus.FAILURE])

    def reset_needs_template_runs_for_reprocessing(self) -> EtoRunResetResult:
        """Reset all needs_template runs to not_started status"""
        return self._bulk_reset_runs([EtoRunStatus.NEEDS_TEMPLATE])

    def reset_failed_and_needs_template_runs_for_reprocessing(self) -> EtoRunResetResult:
        """Reset all failed and needs_template runs to not_started status"""
        return self._bulk_reset_runs([EtoRunStatus.FAILURE, EtoRunStatus.NEEDS_TEMPLATE])

    def reset_selected_runs_for_reprocessing(self, eto_run_ids: List[int]) -> EtoRunResetResult:
        """Reset selected runs to not_started status"""
        if not eto_run_ids:
            return EtoRunResetResult(
                failure_count=0,
                needs_template_count=0,
                total_reset=0
            )

        try:
            with self.connection_manager.session_scope() as session:
                # Get current status counts
                eligible_runs = (
                    session.query(self.model_class)
                    .filter(
                        self.model_class.id.in_(eto_run_ids),
                        self.model_class.status.in_([EtoRunStatus.FAILURE.value, EtoRunStatus.NEEDS_TEMPLATE.value])
                    )
                    .all()
                )

                failure_count = sum(1 for run in eligible_runs if run.status == EtoRunStatus.FAILURE.value)
                needs_template_count = sum(1 for run in eligible_runs if run.status == EtoRunStatus.NEEDS_TEMPLATE.value)

                # Reset the runs
                for model in eligible_runs:
                    self._reset_processing_fields(model)

                total_reset = len(eligible_runs)

                logger.info(f"Reset {total_reset} selected ETO runs for reprocessing")

                return EtoRunResetResult(
                    failure_count=failure_count,
                    needs_template_count=needs_template_count,
                    total_reset=total_reset
                )

        except SQLAlchemyError as e:
            logger.error(f"Error resetting selected ETO runs for reprocessing: {e}")
            raise RepositoryError(f"Failed to reset selected ETO runs for reprocessing: {e}") from e

    # ========== User Skip/Delete Functionality ==========

    def mark_as_skipped(self, eto_run_id: int) -> EtoRun:
        """Mark run as skipped (only from failure or needs_template status)"""
        try:
            with self.connection_manager.session_scope() as session:
                model = session.get(self.model_class, eto_run_id)

                if not model:
                    raise ObjectNotFoundError("EtoRun", eto_run_id)

                # Check if run can be skipped
                current_status = EtoRunStatus(model.status)
                if current_status not in [EtoRunStatus.FAILURE, EtoRunStatus.NEEDS_TEMPLATE]:
                    raise ValidationError(f"Cannot skip ETO run {eto_run_id}: status must be failure or needs_template, current status is {current_status.value}")

                # Update status and clear processing fields
                model.status = EtoRunStatus.SKIPPED.value
                model.processing_step = None
                model.completed_at = DateTimeUtils.utc_now()

                logger.info(f"Marked ETO run {eto_run_id} as skipped")
                return self._convert_to_domain_object(model)

        except SQLAlchemyError as e:
            logger.error(f"Error marking ETO run {eto_run_id} as skipped: {e}")
            raise RepositoryError(f"Failed to mark ETO run as skipped: {e}") from e

    def delete_skipped_run(self, eto_run_id: int) -> EtoRun:
        """Permanently delete run (only if status is skipped)"""
        try:
            with self.connection_manager.session_scope() as session:
                model = session.get(self.model_class, eto_run_id)

                if not model:
                    raise ObjectNotFoundError("EtoRun", eto_run_id)

                # Check if run can be deleted
                current_status = EtoRunStatus(model.status)
                if current_status != EtoRunStatus.SKIPPED:
                    raise ValidationError(f"Cannot delete ETO run {eto_run_id}: status must be skipped, current status is {current_status.value}")

                # Convert to domain object before deletion
                deleted_run = self._convert_to_domain_object(model)

                session.delete(model)

                logger.info(f"Permanently deleted ETO run {eto_run_id}")
                return deleted_run

        except SQLAlchemyError as e:
            logger.error(f"Error deleting ETO run {eto_run_id}: {e}")
            raise RepositoryError(f"Failed to delete ETO run: {e}") from e

    # ========== System Processing Functionality ==========

    def start_processing(self, eto_run_id: int) -> EtoRun:
        """Start processing: set status to processing and step to template_matching"""
        try:
            with self.connection_manager.session_scope() as session:
                model = session.get(self.model_class, eto_run_id)

                if not model:
                    raise ObjectNotFoundError("EtoRun", eto_run_id)

                # Validate current status
                current_status = EtoRunStatus(model.status)
                if current_status != EtoRunStatus.NOT_STARTED:
                    raise ValidationError(f"Cannot start processing ETO run {eto_run_id}: status must be not_started, current status is {current_status.value}")

                # Update to processing state
                current_time = DateTimeUtils.utc_now()
                model.status = EtoRunStatus.PROCESSING.value
                model.processing_step = EtoProcessingStep.TEMPLATE_MATCHING.value
                model.started_at = current_time

                logger.debug(f"Started processing ETO run {eto_run_id}")
                return self._convert_to_domain_object(model)

        except SQLAlchemyError as e:
            logger.error(f"Error starting processing for ETO run {eto_run_id}: {e}")
            raise RepositoryError(f"Failed to start processing ETO run: {e}") from e

    def set_template_match_and_advance(self, eto_run_id: int, template_match: EtoRunTemplateMatchUpdate) -> EtoRun:
        """Set template match results and advance to extracting_data step"""
        try:
            with self.connection_manager.session_scope() as session:
                model = session.get(self.model_class, eto_run_id)

                if not model:
                    raise ObjectNotFoundError("EtoRun", eto_run_id)

                # Validate current state
                self._validate_processing_state(model, EtoProcessingStep.TEMPLATE_MATCHING)

                # Update template match and advance processing step
                model.matched_template_id = template_match.matched_template_id
                model.matched_template_version = template_match.matched_template_version
                model.processing_step = EtoProcessingStep.EXTRACTING_DATA.value

                logger.debug(f"Set template match for ETO run {eto_run_id}: template {template_match.matched_template_id} v{template_match.matched_template_version}")
                return self._convert_to_domain_object(model)

        except SQLAlchemyError as e:
            logger.error(f"Error setting template match for ETO run {eto_run_id}: {e}")
            raise RepositoryError(f"Failed to set template match: {e}") from e

    def set_extracted_data_and_advance(self, eto_run_id: int, extraction_data: EtoRunDataExtractionUpdate) -> EtoRun:
        """Set extracted data and advance to transforming_data step"""
        try:
            with self.connection_manager.session_scope() as session:
                model = session.get(self.model_class, eto_run_id)

                if not model:
                    raise ObjectNotFoundError("EtoRun", eto_run_id)

                # Validate current state
                self._validate_processing_state(model, EtoProcessingStep.EXTRACTING_DATA)

                # Update extracted data and advance processing step
                model.extracted_data = json.dumps(extraction_data.extracted_data)
                model.processing_step = EtoProcessingStep.TRANSFORMING_DATA.value

                logger.debug(f"Set extracted data for ETO run {eto_run_id}")
                return self._convert_to_domain_object(model)

        except SQLAlchemyError as e:
            logger.error(f"Error setting extracted data for ETO run {eto_run_id}: {e}")
            raise RepositoryError(f"Failed to set extracted data: {e}") from e

    def set_transformed_data_and_complete(self, eto_run_id: int, transformation_data: EtoRunTransformationUpdate) -> EtoRun:
        """Set transformed data and mark as completed successfully"""
        try:
            with self.connection_manager.session_scope() as session:
                model = session.get(self.model_class, eto_run_id)

                if not model:
                    raise ObjectNotFoundError("EtoRun", eto_run_id)

                # Validate current state
                self._validate_processing_state(model, EtoProcessingStep.TRANSFORMING_DATA)

                # Update transformation results and complete processing
                current_time = DateTimeUtils.utc_now()

                model.target_data = json.dumps(transformation_data.target_data)
                if transformation_data.transformation_audit:
                    model.transformation_audit = json.dumps(transformation_data.transformation_audit)
                if transformation_data.step_execution_log:
                    model.step_execution_log = json.dumps(transformation_data.step_execution_log)

                # Complete processing
                model.status = EtoRunStatus.SUCCESS.value
                model.processing_step = None
                model.completed_at = current_time

                # Calculate processing duration
                if model.started_at:
                    model.processing_duration_ms = _calculate_duration_ms(current_time, model.started_at)

                logger.info(f"Completed ETO run {eto_run_id} successfully")
                return self._convert_to_domain_object(model)

        except SQLAlchemyError as e:
            logger.error(f"Error setting transformed data for ETO run {eto_run_id}: {e}")
            raise RepositoryError(f"Failed to set transformed data: {e}") from e

    def set_order_integration(self, eto_run_id: int, order_data: EtoRunOrderUpdate) -> EtoRun:
        """Set order ID after successful order creation"""
        try:
            with self.connection_manager.session_scope() as session:
                model = session.get(self.model_class, eto_run_id)

                if not model:
                    raise ObjectNotFoundError("EtoRun", eto_run_id)

                # Validate status
                current_status = EtoRunStatus(model.status)
                if current_status != EtoRunStatus.SUCCESS:
                    raise ValidationError(f"Cannot set order integration for ETO run {eto_run_id}: status must be success, current status is {current_status.value}")

                model.order_id = order_data.order_id

                logger.debug(f"Set order integration for ETO run {eto_run_id}: order {order_data.order_id}")
                return self._convert_to_domain_object(model)

        except SQLAlchemyError as e:
            logger.error(f"Error setting order integration for ETO run {eto_run_id}: {e}")
            raise RepositoryError(f"Failed to set order integration: {e}") from e

    def set_failure_with_error(self, eto_run_id: int, error_type: EtoErrorType, error_message: str, error_details: Optional[Dict[str, Any]] = None, failed_pipeline_step_id: Optional[int] = None) -> EtoRun:
        """Set run as failed with error information"""
        try:
            with self.connection_manager.session_scope() as session:
                model = session.get(self.model_class, eto_run_id)

                if not model:
                    raise ObjectNotFoundError("EtoRun", eto_run_id)

                # Validate current status (must be processing)
                current_status = EtoRunStatus(model.status)
                if current_status != EtoRunStatus.PROCESSING:
                    raise ValidationError(f"Cannot set failure for ETO run {eto_run_id}: status must be processing, current status is {current_status.value}")

                # Set error information and failure status
                current_time = DateTimeUtils.utc_now()

                model.status = EtoRunStatus.FAILURE.value
                model.processing_step = None
                model.error_type = error_type.value
                model.error_message = error_message
                if error_details:
                    model.error_details = json.dumps(error_details)
                if failed_pipeline_step_id:
                    model.failed_pipeline_step_id = failed_pipeline_step_id

                model.completed_at = current_time

                # Calculate processing duration
                if model.started_at:
                    model.processing_duration_ms = _calculate_duration_ms(current_time, model.started_at)

                logger.warning(f"Set ETO run {eto_run_id} as failed: {error_type.value} - {error_message}")
                return self._convert_to_domain_object(model)

        except SQLAlchemyError as e:
            logger.error(f"Error setting failure for ETO run {eto_run_id}: {e}")
            raise RepositoryError(f"Failed to set failure: {e}") from e

    def set_needs_template(self, eto_run_id: int, message: str = "No matching template found") -> EtoRun:
        """Set run as needs_template when no matching template is found (not an error condition)"""
        try:
            with self.connection_manager.session_scope() as session:
                model = session.get(self.model_class, eto_run_id)

                if not model:
                    raise ObjectNotFoundError("EtoRun", eto_run_id)

                # Validate current state (must be processing with template_matching step)
                self._validate_processing_state(model, EtoProcessingStep.TEMPLATE_MATCHING)

                # Set needs_template status (not an error - system correctly identified it needs a template)
                current_time = DateTimeUtils.utc_now()

                model.status = EtoRunStatus.NEEDS_TEMPLATE.value
                model.processing_step = None
                # Don't set error fields - needs_template is a normal workflow outcome, not an error
                model.error_type = None
                model.error_message = None
                model.error_details = None
                model.completed_at = current_time

                # Calculate processing duration
                if model.started_at:
                    model.processing_duration_ms = _calculate_duration_ms(current_time, model.started_at)

                logger.info(f"Set ETO run {eto_run_id} as needs_template: {message}")
                return self._convert_to_domain_object(model)

        except SQLAlchemyError as e:
            logger.error(f"Error setting needs_template for ETO run {eto_run_id}: {e}")
            raise RepositoryError(f"Failed to set needs_template: {e}") from e

    # ========== Helper Methods ==========

    def _bulk_reset_runs(self, statuses: List[EtoRunStatus]) -> EtoRunResetResult:
        """Helper method for bulk resetting runs by status"""
        try:
            with self.connection_manager.session_scope() as session:
                status_values = [status.value for status in statuses]

                # Get counts first
                failure_count = 0
                needs_template_count = 0

                if EtoRunStatus.FAILURE in statuses:
                    failure_count = session.query(self.model_class).filter(
                        self.model_class.status == EtoRunStatus.FAILURE.value
                    ).count()

                if EtoRunStatus.NEEDS_TEMPLATE in statuses:
                    needs_template_count = session.query(self.model_class).filter(
                        self.model_class.status == EtoRunStatus.NEEDS_TEMPLATE.value
                    ).count()

                # Bulk update
                update_count = session.query(self.model_class).filter(
                    self.model_class.status.in_(status_values)
                ).update({
                    self.model_class.status: EtoRunStatus.NOT_STARTED.value,
                    self.model_class.processing_step: None,
                    self.model_class.error_type: None,
                    self.model_class.error_message: None,
                    self.model_class.error_details: None,
                    self.model_class.matched_template_id: None,
                    self.model_class.matched_template_version: None,
                    self.model_class.extracted_data: None,
                    self.model_class.transformation_audit: None,
                    self.model_class.target_data: None,
                    self.model_class.failed_pipeline_step_id: None,
                    self.model_class.step_execution_log: None,
                    self.model_class.started_at: None,
                    self.model_class.completed_at: None,
                    self.model_class.processing_duration_ms: None,
                    self.model_class.order_id: None,
                }, synchronize_session=False)

                logger.info(f"Bulk reset {update_count} ETO runs for reprocessing")

                return EtoRunResetResult(
                    failure_count=failure_count,
                    needs_template_count=needs_template_count,
                    total_reset=update_count
                )

        except SQLAlchemyError as e:
            logger.error(f"Error bulk resetting ETO runs: {e}")
            raise RepositoryError(f"Failed to bulk reset ETO runs: {e}") from e

    def _reset_processing_fields(self, model: EtoRunModel) -> None:
        """Helper method to reset all processing fields to defaults"""
        model.status = EtoRunStatus.NOT_STARTED.value
        model.processing_step = None
        model.error_type = None
        model.error_message = None
        model.error_details = None
        model.matched_template_id = None
        model.matched_template_version = None
        model.extracted_data = None
        model.transformation_audit = None
        model.target_data = None
        model.failed_pipeline_step_id = None
        model.step_execution_log = None
        model.started_at = None
        model.completed_at = None
        model.processing_duration_ms = None
        model.order_id = None

    def _validate_processing_state(self, model: EtoRunModel, expected_step: EtoProcessingStep) -> None:
        """Helper method to validate current processing state"""
        current_status = EtoRunStatus(model.status)
        if current_status != EtoRunStatus.PROCESSING:
            raise ValidationError(f"ETO run {model.id} is not in processing status: {current_status.value}")

        current_step = model.processing_step
        if current_step != expected_step.value:
            raise ValidationError(f"ETO run {model.id} is not in expected processing step. Expected: {expected_step.value}, Current: {current_step}")