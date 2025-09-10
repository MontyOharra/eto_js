"""
Template Repository
Data access layer for PdfTemplate model operations
"""
import logging
from typing import Optional, List, Dict, Any
from datetime import datetime, timezone
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy import func, desc
from .base_repository import BaseRepository, RepositoryError
from ..models import PdfTemplate


logger = logging.getLogger(__name__)


class TemplateRepository(BaseRepository[PdfTemplate]):
    """Repository for PdfTemplate model operations"""
    
    @property
    def model_class(self):
        return PdfTemplate
    
    def get_active_templates(self) -> List[PdfTemplate]:
        """Get all active templates"""
        return self.get_by_status('active')
    
    def get_by_customer(self, customer_name: str) -> List[PdfTemplate]:
        """Get templates by customer name"""
        if not customer_name:
            return []
        
        return self.get_by_field('customer_name', customer_name)
    
    def get_by_status(self, status: str, limit: Optional[int] = None) -> List[PdfTemplate]:
        """Get templates by status (active, archived, draft)"""
        if not status:
            return []
        
        try:
            with self.connection_manager.session_scope() as session:
                query = session.query(self.model_class).filter(
                    self.model_class.status == status
                ).order_by(self.model_class.last_used_at.desc().nullslast(), 
                           self.model_class.created_at.desc())
                
                if limit is not None:
                    query = query.limit(limit)
                
                return query.all()
                
        except SQLAlchemyError as e:
            logger.error(f"Error getting templates by status {status}: {e}")
            raise RepositoryError(f"Failed to get templates by status: {e}") from e
    
    def get_current_versions(self) -> List[PdfTemplate]:
        """Get only current version templates"""
        try:
            with self.connection_manager.session_scope() as session:
                return session.query(self.model_class).filter(
                    self.model_class.is_current_version == True
                ).order_by(self.model_class.last_used_at.desc().nullslast(),
                           self.model_class.created_at.desc()).all()
                
        except SQLAlchemyError as e:
            logger.error(f"Error getting current version templates: {e}")
            raise RepositoryError(f"Failed to get current version templates: {e}") from e
    
    def get_most_used(self, limit: int = 10) -> List[PdfTemplate]:
        """Get most frequently used templates"""
        try:
            with self.connection_manager.session_scope() as session:
                return session.query(self.model_class).filter(
                    self.model_class.status == 'active'
                ).order_by(self.model_class.usage_count.desc().nullslast(),
                           self.model_class.last_used_at.desc().nullslast()).limit(limit).all()
                
        except SQLAlchemyError as e:
            logger.error(f"Error getting most used templates: {e}")
            raise RepositoryError(f"Failed to get most used templates: {e}") from e
    
    def update_usage_stats(self, template_id: int, last_used_at: datetime) -> Optional[PdfTemplate]:
        """Update usage count and last used timestamp"""
        if template_id is None:
            raise ValueError("template_id cannot be None")
        
        if last_used_at is None:
            last_used_at = datetime.now(timezone.utc)
        
        try:
            # Get current template to increment usage count
            current_template = self.get_by_id(template_id)
            
            if not current_template:
                logger.warning(f"Template with ID {template_id} not found")
                return None
            
            # Increment usage count
            new_usage_count = (current_template.usage_count or 0) + 1
            
            update_data = {
                'usage_count': new_usage_count,
                'last_used_at': last_used_at
            }
            
            updated_template = self.update(template_id, update_data)
            if updated_template:
                logger.debug(f"Updated usage stats for template {template_id}: count={new_usage_count}")
            
            return updated_template
            
        except Exception as e:
            logger.error(f"Error updating usage stats for template {template_id}: {e}")
            raise RepositoryError(f"Failed to update usage stats: {e}") from e
    
    def get_template_statistics(self) -> Dict[str, Any]:
        """Get template usage statistics"""
        try:
            with self.connection_manager.session_scope() as session:
                # Count by status
                status_counts = session.query(
                    self.model_class.status,
                    func.count(self.model_class.id).label('count')
                ).group_by(self.model_class.status).all()
                
                # Get completion statistics
                total_templates = session.query(func.count(self.model_class.id)).scalar() or 0
                complete_templates = session.query(func.count(self.model_class.id)).filter(
                    self.model_class.is_complete == True
                ).scalar() or 0
                
                # Get usage statistics
                total_usage = session.query(func.sum(self.model_class.usage_count)).scalar() or 0
                avg_usage = session.query(func.avg(self.model_class.usage_count)).filter(
                    self.model_class.usage_count > 0
                ).scalar() or 0
                
                # Get most used template
                most_used_template = session.query(self.model_class).order_by(
                    self.model_class.usage_count.desc().nullslast()
                ).first()
                
                # Get current version statistics
                current_versions = session.query(func.count(self.model_class.id)).filter(
                    self.model_class.is_current_version == True
                ).scalar() or 0
                
                # Build statistics dictionary
                stats = {
                    'status_counts': {status: count for status, count in status_counts},
                    'total_templates': total_templates,
                    'complete_templates': complete_templates,
                    'completion_rate_percent': round((complete_templates / total_templates * 100) if total_templates > 0 else 0, 2),
                    'current_versions': current_versions,
                    'total_usage': total_usage,
                    'avg_usage_per_template': round(avg_usage, 2),
                    'most_used_template': {
                        'id': most_used_template.id if most_used_template else None,
                        'name': most_used_template.name if most_used_template else None,
                        'usage_count': most_used_template.usage_count if most_used_template else 0
                    } if most_used_template else None
                }
                
                return stats
                
        except SQLAlchemyError as e:
            logger.error(f"Error getting template statistics: {e}")
            raise RepositoryError(f"Failed to get template statistics: {e}") from e