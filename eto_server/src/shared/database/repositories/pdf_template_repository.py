"""
PDF Template Repository
Repository for PDF template CRUD operations with domain object conversion
"""
import logging
from typing import Optional, List, Dict, Any
from sqlalchemy.exc import SQLAlchemyError

from shared.database.repositories import BaseRepository, RepositoryError
from shared.database.models import PdfTemplateModel
from shared.database.connection import DatabaseConnectionManager
from shared.domain import PdfTemplate


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
            customer_name=getattr(model, 'customer_name'),
            description=getattr(model, 'description'),
            signature_objects=getattr(model, 'signature_objects'),
            signature_object_count=getattr(model, 'signature_object_count'),
            extraction_fields=getattr(model, 'extraction_fields'),
            is_complete=getattr(model, 'is_complete'),
            coverage_threshold=getattr(model, 'coverage_threshold'),
            usage_count=getattr(model, 'usage_count'),
            last_used_at=getattr(model, 'last_used_at'),
            version=getattr(model, 'version'),
            is_current_version=getattr(model, 'is_current_version'),
            created_by=getattr(model, 'created_by'),
            created_at=getattr(model, 'created_at'),
            updated_at=getattr(model, 'updated_at'),
            status=getattr(model, 'status')
        )

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
            logger.error(f"Error getting PDF template by ID {template_id}: {e}")
            raise RepositoryError(f"Failed to get PDF template by ID: {e}") from e

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

    def create(self, template_data: Dict[str, Any]) -> PdfTemplate:
        """Create a new PDF template"""
        if not template_data:
            raise ValueError("PDF template data dictionary cannot be empty")

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

                logger.debug(f"Created PDF template with ID: {template.id}")
                return domain_template

        except SQLAlchemyError as e:
            logger.error(f"Error creating PDF template: {e}")
            raise RepositoryError(f"Failed to create PDF template: {e}") from e
        except Exception as e:
            logger.error(f"Unexpected error creating PDF template: {e}")
            raise RepositoryError(f"Unexpected error: {e}") from e

    def update(self, template_id: int, updates: Dict[str, Any]) -> Optional[PdfTemplate]:
        """Update an existing PDF template by ID"""
        if template_id is None:
            raise ValueError("PDF template ID cannot be None")

        if not updates:
            raise ValueError("Update data cannot be empty")

        try:
            with self.connection_manager.session_scope() as session:
                # Get existing template
                template = session.query(self.model_class).filter(
                    self.model_class.id == template_id
                ).first()

                if not template:
                    logger.warning(f"PDF template with ID {template_id} not found")
                    return None

                # Update fields
                for key, value in updates.items():
                    if hasattr(template, key):
                        setattr(template, key, value)
                    else:
                        logger.warning(f"Ignoring unknown field '{key}' for PDF template")

                # Flush to update in database
                session.flush()
                session.refresh(template)

                # Convert to domain object before session closes
                domain_template = self._convert_to_domain_object(template)

                logger.debug(f"Updated PDF template with ID: {template_id}")
                return domain_template

        except SQLAlchemyError as e:
            logger.error(f"Error updating PDF template {template_id}: {e}")
            raise RepositoryError(f"Failed to update PDF template: {e}") from e

    def delete(self, template_id: int) -> bool:
        """Delete a PDF template by ID"""
        if template_id is None:
            raise ValueError("PDF template ID cannot be None")

        try:
            with self.connection_manager.session_scope() as session:
                # Get existing template
                template = session.query(self.model_class).filter(
                    self.model_class.id == template_id
                ).first()

                if not template:
                    logger.warning(f"PDF template with ID {template_id} not found")
                    return False

                # Delete the template
                session.delete(template)

                logger.debug(f"Deleted PDF template with ID: {template_id}")
                return True

        except SQLAlchemyError as e:
            logger.error(f"Error deleting PDF template {template_id}: {e}")
            raise RepositoryError(f"Failed to delete PDF template: {e}") from e

    # === Specialized Query Methods ===

    def get_active_templates(self) -> List[PdfTemplate]:
        """Get all active PDF templates for matching"""
        try:
            with self.connection_manager.session_scope() as session:
                models = session.query(self.model_class).filter(
                    self.model_class.status == 'active',
                    self.model_class.is_complete == True
                ).order_by(self.model_class.last_used_at.desc()).all()

                return [self._convert_to_domain_object(model) for model in models]

        except SQLAlchemyError as e:
            logger.error(f"Error getting active PDF templates: {e}")
            raise RepositoryError(f"Failed to get active PDF templates: {e}") from e

    def get_by_customer_name(self, customer_name: str) -> List[PdfTemplate]:
        """Get all PDF templates for a specific customer"""
        if not customer_name:
            return []

        try:
            with self.connection_manager.session_scope() as session:
                models = session.query(self.model_class).filter(
                    self.model_class.customer_name == customer_name
                ).order_by(self.model_class.created_at.desc()).all()

                return [self._convert_to_domain_object(model) for model in models]

        except SQLAlchemyError as e:
            logger.error(f"Error getting PDF templates for customer {customer_name}: {e}")
            raise RepositoryError(f"Failed to get PDF templates for customer: {e}") from e

    def get_template_versions(self, base_template_id: int) -> List[PdfTemplate]:
        """Get all versions of a template"""
        try:
            with self.connection_manager.session_scope() as session:
                # Get both the original template and its versions
                models = session.query(self.model_class).filter(
                    (self.model_class.id == base_template_id) |
                    (self.model_class.parent_template_id == base_template_id)
                ).order_by(self.model_class.version.desc()).all()

                return [self._convert_to_domain_object(model) for model in models]

        except SQLAlchemyError as e:
            logger.error(f"Error getting versions for PDF template {base_template_id}: {e}")
            raise RepositoryError(f"Failed to get PDF template versions: {e}") from e

    def get_next_version_number(self, base_template_id: int) -> int:
        """Get the next version number for a template"""
        try:
            with self.connection_manager.session_scope() as session:
                max_version = session.query(self.model_class.version).filter(
                    (self.model_class.id == base_template_id) |
                    (self.model_class.parent_template_id == base_template_id)
                ).order_by(self.model_class.version.desc()).first()

                return (max_version[0] + 1) if max_version else 1

        except SQLAlchemyError as e:
            logger.error(f"Error getting next version number for PDF template {base_template_id}: {e}")
            raise RepositoryError(f"Failed to get next version number: {e}") from e

    def mark_versions_as_not_current(self, base_template_id: int) -> None:
        """Mark all versions of a template as not current"""
        try:
            with self.connection_manager.session_scope() as session:
                session.query(self.model_class).filter(
                    (self.model_class.id == base_template_id) |
                    (self.model_class.parent_template_id == base_template_id)
                ).update({self.model_class.is_current_version: False})

        except SQLAlchemyError as e:
            logger.error(f"Error marking versions as not current for PDF template {base_template_id}: {e}")
            raise RepositoryError(f"Failed to mark versions as not current: {e}") from e

    def increment_usage_count(self, template_id: int) -> None:
        """Increment the usage count for a template"""
        try:
            with self.connection_manager.session_scope() as session:
                from datetime import datetime
                session.query(self.model_class).filter(
                    self.model_class.id == template_id
                ).update({
                    self.model_class.usage_count: self.model_class.usage_count + 1,
                    self.model_class.last_used_at: datetime.utcnow()
                })

        except SQLAlchemyError as e:
            logger.error(f"Error incrementing usage count for PDF template {template_id}: {e}")
            raise RepositoryError(f"Failed to increment usage count: {e}") from e