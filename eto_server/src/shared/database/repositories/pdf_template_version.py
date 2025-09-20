"""
PDF Template Version Repository
"""

from sqlalchemy.orm import validates

import logging
import json
from typing import Optional, List, Dict, Any
from sqlalchemy.exc import SQLAlchemyError

from shared.database.repositories import BaseRepository
from shared.exceptions import RepositoryError, ObjectNotFoundError, ValidationError
from shared.database.models import PdfTemplateVersionModel
from shared.database.connection import DatabaseConnectionManager
from shared.domain import PdfTemplateVersion, PdfObject, ExtractionField

logger = logging.getLogger(__name__)


class PdfTemplateVersionRepository(BaseRepository[PdfTemplateVersionModel]):
    """Repository for PDF template versions"""
    
    def __init__(self, connection_manager: DatabaseConnectionManager):
        super().__init__(connection_manager)
        
    @property
    def model_class(self):
        return PdfTemplateVersionModel
    
    def _convert_to_domain_object(self, model: PdfTemplateVersionModel) -> PdfTemplateVersion:
        """Convert SQLAlchemy model to domain object"""
        return PdfTemplateVersion(
            id=getattr(model, 'id'),
            pdf_template_id=getattr(model, 'pdf_template_id'),
            version=getattr(model, 'version'),
            signature_objects=getattr(model, 'signature_objects'),
            signature_object_count=getattr(model, 'signature_object_count'),
            extraction_fields=getattr(model, 'extraction_fields'),
            usage_count=getattr(model, 'usage_count'),
            last_used_at=getattr(model, 'last_used_at'),
            created_at=getattr(model, 'created_at')
        )
        
    def create(self,
        pdf_template_id: int,
        version: int,
        signature_objects: List[PdfObject],
        extraction_fields: List[ExtractionField]
    ) -> PdfTemplateVersion:
        """Create a new PDF template version"""

        try:
            with self.connection_manager.session_scope() as session:
                # Convert domain objects to JSON strings for database storage
                signature_objects_json = json.dumps([obj.__dict__ for obj in signature_objects])
                extraction_fields_json = json.dumps([field.__dict__ for field in extraction_fields])
                signature_object_count = len(signature_objects)

                # Create new model with type-safe field assignment
                model = self.model_class(
                    pdf_template_id=pdf_template_id,
                    version=version,
                    signature_objects=signature_objects_json,
                    signature_object_count=signature_object_count,
                    extraction_fields=extraction_fields_json
                )

                # Add to session and flush to get ID
                session.add(model)
                session.flush()
                
                # Refresh to get updated fields
                session.refresh(model)
                
                # Convert to domain object before session closes
                domain_template = self._convert_to_domain_object(model)
                
                logger.debug(f"Created PDF template version: {domain_template.id}")
                return domain_template
            
        except SQLAlchemyError as e:
            logger.error(f"Error creating PDF template version: {e}")
            raise RepositoryError(f"Failed to create PDF template version: {e}") from e

    
    def get_by_pdf_template_id(self, template_id: int) -> List[PdfTemplateVersion]:
        """Get all versions of a template"""
        try:
            with self.connection_manager.session_scope() as session:
                models = session.query(self.model_class).filter(
                    self.model_class.pdf_template_id == template_id
                ).order_by(self.model_class.created_at.desc()).all()
                
                return [self._convert_to_domain_object(model) for model in models]
                
        except SQLAlchemyError as e:
            logger.error(f"Error getting versions for PDF template {template_id}: {e}")
            raise RepositoryError(f"Failed to get PDF template versions: {e}") from e