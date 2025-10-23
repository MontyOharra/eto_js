"""
PDF Files Repository
Repository for pdf_files table with CRUD operations
"""
import json
import logging
from datetime import datetime, timezone
from typing import Type

from shared.database.repositories.base import BaseRepository
from shared.database.models import PdfFileModel
from shared.types.pdf_files import (
    PdfMetadata,
    PdfCreate,
    PdfExtractedObjects,
    serialize_extracted_objects,
    deserialize_extracted_objects
)
from shared.exceptions import ObjectNotFoundError

logger = logging.getLogger(__name__)


class PdfRepository(BaseRepository[PdfFileModel]):
    """
    Repository for PDF file CRUD operations.

    Supports dual-mode operation:
    - Standalone: Pass connection_manager, auto-commits
    - UoW: Pass session, caller controls transaction

    Field mappings (model → dataclass):
    - objects_json → extracted_objects
    - file_size → file_size_bytes
    - relative_path → file_path
    - created_at → stored_at
    """

    @property
    def model_class(self) -> Type[PdfFileModel]:
        """Return the SQLAlchemy model class this repository manages"""
        return PdfFileModel

    # ========== Helper Methods ==========

    def _model_to_dataclass(self, model: PdfFileModel) -> PdfMetadata:
        """Convert ORM model to PdfMetadata dataclass"""
        # Parse objects_json to dict, then deserialize to typed dataclass
        if model.objects_json:
            try:
                objects_dict = json.loads(model.objects_json)
                extracted_objects = deserialize_extracted_objects(objects_dict)
            except (json.JSONDecodeError, KeyError, ValueError) as e:
                logger.error(f"Invalid JSON in objects_json for PDF {model.id}: {e}")
                # Return empty typed structure
                extracted_objects = PdfExtractedObjects(
                    text_words=[],
                    text_lines=[],
                    graphic_rects=[],
                    graphic_lines=[],
                    graphic_curves=[],
                    images=[],
                    tables=[]
                )
        else:
            # No objects extracted
            extracted_objects = PdfExtractedObjects(
                text_words=[],
                text_lines=[],
                graphic_rects=[],
                graphic_lines=[],
                graphic_curves=[],
                images=[],
                tables=[]
            )

        return PdfMetadata(
            id=model.id,
            email_id=model.email_id,
            original_filename=model.original_filename,
            file_hash=model.file_hash or "",
            file_size_bytes=model.file_size or 0,
            file_path=model.relative_path,
            page_count=model.page_count,
            stored_at=model.created_at,
            extracted_objects=extracted_objects,
            created_at=model.created_at,
            updated_at=model.updated_at,
        )

    # ========== CRUD Operations ==========

    def get_by_id(self, pdf_id: int) -> PdfMetadata | None:
        """
        Get PDF metadata by ID.

        Args:
            pdf_id: PDF record ID

        Returns:
            PdfMetadata dataclass or None if not found
        """
        with self._get_session() as session:
            model = session.get(self.model_class, pdf_id)

            if model is None:
                return None

            return self._model_to_dataclass(model)

    def get_by_hash(self, file_hash: str) -> PdfMetadata | None:
        """
        Get PDF metadata by file hash (for deduplication).

        Args:
            file_hash: SHA-256 hash of PDF file

        Returns:
            PdfMetadata dataclass or None if not found
        """
        with self._get_session() as session:
            model = session.query(self.model_class).filter_by(file_hash=file_hash).first()

            if model is None:
                return None

            return self._model_to_dataclass(model)

    def create(self, pdf_data: PdfCreate) -> PdfMetadata:
        """
        Create new PDF record.

        Args:
            pdf_data: PdfCreate dataclass with PDF data

        Returns:
            Created PdfMetadata dataclass
        """
        with self._get_session() as session:
            # Serialize typed extracted_objects to dict, then to JSON string
            objects_dict = serialize_extracted_objects(pdf_data.extracted_objects)
            objects_json = json.dumps(objects_dict)

            # Create ORM model
            model = self.model_class(
                email_id=pdf_data.email_id,
                filename=pdf_data.original_filename,  # Store in both filename and original_filename
                original_filename=pdf_data.original_filename,
                file_hash=pdf_data.file_hash,
                file_size=pdf_data.file_size_bytes,
                relative_path=pdf_data.file_path,
                page_count=pdf_data.page_count,
                objects_json=objects_json,
                # created_at and updated_at auto-set by server_default
            )

            session.add(model)
            session.flush()  # Get ID without committing

            return self._model_to_dataclass(model)
