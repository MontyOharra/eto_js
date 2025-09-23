"""
PDF Template Repository
Repository for PDF template CRUD operations with Pydantic model conversion
"""
import logging
from typing import Optional, List, Dict, Any
from sqlalchemy.exc import SQLAlchemyError
from datetime import datetime, timezone

from shared.database.repositories import BaseRepository
from shared.exceptions import RepositoryError, ObjectNotFoundError, ValidationError
from shared.database.models import PdfTemplateModel
from shared.database.connection import DatabaseConnectionManager
from shared.models import PdfTemplate, PdfTemplateCreate, PdfTemplateUpdate
from shared.utils import DateTimeUtils


logger = logging.getLogger(__name__)


class PdfTemplateRepository(BaseRepository[PdfTemplateModel]):
    """Repository for PDF template operations"""

    def __init__(self, connection_manager: DatabaseConnectionManager):
        super().__init__(connection_manager)

    @property
    def model_class(self):
        return PdfTemplateModel

    def _convert_to_domain_object(self, model: PdfTemplateModel) -> PdfTemplate:
        """Convert SQLAlchemy model to Pydantic domain object"""
        # Use Pydantic's automatic conversion from SQLAlchemy model
        return PdfTemplate.model_validate(model)

    # === Core CRUD Operations (returning domain objects) ===

    def create(self, template_create: PdfTemplateCreate) -> PdfTemplate:
        """Create a new PDF template from create model"""
        try:
            with self.connection_manager.session_scope() as session:
                # Convert create model to SQLAlchemy model (exclude fields not in DB)
                model_data = template_create.model_dump_for_db()
                model = self.model_class(**model_data)

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

    def get_by_id(self, template_id: int) -> Optional[PdfTemplate]:
        """Get PDF template by ID"""
        try:
            with self.connection_manager.session_scope() as session:
                model = session.get(self.model_class, template_id)
                if not model:
                    return None        
                return self._convert_to_domain_object(model)
              
        except SQLAlchemyError as e:
            logger.error(f"Error getting PDF template {template_id}: {e}")
            raise RepositoryError(f"Failed to get PDF template: {e}") from e
        
    def set_current_version_id(self, id: int, version_id: int) -> Optional[PdfTemplate]:
        """Set the current version ID for a template"""
        try:
            with self.connection_manager.session_scope() as session:
                # Get existing template
                model = session.get(self.model_class, id)

                if not model:
                    return None

                # Update current version ID
                model.current_version_id = version_id
                session.flush()
                session.refresh(model)

                logger.debug(f"Updated PDF template with ID: {id}")
                return self._convert_to_domain_object(model)
        except SQLAlchemyError as e:
            logger.error(f"Error updating PDF template {id}: {e}")
            raise RepositoryError(f"Failed to update PDF template: {e}") from e

    def get_all(self, status: Optional[str] = None, order_by: Optional[str] = None, desc: bool = False,
               limit: Optional[int] = None, offset: Optional[int] = None) -> List[PdfTemplate]:
        """Get all PDF templates with optional filtering, sorting and pagination"""
        try:
            with self.connection_manager.session_scope() as session:
                query = session.query(self.model_class)

                # Apply status filtering if specified
                if status:
                    query = query.filter(self.model_class.status == status)

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

    def update(self, template_id: int, update_data: PdfTemplateUpdate) -> Optional[PdfTemplate]:
        """Update a PDF template with the provided data"""
        try:
            with self.connection_manager.session_scope() as session:
                # Get existing template
                model = session.get(self.model_class, template_id)
                if not model:
                    return None

                # Update only fields that are provided (not None)
                update_dict = update_data.model_dump_for_db()
                for field, value in update_dict.items():
                    if hasattr(model, field):
                        setattr(model, field, value)

                # Update the updated_at timestamp
                model.updated_at = DateTimeUtils.utc_now()
                
                session.flush()
                session.refresh(model)

                logger.debug(f"Updated PDF template with ID: {template_id}")
                return self._convert_to_domain_object(model)

        except SQLAlchemyError as e:
            logger.error(f"Error updating PDF template {template_id}: {e}")
            raise RepositoryError(f"Failed to update PDF template: {e}") from e

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
