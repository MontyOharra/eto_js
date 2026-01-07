"""
PDF Template Version Repository
Repository for pdf_template_versions table with CRUD operations
"""
import json
import logging
from typing import Type

from shared.database.repositories.base import BaseRepository
from shared.database.models import PdfTemplateVersionModel
from shared.types.pdf_templates import (
    PdfTemplateVersion,
    PdfTemplateVersionCreate,
    PdfTemplateVersionSummary,
    ExtractionField,
)
from shared.types.pdf_files import PdfObjects

logger = logging.getLogger(__name__)


class PdfTemplateVersionRepository(BaseRepository[PdfTemplateVersionModel]):
    """
    Repository for PDF template version CRUD operations.

    Handles JSON serialization/deserialization of:
    - signature_objects (PdfObjects)
    - extraction_fields (list[ExtractionField])

    Supports dual-mode operation:
    - Standalone: Pass connection_manager, auto-commits
    - UoW: Pass session, caller controls transaction
    """

    @property
    def model_class(self) -> Type[PdfTemplateVersionModel]:
        """Return the SQLAlchemy model class this repository manages"""
        return PdfTemplateVersionModel

    # ========== Serialization Methods ==========

    def _serialize_pdf_objects(self, obj: PdfObjects) -> str:
        """Convert PdfObjects to JSON string for DB storage."""
        return json.dumps(obj.model_dump())

    def _deserialize_pdf_objects(self, json_str: str) -> PdfObjects:
        """Convert JSON string from DB to PdfObjects."""
        data = json.loads(json_str)
        return PdfObjects.model_validate(data)

    def _serialize_extraction_fields(self, fields: list[ExtractionField]) -> str:
        """Convert list of ExtractionField to JSON string for DB storage."""
        return json.dumps({"fields": [field.model_dump() for field in fields]})

    def _deserialize_extraction_fields(self, json_str: str) -> list[ExtractionField]:
        """Convert JSON string from DB to list of ExtractionField."""
        data = json.loads(json_str)
        # Support both wrapped and unwrapped formats for backward compatibility
        fields_data = data.get("fields", data) if isinstance(data, dict) else data

        return [ExtractionField.model_validate(f) for f in fields_data]

    # ========== Helper Methods ==========

    def _model_to_version(self, model: PdfTemplateVersionModel) -> PdfTemplateVersion:
        """Convert ORM model to PdfTemplateVersion"""
        # Deserialize JSON fields
        signature_objects = self._deserialize_pdf_objects(model.signature_objects)
        extraction_fields = self._deserialize_extraction_fields(model.extraction_fields)

        # Get source_pdf_id from the template relationship
        source_pdf_id = model.pdf_template.source_pdf_id

        return PdfTemplateVersion(
            id=model.id,
            template_id=model.pdf_template_id,
            version_number=model.version_num,
            source_pdf_id=source_pdf_id,
            signature_objects=signature_objects,
            extraction_fields=extraction_fields,
            pipeline_definition_id=model.pipeline_definition_id,
            created_at=model.created_at,
        )

    def model_to_version_with_source(self, model: PdfTemplateVersionModel, source_pdf_id: int) -> PdfTemplateVersion:
        """
        Convert ORM model to PdfTemplateVersion with provided source_pdf_id.

        Used when template relationship may not be loaded and source_pdf_id is known.

        Args:
            model: PdfTemplateVersionModel instance
            source_pdf_id: Source PDF file ID

        Returns:
            PdfTemplateVersion
        """
        # Deserialize JSON fields
        signature_objects = self._deserialize_pdf_objects(model.signature_objects)
        extraction_fields = self._deserialize_extraction_fields(model.extraction_fields)

        return PdfTemplateVersion(
            id=model.id,
            template_id=model.pdf_template_id,
            version_number=model.version_num,
            source_pdf_id=source_pdf_id,
            signature_objects=signature_objects,
            extraction_fields=extraction_fields,
            pipeline_definition_id=model.pipeline_definition_id,
            created_at=model.created_at,
        )

    # ========== CRUD Operations ==========

    def create(self, version_data: PdfTemplateVersionCreate) -> PdfTemplateVersion:
        """
        Create new template version with JSON serialization.

        Args:
            version_data: PdfTemplateVersionCreate with version data

        Returns:
            Created PdfTemplateVersion
        """
        with self._get_session() as session:
            # Serialize complex types to JSON
            signature_objects_json = self._serialize_pdf_objects(version_data.signature_objects)
            extraction_fields_json = self._serialize_extraction_fields(version_data.extraction_fields)

            # Create ORM model
            model = self.model_class(
                pdf_template_id=version_data.template_id,
                version_num=version_data.version_number,
                signature_objects=signature_objects_json,
                extraction_fields=extraction_fields_json,
                pipeline_definition_id=version_data.pipeline_definition_id,
                usage_count=0,  # Initialize to 0
                last_used_at=None,
                # created_at and updated_at auto-set by server_default
            )

            session.add(model)
            session.flush()  # Get ID without committing

            # Manually set source_pdf_id for the return
            # (In a real scenario, we'd load the template to get this)
            return PdfTemplateVersion(
                id=model.id,
                template_id=model.pdf_template_id,
                version_number=model.version_num,
                source_pdf_id=version_data.source_pdf_id,  # Use from input
                signature_objects=version_data.signature_objects,
                extraction_fields=version_data.extraction_fields,
                pipeline_definition_id=model.pipeline_definition_id,
                created_at=model.created_at,
            )

    def get_by_id(self, version_id: int) -> PdfTemplateVersion | None:
        """
        Get template version by ID with JSON deserialization.

        Args:
            version_id: Version record ID

        Returns:
            PdfTemplateVersion or None if not found
        """
        with self._get_session() as session:
            model = session.query(self.model_class).filter_by(id=version_id).first()

            if model is None:
                return None

            return self._model_to_version(model)

    def list_by_template(self, template_id: int) -> list[PdfTemplateVersionSummary]:
        """
        List all versions for a template (version history).

        Ordered by version_number DESC (newest first).

        Args:
            template_id: Template ID

        Returns:
            List of PdfTemplateVersionSummary
        """
        with self._get_session() as session:
            models = (
                session.query(self.model_class)
                .filter_by(pdf_template_id=template_id)
                .order_by(self.model_class.version_num.desc())
                .all()
            )

            # Get current_version_id to mark which is current
            from shared.database.models import PdfTemplateModel
            template = session.get(PdfTemplateModel, template_id)
            current_version_id = template.current_version_id if template else None

            return [
                PdfTemplateVersionSummary(
                    id=model.id,
                    version_number=model.version_num,
                    created_at=model.created_at,
                    is_current=(model.id == current_version_id)
                )
                for model in models
            ]

    def get_version_list_for_template(self, template_id: int) -> list[tuple[int, int]]:
        """
        Get a list of (id, version_number) tuples for all versions of a template.

        Ordered by version_number ASC (oldest first).

        Args:
            template_id: Template ID

        Returns:
            List of tuples (version_id, version_number) for each version
        """
        with self._get_session() as session:
            models = (
                session.query(self.model_class.id, self.model_class.version_num)
                .filter_by(pdf_template_id=template_id)
                .order_by(self.model_class.version_num.asc())
                .all()
            )

            return [(model.id, model.version_num) for model in models]

    def get_current_for_template(self, template_id: int) -> PdfTemplateVersion | None:
        """
        Get the current active version for a template.

        Args:
            template_id: Template ID

        Returns:
            PdfTemplateVersion or None if no current version
        """
        with self._get_session() as session:
            # Join to template to get current_version_id
            from shared.database.models import PdfTemplateModel

            template = session.get(PdfTemplateModel, template_id)
            if not template or not template.current_version_id:
                return None

            model = session.get(self.model_class, template.current_version_id)
            if not model:
                return None

            return self._model_to_version(model)

    def increment_usage_count(self, version_id: int) -> None:
        """
        Increment usage count and update last_used_at for a template version.

        Called when a template is matched during ETO processing to track
        template usage statistics.

        Args:
            version_id: Template version ID
        """
        from datetime import datetime, timezone

        with self._get_session() as session:
            model = session.get(self.model_class, version_id)
            if model:
                model.usage_count += 1
                model.last_used_at = datetime.now(timezone.utc)
                session.flush()  # Persist changes
                logger.debug(f"Incremented usage count for version {version_id} to {model.usage_count}")
