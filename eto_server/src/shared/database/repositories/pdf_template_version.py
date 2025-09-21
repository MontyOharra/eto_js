"""
PDF Template Version Repository
Repository for PDF template version CRUD operations with Pydantic model conversion
"""

import json
import logging
from typing import Optional, List
from sqlalchemy.exc import SQLAlchemyError
from datetime import datetime, timezone

from shared.database.repositories import BaseRepository
from shared.exceptions import RepositoryError, ObjectNotFoundError
from shared.database.models import PdfTemplateVersionModel
from shared.database.connection import DatabaseConnectionManager
from shared.models import PdfTemplateVersion, PdfTemplateVersionCreate

logger = logging.getLogger(__name__)


class PdfTemplateVersionRepository(BaseRepository[PdfTemplateVersionModel]):
    """Repository for PDF template versions"""
    
    def __init__(self, connection_manager: DatabaseConnectionManager):
        super().__init__(connection_manager)
        
    @property
    def model_class(self):
        return PdfTemplateVersionModel
    
    def _convert_to_domain_object(self, model: PdfTemplateVersionModel) -> PdfTemplateVersion:
        """Convert SQLAlchemy model to Pydantic domain object with JSON parsing"""
        return PdfTemplateVersion.from_db_model(model)
        
    def create(self, version_create: PdfTemplateVersionCreate) -> PdfTemplateVersion:
        """Create a new PDF template version from create model"""
        try:
            with self.connection_manager.session_scope() as session:
                # Calculate next version number for this template
                next_version_number = self._get_next_version_number(session, version_create.pdf_template_id)
                
                # Serialize objects to JSON for database storage
                version_data = version_create.model_dump_for_db()
                
                model = self.model_class(
                    version_num=next_version_number,
                    **version_data
                )

                # Add to session and flush to get ID
                session.add(model)
                session.flush()

                # Refresh to get updated fields
                session.refresh(model)

                logger.debug(f"Created PDF template version with ID: {model.id}")
                return self._convert_to_domain_object(model)

        except SQLAlchemyError as e:
            logger.error(f"Error creating PDF template version: {e}")
            raise RepositoryError(f"Failed to create PDF template version: {e}") from e

    def get_by_id(self, version_id: int) -> Optional[PdfTemplateVersion]:
        """Get PDF template version by ID"""
        try:
            with self.connection_manager.session_scope() as session:
                model = session.get(self.model_class, version_id)
                if not model:
                    return None
                return self._convert_to_domain_object(model)
        except SQLAlchemyError as e:
            logger.error(f"Error getting PDF template version {version_id}: {e}")
            raise RepositoryError(f"Failed to get PDF template version: {e}") from e
    
    def get_by_template_id(self, template_id: int) -> List[PdfTemplateVersion]:
        """Get all versions for a template"""
        try:
            with self.connection_manager.session_scope() as session:
                models = session.query(self.model_class).filter(
                    self.model_class.pdf_template_id == template_id
                ).order_by(self.model_class.version_num.desc()).all()

                return [self._convert_to_domain_object(model) for model in models]

        except SQLAlchemyError as e:
            logger.error(f"Error getting template versions for template {template_id}: {e}")
            raise RepositoryError(f"Failed to get template versions: {e}") from e

    def _get_next_version_number(self, session, template_id: int) -> int:
        """
        Get the next version number for a template (internal method)
        
        Args:
            session: Active SQLAlchemy session
            template_id: ID of the template
            
        Returns:
            Next version number (max existing version + 1, or 1 if no versions)
        """
        try:
            # Get all versions for this template
            with self.connection_manager.session_scope() as session:
              versions = session.query(self.model_class).filter(
                  self.model_class.pdf_template_id == template_id
              ).all()
              
              if not versions:
                  return 1
              
              # Find the maximum version number
              max_version = max(version.version_num for version in versions)
              return max_version + 1
            
        except SQLAlchemyError as e:
            logger.error(f"Error calculating next version number for template {template_id}: {e}")
            raise RepositoryError(f"Failed to calculate next version number: {e}") from e

    def increment_usage_count(self, version_id: int) -> None:
        """Increment usage count for a template version"""
        try:
            with self.connection_manager.session_scope() as session:
                model = session.get(self.model_class, version_id)
                if model:
                    model.usage_count += 1
                    model.last_used_at = datetime.now(timezone.utc)

        except SQLAlchemyError as e:
            logger.error(f"Error incrementing usage count for version {version_id}: {e}")
            raise RepositoryError(f"Failed to increment usage count: {e}") from e