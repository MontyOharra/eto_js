"""
Template Repository
Repository for PDF template CRUD operations with domain object conversion
"""
import logging
from typing import Optional, List, Dict, Any
from sqlalchemy.exc import SQLAlchemyError

from .base_repository import BaseRepository, RepositoryError
from ..models import PdfTemplateModel
from features.eto_processing.types import PdfTemplate
from ..connection import DatabaseConnectionManager

logger = logging.getLogger(__name__)


class TemplateRepository(BaseRepository[PdfTemplateModel]):
    """Repository for PDF template operations"""

    def __init__(self, connection_manager: DatabaseConnectionManager):
        super().__init__(connection_manager)

    @property
    def model_class(self):
        return PdfTemplateModel

    def _convert_to_domain_object(self, model: PdfTemplateModel) -> PdfTemplate:
        """Convert SQLAlchemy model to domain object"""
        if not model:
            return None

        return PdfTemplate(
            id=model.id,
            name=model.name,
            customer_name=model.customer_name,
            description=model.description,
            signature_objects=model.signature_objects,
            signature_object_count=model.signature_object_count,
            extraction_fields=model.extraction_fields,
            is_complete=model.is_complete,
            coverage_threshold=model.coverage_threshold,
            usage_count=model.usage_count,
            last_used_at=model.last_used_at,
            version=model.version,
            is_current_version=model.is_current_version,
            created_by=model.created_by,
            created_at=model.created_at,
            updated_at=model.updated_at,
            status=model.status
        )

    def _convert_to_domain_objects(self, models: List[PdfTemplateModel]) -> List[PdfTemplate]:
        """Convert list of SQLAlchemy models to domain objects"""
        return [self._convert_to_domain_object(model) for model in models if model]

    # === Core CRUD Operations (returning domain objects) ===

    def get_by_id(self, template_id: int) -> Optional[PdfTemplate]:
        """Get template by ID"""
        if template_id is None:
            return None

        try:
            with self.connection_manager.session_scope() as session:
                model = session.query(self.model_class).filter(
                    self.model_class.id == template_id
                ).first()
                return self._convert_to_domain_object(model)

        except SQLAlchemyError as e:
            logger.error(f"Error getting template by ID {template_id}: {e}")
            raise RepositoryError(f"Failed to get template by ID: {e}") from e

    def get_all(self, order_by: Optional[str] = None, desc: bool = False,
               limit: Optional[int] = None, offset: Optional[int] = None) -> List[PdfTemplate]:
        """Get all templates with optional sorting and pagination"""
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
                return self._convert_to_domain_objects(models)

        except SQLAlchemyError as e:
            logger.error(f"Error getting all templates: {e}")
            raise RepositoryError(f"Failed to get templates: {e}") from e

    def create(self, template_data: Dict[str, Any]) -> PdfTemplate:
        """Create a new template"""
        if not template_data:
            raise ValueError("Template data dictionary cannot be empty")

        try:
            with self.connection_manager.session_scope() as session:
                # Create new template instance
                template = self.model_class(**template_data)

                # Add to session and flush to get ID
                session.add(template)
                session.flush()

                # Refresh to get updated fields
                session.refresh(template)

                # Convert to domain object before session closes
                domain_template = self._convert_to_domain_object(template)

                logger.debug(f"Created template with ID: {template.id}")
                return domain_template

        except SQLAlchemyError as e:
            logger.error(f"Error creating template: {e}")
            raise RepositoryError(f"Failed to create template: {e}") from e
        except Exception as e:
            logger.error(f"Unexpected error creating template: {e}")
            raise RepositoryError(f"Unexpected error: {e}") from e

    def update(self, template_id: int, updates: Dict[str, Any]) -> Optional[PdfTemplate]:
        """Update an existing template by ID"""
        if template_id is None:
            raise ValueError("Template ID cannot be None")

        if not updates:
            raise ValueError("Update data cannot be empty")

        try:
            with self.connection_manager.session_scope() as session:
                # Get existing template
                template = session.query(self.model_class).filter(
                    self.model_class.id == template_id
                ).first()

                if not template:
                    logger.warning(f"Template with ID {template_id} not found")
                    return None

                # Update fields
                for key, value in updates.items():
                    if hasattr(template, key):
                        setattr(template, key, value)
                    else:
                        logger.warning(f"Ignoring unknown field '{key}' for template")

                # Flush to update in database
                session.flush()
                session.refresh(template)

                # Convert to domain object before session closes
                domain_template = self._convert_to_domain_object(template)

                logger.debug(f"Updated template with ID: {template_id}")
                return domain_template

        except SQLAlchemyError as e:
            logger.error(f"Error updating template {template_id}: {e}")
            raise RepositoryError(f"Failed to update template: {e}") from e

    def delete(self, template_id: int) -> bool:
        """Delete a template by ID"""
        if template_id is None:
            raise ValueError("Template ID cannot be None")

        try:
            with self.connection_manager.session_scope() as session:
                # Get existing template
                template = session.query(self.model_class).filter(
                    self.model_class.id == template_id
                ).first()

                if not template:
                    logger.warning(f"Template with ID {template_id} not found")
                    return False

                # Delete the template
                session.delete(template)

                logger.debug(f"Deleted template with ID: {template_id}")
                return True

        except SQLAlchemyError as e:
            logger.error(f"Error deleting template {template_id}: {e}")
            raise RepositoryError(f"Failed to delete template: {e}") from e