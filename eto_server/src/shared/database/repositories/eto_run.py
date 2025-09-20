"""
ETO Run Repository
Data access layer for EtoRunModel model operations
"""

import json
import logging
from typing import Optional, List, Dict, Any
from datetime import datetime, timezone
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy import func, case

from shared.database.repositories.base import BaseRepository
from shared.exceptions import RepositoryError, ObjectNotFoundError, ValidationError
from shared.database.models import EtoRunModel
from shared.domain import EtoRun, EtoRunStatus, EtoProcessingStep, EtoErrorType


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
    
    def create(self, eto_run_data: Dict[str, Any]) -> EtoRun:
        """Create a new ETO run record"""
        if not eto_run_data:
            raise ValueError("ETO run data dictionary cannot be empty")
            
        try:
            with self.connection_manager.session_scope() as session:
                # Create new model
                model = self.model_class(**eto_run_data)
                
                # Add to session and flush to get ID
                session.add(model)
                session.flush()
                
                # Refresh to get updated fields
                session.refresh(model)
                
                # Convert to domain object before session closes
                domain_run = self._convert_to_domain_object(model)
                return domain_run
                
        except SQLAlchemyError as e:  
            logger.error(f"Error creating ETO run: {e}")
            raise RepositoryError(f"Failed to create ETO run: {e}") from e

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

    def get_by_pdf_id(self, pdf_file_id: int) -> List[EtoRun]: 
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

    def get_by_template_id(self, template_id: int) -> List[EtoRun]:
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

    def update_status(self, id: int, status: EtoRunStatus) -> Optional[EtoRun]:
        """Update run status and related fields"""
        if id is None or not status:
            raise ValueError("run_id and status are required")

        try:
            with self.connection_manager.session_scope() as session:
                model = session.get(self.model_class, id)
                
                if not model:
                    return None
                
                current_time = datetime.now(timezone.utc)
                
                setattr(model, "status", status)
                setattr(model, "updated_at", current_time)
                
                if status == "processing":
                    setattr(model, "started_at", current_time)
                    setattr(model, "processing_step", "template_matching")
                elif status in ["needs_template", "failed", "success"]:
                    processing_time = 1000 * (getattr(model, "started_at") - current_time)
                    setattr(model, "completed_at", current_time)
                    setattr(model, "processing_duration_ms", processing_time)
                    setattr(model, "processing_step", None)
                elif status == "not_started":
                    setattr(model, "processing_step", None)
                    setattr(model, "error_type", None)
                    setattr(model, "error_message", None)
                    setattr(model, "error_details", None)
                    setattr(model, "matched_template_id", None)
                    setattr(model, "matched_template_version", None)
                    setattr(model, "extracted_data", None)
                    setattr(model, "transformation_audit", None)
                    setattr(model, "target_data", None)
                    setattr(model, "failed_pipeline_step_id", None)
                    setattr(model, "step_execution_log", None)
                    setattr(model, "started_at", None)
                    setattr(model, "completed_at", None)
                    setattr(model, "processing_duration_ms", None)
                    setattr(model, "order_id", None)
        
                return self._convert_to_domain_object(model)
            
        except SQLAlchemyError as e:
            logger.error(f"Error setting status for eto_run {id}: {e}")
            raise RepositoryError(f"Failed to set status: {e}") from e        

    def update_processing_step(self, id: int, processing_step: EtoProcessingStep) -> Optional[EtoRun]:
        try:
            with self.connection_manager.session_scope() as session:
                model = session.get(self.model_class, id)
                
                if not model:
                    return None
                if getattr(model, "status") != "processing":
                    raise RepositoryError(f"Cannot update processing_step for eto_run: {id}. Status must be 'processing'")         

                setattr(model, "processing_step", processing_step)
                
                return self._convert_to_domain_object(model)
            
        except SQLAlchemyError as e:
            logger.error(f"Erorr setting processing step for eto_run {id}: {e}")
            raise RepositoryError(f"Failed to set processing step: {e}") from e

    def set_template_match(self, id: int, template_id : int, template_version: int) -> Optional[EtoRun]:
        try:
            with self.connection_manager.session_scope() as session:
                model = session.get(self.model_class, id)

                if not model:
                    return None

                setattr(model, "matched_template_id", template_id)
                setattr(model, "matched_template_version", template_version)
                setattr(model, "processing_step", "extracting_data")
                
                return self._convert_to_domain_object(model)
            
        except SQLAlchemyError as e:
            logger.error(f"Error setting template match for eto_run {id}: {e}")
            raise RepositoryError(f"Failed to set template match: {e}") from e     
            
    def set_extracted_data(self, id: int, data_extracted: Dict[str, Any]) -> Optional[EtoRun]:
        try:
            with self.connection_manager.session_scope() as session:
                model = session.get(self.model_class, id)

                if not model:
                    return None

                setattr(model, "matched_template_id", id)
                setattr(model, "matched_template_version", id)
                
                return self._convert_to_domain_object(model)
            
        except SQLAlchemyError as e:
            logger.error(f"Error setting template match for eto_run {id}: {e}")
            raise RepositoryError(f"Failed to set template match: {e}") from e     

    def mark_as_failed(
        self,
        id: int,
        error_message: str,
        error_type: EtoErrorType,
        error_details: Dict[str, Any],
    ) -> Optional[EtoRun]:
        """Mark run as failed with error details"""
        if id is None or not error_message:
            raise ValueError("run_id and error_message are required")

        # Convert error_details dict to JSON string for database storage
        error_details_json = json.dumps(error_details) if error_details else None

        update_data = {
            "error_message": error_message,
            "error_type": error_type,
            "error_details": error_details_json,
            "processing_step": None,  # Clear processing step on failure
        }

        return self.update_status(id, "failure", **update_data)

    def get_with_filters(
        self,
        status: Optional[str] = None,
        email_id: Optional[int] = None,
        template_id: Optional[int] = None,
        has_errors: Optional[bool] = None,
        date_from: Optional[datetime] = None,
        date_to: Optional[datetime] = None,
        page: int = 1,
        limit: int = 20,
        order_by: str = "created_at",
        desc: bool = True
    ) -> Dict[str, Any]:
        """Get ETO runs with filtering and pagination"""
        try:
            with self.connection_manager.session_scope() as session:
                # Base query
                query = session.query(self.model_class)

                # Apply filters
                if status:
                    query = query.filter(self.model_class.status == status)

                if email_id:
                    query = query.filter(self.model_class.email_id == email_id)

                if template_id:
                    query = query.filter(self.model_class.matched_template_id == template_id)

                if has_errors is not None:
                    if has_errors:
                        query = query.filter(self.model_class.error_message.isnot(None))
                    else:
                        query = query.filter(self.model_class.error_message.is_(None))

                if date_from:
                    query = query.filter(self.model_class.created_at >= date_from)

                if date_to:
                    query = query.filter(self.model_class.created_at <= date_to)

                # Get total count before pagination
                total_count = query.count()

                # Apply sorting
                if hasattr(self.model_class, order_by):
                    column = getattr(self.model_class, order_by)
                    query = query.order_by(column.desc() if desc else column)

                # Apply pagination
                offset = (page - 1) * limit
                paginated_query = query.offset(offset).limit(limit)

                # Execute query and convert to domain objects
                models = paginated_query.all()
                runs = [self._convert_to_domain_object(model) for model in models]

                # Calculate pagination metadata
                total_pages = (total_count + limit - 1) // limit

                return {
                    "runs": runs,
                    "total": total_count,
                    "page": page,
                    "limit": limit,
                    "total_pages": total_pages
                }

        except SQLAlchemyError as e:
            logger.error(f"Error getting ETO runs with filters: {e}")
            raise RepositoryError(f"Failed to get ETO runs with filters: {e}") from e

    def get_statistics(self) -> Dict[str, Any]:
        """Get processing statistics for ETO runs"""
        try:
            with self.connection_manager.session_scope() as session:
                # Basic counts by status
                status_counts = (
                    session.query(
                        self.model_class.status,
                        func.count(self.model_class.id).label('count')
                    )
                    .group_by(self.model_class.status)
                    .all()
                )

                # Total runs
                total_runs = session.query(self.model_class).count()

                # Success rate calculation
                successful_runs = (
                    session.query(self.model_class)
                    .filter(self.model_class.status == 'success')
                    .count()
                )
                success_rate = successful_runs / total_runs if total_runs > 0 else 0.0

                # Average processing time for completed runs
                avg_processing_time = (
                    session.query(func.avg(self.model_class.processing_duration_ms))
                    .filter(self.model_class.processing_duration_ms.isnot(None))
                    .scalar()
                )

                # Recent activity counts (last 24 hours)
                from datetime import timedelta
                last_24h = datetime.now(timezone.utc) - timedelta(hours=24)
                last_24h_runs = (
                    session.query(self.model_class)
                    .filter(self.model_class.created_at >= last_24h)
                    .count()
                )

                # Last successful and failed runs
                last_successful_run = (
                    session.query(self.model_class.completed_at)
                    .filter(self.model_class.status == 'success')
                    .order_by(self.model_class.completed_at.desc())
                    .first()
                )

                last_failed_run = (
                    session.query(self.model_class.completed_at)
                    .filter(self.model_class.status == 'failure')
                    .order_by(self.model_class.completed_at.desc())
                    .first()
                )

                return {
                    "total_runs": total_runs,
                    "status_counts": [{"status": status, "count": count} for status, count in status_counts],
                    "success_rate": success_rate,
                    "average_processing_time_ms": int(avg_processing_time) if avg_processing_time else None,
                    "last_24h_runs": last_24h_runs,
                    "last_successful_run": last_successful_run[0] if last_successful_run else None,
                    "last_failed_run": last_failed_run[0] if last_failed_run else None
                }

        except SQLAlchemyError as e:
            logger.error(f"Error getting ETO run statistics: {e}")
            raise RepositoryError(f"Failed to get ETO run statistics: {e}") from e

    def reset_failed_runs_for_reprocessing(self) -> Dict[str, int]:
        """
        Bulk reset failed and needs_template runs to not_started status

        Returns:
            Dictionary with counts: {
                'failure_count': int,
                'needs_template_count': int,
                'total_reset': int
            }
        """
        try:
            with self.connection_manager.get_session() as session:
                # Get counts first for reporting
                failure_count = session.query(self.model_class).filter(
                    self.model_class.status == 'failure'
                ).count()

                needs_template_count = session.query(self.model_class).filter(
                    self.model_class.status == 'needs_template'
                ).count()

                total_eligible = failure_count + needs_template_count

                if total_eligible == 0:
                    return {
                        'failure_count': 0,
                        'needs_template_count': 0,
                        'total_reset': 0
                    }

                # Bulk update - reset all processing-related fields
                update_count = session.query(self.model_class).filter(
                    self.model_class.status.in_(['failure', 'needs_template'])
                ).update({
                    # Status & Processing State
                    self.model_class.status: 'not_started',
                    self.model_class.processing_step: None,

                    # Error Tracking
                    self.model_class.error_type: None,
                    self.model_class.error_message: None,
                    self.model_class.error_details: None,

                    # Template Matching Results
                    self.model_class.matched_template_id: None,
                    self.model_class.matched_template_version: None,
                    # Data Processing Results
                    self.model_class.extracted_data: None,
                    self.model_class.transformation_audit: None,
                    self.model_class.target_data: None,

                    # Pipeline Execution Tracking
                    self.model_class.failed_pipeline_step_id: None,
                    self.model_class.step_execution_log: None,

                    # Processing Timeline
                    self.model_class.started_at: None,
                    self.model_class.completed_at: None,
                    self.model_class.processing_duration_ms: None,

                    # Order Integration
                    self.model_class.order_id: None,

                    # Updated timestamp will be set automatically by the model
                }, synchronize_session=False)

                session.commit()

                logger.info(f"Reset {update_count} ETO runs for reprocessing (failure: {failure_count}, needs_template: {needs_template_count})")

                return {
                    'failure_count': failure_count,
                    'needs_template_count': needs_template_count,
                    'total_reset': update_count
                }

        except SQLAlchemyError as e:
            logger.error(f"Error resetting ETO runs for reprocessing: {e}")
            raise RepositoryError(f"Failed to reset ETO runs for reprocessing: {e}") from e
