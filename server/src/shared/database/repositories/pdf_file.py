"""
PDF Files Repository
Repository for pdf_files table with CRUD operations
"""
import json
import logging
from typing import Type, Any

from shared.database.repositories.base import BaseRepository
from shared.database.models import PdfFileModel
from shared.types.pdf_files import (
    PdfFile,
    PdfFileCreate,
    PdfObjects,
    TextWord,
    GraphicRect,
    GraphicLine,
    GraphicCurve,
    Image,
    Table,
)

logger = logging.getLogger(__name__)


class PdfFileRepository(BaseRepository[PdfFileModel]):
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

    # ========== Serialization Methods ==========

    def _serialize_pdf_objects(self, obj: PdfObjects) -> str:
        """
        Convert PdfObjects dataclass directly to JSON string for DB storage.

        Uses dataclasses.asdict to recursively convert nested dataclasses.
        Tuples (like bbox) are automatically converted to lists for JSON compatibility.

        Note: PSLiteral and other non-serializable types are already cleaned
        during extraction in PdfFilesService._extract_objects_from_file(),
        so this is a simple conversion.
        """
        from dataclasses import asdict
        return json.dumps(asdict(obj))

    def _deserialize_pdf_objects(self, json_str: str) -> PdfObjects:
        """
        Convert JSON string from DB directly to PdfObjects dataclass.

        Reconstructs all nested dataclasses from dict representation.
        Lists are converted back to appropriate dataclass types.
        """
        data = json.loads(json_str)

        return PdfObjects(
            text_words=[
                TextWord(
                    page=w["page"],
                    bbox=tuple(w["bbox"]),  # Convert list back to tuple
                    text=w["text"],
                    fontname=w["fontname"],
                    fontsize=w["fontsize"]
                )
                for w in data.get("text_words", [])
            ],
            graphic_rects=[
                GraphicRect(
                    page=r["page"],
                    bbox=tuple(r["bbox"]),
                    linewidth=r["linewidth"]
                )
                for r in data.get("graphic_rects", [])
            ],
            graphic_lines=[
                GraphicLine(
                    page=l["page"],
                    bbox=tuple(l["bbox"]),
                    linewidth=l["linewidth"]
                )
                for l in data.get("graphic_lines", [])
            ],
            graphic_curves=[
                GraphicCurve(
                    page=c["page"],
                    bbox=tuple(c["bbox"]),
                    points=[tuple(p) for p in c["points"]],  # Convert list of lists to list of tuples
                    linewidth=c["linewidth"]
                )
                for c in data.get("graphic_curves", [])
            ],
            images=[
                Image(
                    page=i["page"],
                    bbox=tuple(i["bbox"]),
                    format=i["format"],
                    colorspace=i["colorspace"],
                    bits=i["bits"]
                )
                for i in data.get("images", [])
            ],
            tables=[
                Table(
                    page=t["page"],
                    bbox=tuple(t["bbox"]),
                    rows=t["rows"],
                    cols=t["cols"]
                )
                for t in data.get("tables", [])
            ]
        )

    # ========== Helper Methods ==========

    def _model_to_dataclass(self, model: PdfFileModel) -> PdfFile:
        """Convert ORM model to PdfFile dataclass"""
        # Deserialize objects_json directly to typed dataclass
        if model.objects_json:
            try:
                extracted_objects = self._deserialize_pdf_objects(model.objects_json)
            except (json.JSONDecodeError, KeyError, ValueError) as e:
                logger.error(f"Invalid JSON in objects_json for PDF {model.id}: {e}")
                # Return empty typed structure
                extracted_objects = PdfObjects(
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
            extracted_objects = PdfObjects(
                text_words=[],
                text_lines=[],
                graphic_rects=[],
                graphic_lines=[],
                graphic_curves=[],
                images=[],
                tables=[]
            )

        return PdfFile(
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

    def get_by_id(self, pdf_id: int) -> PdfFile | None:
        """
        Get PDF file by ID.

        Args:
            pdf_id: PDF record ID

        Returns:
            PdfFile dataclass or None if not found
        """
        with self._get_session() as session:
            model = session.get(self.model_class, pdf_id)

            if model is None:
                return None

            return self._model_to_dataclass(model)

    def get_by_hash(self, file_hash: str) -> PdfFile | None:
        """
        Get PDF file by file hash (for deduplication).

        Args:
            file_hash: SHA-256 hash of PDF file

        Returns:
            PdfFile dataclass or None if not found
        """
        with self._get_session() as session:
            model = session.query(self.model_class).filter_by(file_hash=file_hash).first()

            if model is None:
                return None

            return self._model_to_dataclass(model)

    def get_by_ids(self, pdf_ids: list[int]) -> list[PdfFile]:
        """
        Batch fetch PDF files by IDs.

        Args:
            pdf_ids: List of PDF record IDs

        Returns:
            List of PdfFile dataclasses (excludes not found)
        """
        if not pdf_ids:
            return []

        with self._get_session() as session:
            models = (
                session.query(self.model_class)
                .filter(self.model_class.id.in_(pdf_ids))
                .all()
            )

            return [self._model_to_dataclass(model) for model in models]

    def create(self, pdf_data: PdfFileCreate) -> PdfFile:
        """
        Create new PDF record.

        Args:
            pdf_data: PdfFileCreate dataclass with PDF data

        Returns:
            Created PdfFile dataclass
        """
        with self._get_session() as session:
            # Serialize typed extracted_objects directly to JSON string
            objects_json = self._serialize_pdf_objects(pdf_data.extracted_objects)

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
