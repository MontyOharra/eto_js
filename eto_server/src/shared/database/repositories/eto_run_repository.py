"""
ETO Run Repository
Data access layer for EtoRunModel model operations
"""

import logging
from typing import Optional, List, Dict, Any
from datetime import datetime, timezone
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy import func, case
from .base_repository import BaseRepository, RepositoryError
from ..models import EtoRunModel
from ....features.eto_processing.types import EtoRun


logger = logging.getLogger(__name__)


class EtoRunRepository(BaseRepository[EtoRunModel]):
    """Repository for EtoRunModel model operations"""

    @property
    def model_class(self):
        return EtoRunModel

    def _convert_to_domain_object(self, eto_run_model: EtoRunModel) -> EtoRun:
        """Convert database model to domain object while session is active"""
        eto_run_data = {
            "id": getattr(eto_run_model, "id"),
            "email_id": getattr(eto_run_model, "email_id"),
            "pdf_file_id": getattr(eto_run_model, "pdf_file_id"),
            "status": getattr(eto_run_model, "status"),
            "created_at": getattr(eto_run_model, "created_at"),
            "updated_at": getattr(eto_run_model, "updated_at"),
            "processing_step": getattr(eto_run_model, "processing_step"),
            "error_type": getattr(eto_run_model, "error_type"),
            "error_message": getattr(eto_run_model, "error_message"),
            "error_details": getattr(eto_run_model, "error_details"),
            "matched_template_id": getattr(eto_run_model, "matched_template_id"),
            "template_version": getattr(eto_run_model, "template_version"),
            "template_match_coverage": getattr(
                eto_run_model, "template_match_coverage"
            ),
            "unmatched_object_count": getattr(eto_run_model, "unmatched_object_count"),
            "extracted_data": getattr(eto_run_model, "extracted_data"),
            "transformation_audit": getattr(eto_run_model, "transformation_audit"),
            "target_data": getattr(eto_run_model, "target_data"),
            "failed_step_id": getattr(eto_run_model, "failed_pipeline_step_id"),
            "step_execution_log": getattr(eto_run_model, "step_execution_log"),
            "started_at": getattr(eto_run_model, "started_at"),
            "completed_at": getattr(eto_run_model, "completed_at"),
            "processing_duration_ms": getattr(eto_run_model, "processing_duration_ms"),
            "order_id": getattr(eto_run_model, "order_id"),
        }
        return EtoRun(**eto_run_data)

    def get_by_id(self, id: int) -> Optional[EtoRun]:
        """Override BaseRepository method to return domain object"""
        try:
            with self.connection_manager.session_scope() as session:
                # Get the model from the session using SQLAlchemy 2.x pattern
                model = session.get(self.model_class, id)

                if model:
                    # Convert to domain object while session is still active
                    logger.debug(
                        f"Retrieved ETO run: {getattr(model, 'id')} for email {getattr(model, 'email_id')}"
                    )
                    return self._convert_to_domain_object(model)
                else:
                    return None
        except SQLAlchemyError as e:
            logger.error(f"Error getting ETO run {id}: {e}")
            raise RepositoryError(f"Failed to get ETO run: {e}") from e

    def get_by_status(self, status: str, limit: Optional[int] = None) -> List[EtoRun]:
        """Get ETO runs by status"""
        if not status:
            return []

        try:
            with self.connection_manager.session_scope() as session:
                query = (
                    session.query(self.model_class)
                    .filter(self.model_class.status == status)
                    .order_by(self.model_class.created_at.desc())
                )

                if limit is not None:
                    query = query.limit(limit)

                models = query.all()

                # Convert all models to domain objects
                return [self._convert_to_domain_object(model) for model in models]

        except SQLAlchemyError as e:
            logger.error(f"Error getting ETO runs by status {status}: {e}")
            raise RepositoryError(f"Failed to get ETO runs by status: {e}") from e

    def get_by_email_id(self, email_id: int) -> List[EtoRun]:
        """Get all ETO runs for a specific email"""
        if email_id is None:
            return []

        try:
            with self.connection_manager.session_scope() as session:
                models = (
                    session.query(self.model_class)
                    .filter(self.model_class.email_id == email_id)
                    .all()
                )

                # Convert all models to domain objects
                return [self._convert_to_domain_object(model) for model in models]

        except SQLAlchemyError as e:
            logger.error(f"Error getting ETO runs for email {email_id}: {e}")
            raise RepositoryError(f"Failed to get ETO runs for email: {e}") from e

    def get_by_pdf_id(self, pdf_file_id: int) -> List["EtoRun"]:
        """Get all ETO runs for a specific PDF file"""
        if pdf_file_id is None:
            return []

        try:
            with self.connection_manager.session_scope() as session:
                models = (
                    session.query(self.model_class)
                    .filter(self.model_class.pdf_file_id == pdf_file_id)
                    .all()
                )

                # Convert all models to domain objects
                return [self._convert_to_domain_object(model) for model in models]

        except SQLAlchemyError as e:
            logger.error(f"Error getting ETO runs for PDF {pdf_file_id}: {e}")
            raise RepositoryError(f"Failed to get ETO runs for PDF: {e}") from e

    def get_by_template_id(self, template_id: int) -> List["EtoRun"]:
        """Get all ETO runs that used a specific template"""
        if template_id is None:
            return []

        try:
            with self.connection_manager.session_scope() as session:
                models = (
                    session.query(self.model_class)
                    .filter(self.model_class.matched_template_id == template_id)
                    .all()
                )

                # Convert all models to domain objects
                return [self._convert_to_domain_object(model) for model in models]

        except SQLAlchemyError as e:
            logger.error(f"Error getting ETO runs for template {template_id}: {e}")
            raise RepositoryError(f"Failed to get ETO runs for template: {e}") from e

    def get_pending_runs(self, limit: Optional[int] = None) -> List["EtoRun"]:
        """Get runs with status 'not_started'"""
        return self.get_by_status("not_started", limit)

    def get_processing_runs(self) -> List["EtoRun"]:
        """Get runs currently being processed"""
        return self.get_by_status("processing")

    def get_failed_runs(self, limit: Optional[int] = None) -> List["EtoRun"]:
        """Get runs with status 'failure'"""
        return self.get_by_status("failure", limit)

    def get_successful_runs(self, limit: Optional[int] = None) -> List["EtoRun"]:
        """Get runs with status 'success'"""
        return self.get_by_status("success", limit)

    def get_runs_needing_templates(self, limit: Optional[int] = None) -> List["EtoRun"]:
        """Get runs with status 'needs_template'"""
        return self.get_by_status("needs_template", limit)

    def update_status(self, run_id: int, status: str, **kwargs) -> Optional["EtoRun"]:
        """Update run status and related fields"""
        if run_id is None or not status:
            raise ValueError("run_id and status are required")

        # Build update data with status and any additional fields
        update_data = {"status": status, **kwargs}

        # Add automatic timestamp updates based on status
        current_time = datetime.now(timezone.utc)
        if status == "processing" and "started_at" not in update_data:
            update_data["started_at"] = current_time
        elif (
            status in ["success", "failure", "skipped"]
            and "completed_at" not in update_data
        ):
            update_data["completed_at"] = current_time

            # Calculate processing duration if we have started_at
            existing_run = self.get_by_id(run_id)
            if (
                existing_run
                and existing_run.started_at is not None
                and "processing_duration_ms" not in update_data
            ):
                duration = current_time - existing_run.started_at
                update_data["processing_duration_ms"] = int(
                    duration.total_seconds() * 1000
                )

        # Update using base repository method
        updated_model = self.update(run_id, update_data)

        if updated_model:
            # Convert to domain object (need to fetch from session to get latest data)
            with self.connection_manager.session_scope() as session:
                fresh_model = session.get(self.model_class, run_id)
                if fresh_model:
                    return self._convert_to_domain_object(fresh_model)

        return None

    def update_processing_step(
        self, run_id: int, status: str, processing_step: str, **kwargs
    ) -> Optional["EtoRun"]:
        """Update processing status and current step atomically"""
        if run_id is None or not status:
            raise ValueError("run_id and status are required")

        update_data = {"status": status, "processing_step": processing_step, **kwargs}

        return self.update_status(run_id, status, **update_data)

    def mark_as_failed(
        self,
        run_id: int,
        error_message: str,
        error_type: str = None,
        error_details: Dict[str, Any] = None,
    ) -> Optional["EtoRun"]:
        """Mark run as failed with error details"""
        if run_id is None or not error_message:
            raise ValueError("run_id and error_message are required")

        update_data = {
            "error_message": error_message,
            "error_type": error_type,
            "error_details": error_details,
            "processing_step": None,  # Clear processing step on failure
        }

        return self.update_status(run_id, "failure", **update_data)

    def get_runs_by_status(
        self, status_list: List[str], limit: Optional[int] = None
    ) -> List["EtoRun"]:
        """Get runs matching any of the provided statuses"""
        if not status_list:
            return []

        try:
            with self.connection_manager.session_scope() as session:
                query = (
                    session.query(self.model_class)
                    .filter(self.model_class.status.in_(status_list))
                    .order_by(self.model_class.created_at.desc())
                )

                if limit is not None:
                    query = query.limit(limit)

                models = query.all()

                # Convert all models to domain objects
                return [self._convert_to_domain_object(model) for model in models]

        except SQLAlchemyError as e:
            logger.error(f"Error getting ETO runs by status list {status_list}: {e}")
            raise RepositoryError(f"Failed to get ETO runs by status list: {e}") from e

    def get_processing_statistics(self) -> Dict[str, Any]:
        """Get processing statistics by status"""
        try:
            with self.connection_manager.session_scope() as session:
                # Count by status
                status_counts = (
                    session.query(
                        self.model_class.status,
                        func.count(self.model_class.id).label("count"),
                    )
                    .group_by(self.model_class.status)
                    .all()
                )

                # Calculate average processing time for completed runs
                avg_processing_time = (
                    session.query(func.avg(self.model_class.processing_duration_ms))
                    .filter(self.model_class.processing_duration_ms.isnot(None))
                    .scalar()
                    or 0
                )

                # Get success rate
                total_completed = (
                    session.query(func.count(self.model_class.id))
                    .filter(self.model_class.status.in_(["success", "failure"]))
                    .scalar()
                    or 0
                )

                total_successful = (
                    session.query(func.count(self.model_class.id))
                    .filter(self.model_class.status == "success")
                    .scalar()
                    or 0
                )

                success_rate = (
                    (total_successful / total_completed * 100)
                    if total_completed > 0
                    else 0
                )

                # Build statistics dictionary
                stats = {
                    "status_counts": {status: count for status, count in status_counts},
                    "total_runs": sum(count for _, count in status_counts),
                    "avg_processing_time_ms": round(avg_processing_time, 2),
                    "success_rate_percent": round(success_rate, 2),
                    "total_completed": total_completed,
                    "total_successful": total_successful,
                }

                return stats

        except SQLAlchemyError as e:
            logger.error(f"Error getting processing statistics: {e}")
            raise RepositoryError(f"Failed to get processing statistics: {e}") from e
