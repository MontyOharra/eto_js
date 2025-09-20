"""
PDF Template Repository
Repository for PDF template CRUD operations with domain object conversion
"""
import logging
from typing import Optional, List, Dict, Any
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy import func

from shared.database.repositories import BaseRepository
from shared.exceptions import RepositoryError, ObjectNotFoundError, ValidationError
from shared.database.models import PdfTemplateModel, PdfTemplateVersionModel
from shared.database.connection import DatabaseConnectionManager
from shared.domain import PdfTemplate, PdfTemplateVersion


logger = logging.getLogger(__name__)


class PdfTemplateRepository(BaseRepository[PdfTemplateModel]):
    """Repository for PDF template operations"""

    def __init__(self, connection_manager: DatabaseConnectionManager):
        super().__init__(connection_manager)

    @property
    def model_class(self):
        return PdfTemplateModel

    def _convert_to_domain_object(self, model: PdfTemplateModel) -> PdfTemplate:
        """Convert SQLAlchemy model to domain object"""

        return PdfTemplate(
            id=getattr(model, 'id'),
            name=getattr(model, 'name'),
            description=getattr(model, 'description'),
            pdf_id=getattr(model, 'pdf_id'),
            status=getattr(model, 'status'),
            current_version_id=getattr(model, 'current_version_id'),
            created_at=getattr(model, 'created_at'),
            updated_at=getattr(model, 'updated_at')
        )

    def _convert_version_to_domain_object(self, version_model: PdfTemplateVersionModel) -> PdfTemplateVersion:
        """Convert SQLAlchemy version model to domain object"""
        return PdfTemplateVersion(
            id=getattr(version_model, 'id'),
            pdf_template_id=getattr(version_model, 'pdf_template_id'),
            version=getattr(version_model, 'version'),
            signature_objects=getattr(version_model, 'signature_objects'),
            signature_object_count=getattr(version_model, 'signature_object_count'),
            extraction_fields=getattr(version_model, 'extraction_fields'),
            usage_count=getattr(version_model, 'usage_count'),
            last_used_at=getattr(version_model, 'last_used_at'),
            created_at=getattr(version_model, 'created_at')
        )

    # === Core CRUD Operations (returning domain objects) ===

    def create(self, 
        name : str,
        description : Optional[str],
        pdf_id : int,
    ) -> PdfTemplate:
        """Create a new PDF template"""

        try:
            with self.connection_manager.session_scope() as session:
                # Create new template instance
                model = self.model_class(
                    name=name,
                    description=description,
                    pdf_id=pdf_id
                )

                # Add to session and flush to get ID
                session.add(model)
                session.flush()

                # Refresh to get updated fields
                session.refresh(model)

                logger.debug(f"Created PDF template with ID: {model.id}")
                return self._convert_to_domain_object(model)

        except SQLAlchemyError as e:
            logger.error(f"Error creating PDF template: {e}")
            raise RepositoryError(f"Failed to create PDF template: {e}") from e
        
    def get_next_version_number(self, template_id: int) -> int:
        """Get the next version number for a template by querying the versions table"""
        try:
            with self.connection_manager.session_scope() as session:
                # Query the versions table to get the maximum version number for this template
                max_version = session.query(func.max(PdfTemplateVersionModel.version)).filter(
                    PdfTemplateVersionModel.pdf_template_id == template_id
                ).scalar()

                # Return next version number (max + 1, or 1 if no versions exist)
                return (max_version + 1) if max_version is not None else 1

        except SQLAlchemyError as e:
            logger.error(f"Error getting next version number for template {template_id}: {e}")
            raise RepositoryError(f"Failed to get next version number: {e}") from e
        
    def set_current_version_id(self, id: int, version_id: int) -> PdfTemplate:
        """Set the current version ID for a template"""

        try:
            with self.connection_manager.session_scope() as session:
                # Get existing template
                model = session.get(self.model_class, id)

                if not model:
                    raise ObjectNotFoundError("PdfTemplate", id)

                # Update current version ID
                model.current_version_id = version_id
                session.flush()
                session.refresh(model)

                logger.debug(f"Updated PDF template with ID: {id}")
                return self._convert_to_domain_object(model)
        except ObjectNotFoundError:
            raise
        except SQLAlchemyError as e:
            logger.error(f"Error updating PDF template {id}: {e}")
            raise RepositoryError(f"Failed to update PDF template: {e}") from e

    def get_all(self, order_by: Optional[str] = None, desc: bool = False,
               limit: Optional[int] = None, offset: Optional[int] = None) -> List[PdfTemplate]:
        """Get all PDF templates with optional sorting and pagination"""
        try:
            with self.connection_manager.session_scope() as session:
                query = session.query(self.model_class)

                # Apply sorting if specified
                if order_by:
                    if hasattr(self.model_class, order_by):
                        column = getattr(self.model_class, order_by)
                        query = query.order_by(column.desc() if desc else column)
                    else:
                        logger.warning(f"Field '{order_by}' does not exist on {self.model_class.__name__}, skipping sort")

                if offset is not None:
                    query = query.offset(offset)

                if limit is not None:
                    query = query.limit(limit)

                models = query.all()
                return [self._convert_to_domain_object(model) for model in models]

        except SQLAlchemyError as e:
            logger.error(f"Error getting all PDF templates: {e}")
            raise RepositoryError(f"Failed to get PDF templates: {e}") from e

    # === Specialized Query Methods ===

    def get_active_templates(self) -> List[PdfTemplate]:
        """Get all active PDF templates for matching"""
        try:
            with self.connection_manager.session_scope() as session:
                models = session.query(self.model_class).filter(
                    self.model_class.status == 'active'
                ).all()

                return [self._convert_to_domain_object(model) for model in models]

        except SQLAlchemyError as e:
            logger.error(f"Error getting active PDF templates: {e}")
            raise RepositoryError(f"Failed to get active PDF templates: {e}") from e
