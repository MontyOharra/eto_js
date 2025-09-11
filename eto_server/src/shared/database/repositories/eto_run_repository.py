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


logger = logging.getLogger(__name__)


class EtoRunRepository(BaseRepository[EtoRunModel]):
    """Repository for EtoRunModel model operations"""
    
    @property
    def model_class(self):
        return EtoRunModel
    
    def get_by_status(self, status: str, limit: Optional[int] = None) -> List[EtoRunModel]:
        """Get ETO runs by status"""
        if not status:
            return []
        
        try:
            with self.connection_manager.session_scope() as session:
                query = session.query(self.model_class).filter(
                    self.model_class.status == status
                ).order_by(self.model_class.created_at.desc())
                
                if limit is not None:
                    query = query.limit(limit)
                
                return query.all()
                
        except SQLAlchemyError as e:
            logger.error(f"Error getting ETO runs by status {status}: {e}")
            raise RepositoryError(f"Failed to get ETO runs by status: {e}") from e
    
    def get_by_email_id(self, email_id: int) -> List[EtoRunModel]:
        """Get all ETO runs for a specific email"""
        if email_id is None:
            return []
        
        return self.get_by_field('email_id', email_id)
    
    def get_by_pdf_id(self, pdf_file_id: int) -> List[EtoRunModel]:
        """Get all ETO runs for a specific PDF file"""
        if pdf_file_id is None:
            return []
        
        return self.get_by_field('pdf_file_id', pdf_file_id)
    
    def get_by_template_id(self, template_id: int) -> List[EtoRunModel]:
        """Get all ETO runs that used a specific template"""
        if template_id is None:
            return []
        
        return self.get_by_field('matched_template_id', template_id)
    
    def get_pending_runs(self, limit: Optional[int] = None) -> List[EtoRunModel]:
        """Get runs with status 'not_started'"""
        return self.get_by_status('not_started', limit)
    
    def get_processing_runs(self) -> List[EtoRunModel]:
        """Get runs currently being processed"""
        return self.get_by_status('processing')
    
    def get_failed_runs(self, limit: Optional[int] = None) -> List[EtoRunModel]:
        """Get runs with status 'failure'"""
        return self.get_by_status('failure', limit)
    
    def get_successful_runs(self, limit: Optional[int] = None) -> List[EtoRunModel]:
        """Get runs with status 'success'"""
        return self.get_by_status('success', limit)
    
    def get_runs_needing_templates(self, limit: Optional[int] = None) -> List[EtoRunModel]:
        """Get runs with status 'needs_template'"""
        return self.get_by_status('needs_template', limit)
    
    def update_status(self, run_id: int, status: str, **kwargs) -> Optional[EtoRunModel]:
        """Update run status and related fields"""
        if run_id is None or not status:
            raise ValueError("run_id and status are required")
        
        # Build update data with status and any additional fields
        update_data = {'status': status, **kwargs}
        
        # Add automatic timestamp updates based on status
        current_time = datetime.now(timezone.utc)
        if status == 'processing' and 'started_at' not in update_data:
            update_data['started_at'] = current_time
        elif status in ['success', 'failure', 'skipped'] and 'completed_at' not in update_data:
            update_data['completed_at'] = current_time
            
            # Calculate processing duration if we have started_at
            existing_run = self.get_by_id(run_id)
            if existing_run and existing_run.started_at is not None and 'processing_duration_ms' not in update_data:
                duration = current_time - existing_run.started_at
                update_data['processing_duration_ms'] = int(duration.total_seconds() * 1000)
        
        return self.update(run_id, update_data)
    
    def get_processing_statistics(self) -> Dict[str, Any]:
        """Get processing statistics by status"""
        try:
            with self.connection_manager.session_scope() as session:
                # Count by status
                status_counts = session.query(
                    self.model_class.status,
                    func.count(self.model_class.id).label('count')
                ).group_by(self.model_class.status).all()
                
                # Calculate average processing time for completed runs
                avg_processing_time = session.query(
                    func.avg(self.model_class.processing_duration_ms)
                ).filter(
                    self.model_class.processing_duration_ms.isnot(None)
                ).scalar() or 0
                
                # Get success rate
                total_completed = session.query(func.count(self.model_class.id)).filter(
                    self.model_class.status.in_(['success', 'failure'])
                ).scalar() or 0
                
                total_successful = session.query(func.count(self.model_class.id)).filter(
                    self.model_class.status == 'success'
                ).scalar() or 0
                
                success_rate = (total_successful / total_completed * 100) if total_completed > 0 else 0
                
                # Build statistics dictionary
                stats = {
                    'status_counts': {status: count for status, count in status_counts},
                    'total_runs': sum(count for _, count in status_counts),
                    'avg_processing_time_ms': round(avg_processing_time, 2),
                    'success_rate_percent': round(success_rate, 2),
                    'total_completed': total_completed,
                    'total_successful': total_successful
                }
                
                return stats
                
        except SQLAlchemyError as e:
            logger.error(f"Error getting processing statistics: {e}")
            raise RepositoryError(f"Failed to get processing statistics: {e}") from e