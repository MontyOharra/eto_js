"""
PDF Files Service
Manages PDF file storage, object extraction, and retrieval
"""
import hashlib
import logging
import tempfile
from datetime import datetime, timezone
from pathlib import Path
import pdfplumber

from shared.database import DatabaseConnectionManager
from shared.database.repositories import PdfFileRepository
from shared.types.pdf_files import (
    PdfMetadata,
    PdfCreate,
    PdfObjects,
    TextWord,
    TextLine,
    GraphicRect,
    GraphicLine,
    GraphicCurve,
    Image,
    Table
)
from shared.config import StorageConfig
from shared.exceptions.service import ObjectNotFoundError, ServiceError, ValidationError

logger = logging.getLogger(__name__)


class PdfFilesService:
    """
    PDF file management service.

    Handles PDF file storage with SHA-256 hash-based deduplication,
    date-based filesystem organization, and automatic object extraction using pdfplumber.
    """

    connection_manager: DatabaseConnectionManager
    storage_config: StorageConfig
    pdf_repository: PdfFileRepository
    base_storage_path: Path

    def __init__(
        self,
        connection_manager: DatabaseConnectionManager,
        storage_config: StorageConfig
    ) -> None:
        """
        Initialize PDF files service

        Args:
            connection_manager: Database connection manager
            storage_config: Storage configuration (filesystem paths)
        """
        self.connection_manager = connection_manager
        self.storage_config = storage_config

        self.pdf_repository = PdfFileRepository(connection_manager=connection_manager)

        # Storage settings
        self.base_storage_path = Path(storage_config.pdf_storage_path)
        self.base_storage_path.mkdir(parents=True, exist_ok=True)

    def get_pdf_metadata(self, pdf_id: int) -> PdfMetadata:
        """
        Get PDF metadata by ID.

        Returns complete metadata including file information, hash,
        storage path, and timestamps.

        Args:
            pdf_id: PDF record ID

        Returns:
            PdfMetadata dataclass

        Raises:
            ObjectNotFoundError: If PDF not found
        """
        metadata = self.pdf_repository.get_by_id(pdf_id)

        if not metadata:
            raise ObjectNotFoundError(f"PDF {pdf_id} not found")

        return metadata

    def get_pdf_file_bytes(self, pdf_id: int) -> tuple[bytes, str]:
        """
        Get PDF file bytes for streaming/download.

        Process:
        1. Get metadata from database
        2. Resolve filesystem path
        3. Read file bytes
        4. Return bytes + filename for Content-Disposition header

        Args:
            pdf_id: PDF record ID

        Returns:
            Tuple of (file_bytes, original_filename)

        Raises:
            ObjectNotFoundError: If PDF record not found
            FileNotFoundError: If file missing from filesystem
            ServiceError: If file read fails
        """
        # Get metadata
        metadata = self.pdf_repository.get_by_id(pdf_id)
        if not metadata:
            raise ObjectNotFoundError(f"PDF {pdf_id} not found")

        # Resolve file path
        file_path = self.base_storage_path / metadata.file_path

        # Validate file exists
        if not file_path.exists():
            logger.error(f"PDF file missing: {file_path}")
            raise FileNotFoundError(
                f"PDF file not found on filesystem (database record exists but file is missing)"
            )

        # Read file
        try:
            with open(file_path, 'rb') as f:
                file_bytes = f.read()

            return file_bytes, metadata.original_filename

        except Exception as e:
            logger.error(f"Error reading PDF file {file_path}: {e}")
            raise ServiceError(f"Failed to read PDF file: {str(e)}")

    def get_pdf_objects(
        self,
        pdf_id: int,
        object_type: str | None = None
    ) -> PdfObjects:
        """
        Get all extracted objects for a PDF.

        Objects are returned as typed PdfObjects dataclass.

        Args:
            pdf_id: PDF record ID
            object_type: Optional filter (not implemented - would require creating filtered PdfObjects)

        Returns:
            PdfObjects dataclass with typed objects

        Raises:
            ObjectNotFoundError: If PDF not found
        """
        # Get PDF metadata (contains typed extracted_objects)
        metadata = self.pdf_repository.get_by_id(pdf_id)
        if not metadata:
            raise ObjectNotFoundError(f"PDF {pdf_id} not found")

        # Return typed extracted_objects
        # Note: object_type filtering not implemented (would require constructing new PdfObjects)
        return metadata.extracted_objects

    def extract_objects_from_bytes(
        self,
        pdf_bytes: bytes,
        filename: str
    ) -> PdfObjects:
        """
        Extract objects from PDF bytes without storing the PDF.

        This is for temporary/preview extraction. Objects are returned
        but not stored in database. PDF file is not saved to filesystem.

        Process:
        1. Validate PDF
        2. Write bytes to temporary file
        3. Extract objects using pdfplumber (returns typed PdfObjects)
        4. Delete temporary file
        5. Return extracted objects (not persisted)

        Args:
            pdf_bytes: Raw PDF file bytes
            filename: Original filename (for logging/error messages)

        Returns:
            PdfObjects dataclass with typed objects

        Raises:
            ValidationError: If PDF is invalid (400)
            ServiceError: If extraction fails (500)
        """
        try:
            # Validate PDF first
            is_valid, error_msg = self._validate_pdf(pdf_bytes)
            if not is_valid:
                raise ValidationError(f"Invalid PDF: {error_msg}")

            # Create temporary file
            with tempfile.NamedTemporaryFile(suffix='.pdf', delete=False) as tmp_file:
                tmp_path = Path(tmp_file.name)
                tmp_file.write(pdf_bytes)

            try:
                # Extract objects from temporary file (returns dict)
                extracted_objects = self._extract_objects_from_file(
                    tmp_path,
                    filename
                )

                return extracted_objects

            finally:
                # Always delete temporary file
                if tmp_path.exists():
                    tmp_path.unlink()

        except ValidationError:
            # Re-raise validation errors unchanged
            raise

        except Exception as e:
            logger.error(f"Error extracting objects from {filename}: {e}")
            raise ServiceError(f"Failed to extract PDF objects: {str(e)}")

    def store_pdf(
        self,
        file_bytes: bytes,
        filename: str,
        email_id: int | None = None
    ) -> PdfMetadata:
        """
        Store PDF file with hash-based deduplication and extract objects.

        Process:
        1. Validate PDF
        2. Calculate SHA-256 hash
        3. Check if hash already exists (deduplication)
        4. If exists: return existing metadata
        5. If new:
           - Save file to date-based path (YYYY/MM/DD/hash.pdf)
           - Extract objects using pdfplumber (returns typed PdfObjects)
           - Create database record with typed extracted_objects
           - Return metadata

        Args:
            file_bytes: Raw PDF file bytes
            filename: Original filename
            email_id: Optional email_id (source tracking)

        Returns:
            PdfMetadata dataclass with complete metadata

        Raises:
            ValidationError: If PDF is invalid (400)
            ServiceError: If storage or extraction fails (500)
        """
        try:
            # Validate PDF first
            is_valid, error_msg = self._validate_pdf(file_bytes)
            if not is_valid:
                raise ValidationError(f"Invalid PDF: {error_msg}")

            # Calculate hash
            file_hash = hashlib.sha256(file_bytes).hexdigest()

            # Check for existing PDF with same hash
            existing = self.pdf_repository.get_by_hash(file_hash)
            if existing:
                logger.info(f"PDF {filename} already exists (hash: {file_hash[:8]}...)")
                return existing

            # Generate storage path: YYYY/MM/DD/hash.pdf
            now = datetime.now(timezone.utc)
            relative_path = Path(
                str(now.year),
                f"{now.month:02d}",
                f"{now.day:02d}",
                f"{file_hash}.pdf"
            )
            full_path = self.base_storage_path / relative_path

            # Create directory structure
            full_path.parent.mkdir(parents=True, exist_ok=True)

            # Write file to filesystem
            with open(full_path, 'wb') as f:
                f.write(file_bytes)

            logger.info(f"Stored PDF at {relative_path}")

            # Extract objects (returns typed PdfObjects)
            extracted_objects = self._extract_objects_from_file(
                full_path,
                filename
            )

            # Count total objects for logging
            total_objects = (
                len(extracted_objects.text_words) + len(extracted_objects.text_lines) +
                len(extracted_objects.graphic_rects) + len(extracted_objects.graphic_lines) +
                len(extracted_objects.graphic_curves) + len(extracted_objects.images) +
                len(extracted_objects.tables)
            )

            # Calculate page count from objects
            page_count = 0
            for obj_list in [
                extracted_objects.text_words, extracted_objects.text_lines,
                extracted_objects.graphic_rects, extracted_objects.graphic_lines,
                extracted_objects.graphic_curves, extracted_objects.images,
                extracted_objects.tables
            ]:
                for obj in obj_list:
                    page_count = max(page_count, obj.page + 1)

            # Create database record with typed extracted_objects
            pdf_create = PdfCreate(
                original_filename=filename,
                file_hash=file_hash,
                file_size_bytes=len(file_bytes),
                file_path=str(relative_path),
                email_id=email_id,
                stored_at=now,
                extracted_objects=extracted_objects,
                page_count=page_count if page_count > 0 else None
            )

            # Single repository call - no UoW needed
            pdf_metadata = self.pdf_repository.create(pdf_create)

            logger.info(
                f"Extracted {total_objects} objects from {filename} "
                f"(PDF ID: {pdf_metadata.id})"
            )

            return pdf_metadata

        except ValidationError:
            # Re-raise validation errors unchanged
            raise

        except Exception as e:
            logger.error(f"Error storing PDF {filename}: {e}", exc_info=True)
            raise ServiceError(f"Failed to store PDF: {str(e)}")

    def _clean_pdf_value(self, value: any) -> any:
        """
        Clean a value from pdfplumber to ensure it's JSON-serializable.

        Handles PSLiteral objects from pdfminer by converting to strings.
        Also handles bytes and other non-serializable types.

        Args:
            value: Raw value from pdfplumber

        Returns:
            Clean, JSON-serializable value
        """
        # Handle None
        if value is None:
            return ''

        # Handle PSLiteral objects (have a 'name' attribute)
        if hasattr(value, 'name'):
            # PSLiteral.name can be bytes or str
            name = value.name
            if isinstance(name, bytes):
                return name.decode('utf-8', errors='replace')
            return str(name)

        # Handle bytes
        if isinstance(value, bytes):
            return value.decode('utf-8', errors='replace')

        # Return as-is for primitive types
        return value

    def _extract_objects_from_file(
        self,
        file_path: Path,
        filename: str
    ) -> PdfObjects:
        """
        Extract objects from PDF file using pdfplumber.

        Returns PdfObjects dataclass with strongly-typed objects.
        All PSLiteral and non-serializable types are converted to clean Python types.

        Extracts:
        - Text words (text, fontname, fontsize)
        - Text lines (bbox only)
        - Graphic rectangles (bbox, linewidth)
        - Graphic lines (bbox, linewidth)
        - Graphic curves (bbox, points, linewidth)
        - Images (metadata: format, colorspace, bits)
        - Tables (bbox, rows, cols)

        Args:
            file_path: Path to PDF file on filesystem
            filename: Original filename (for logging)

        Returns:
            PdfObjects dataclass with typed objects (all clean, JSON-serializable)

        Raises:
            ServiceError: If extraction fails
        """

        # Initialize lists for typed objects
        text_words: list[TextWord] = []
        text_lines: list[TextLine] = []
        graphic_rects: list[GraphicRect] = []
        graphic_lines: list[GraphicLine] = []
        graphic_curves: list[GraphicCurve] = []
        images: list[Image] = []
        tables: list[Table] = []

        try:
            with pdfplumber.open(file_path) as pdf:
                for page in pdf.pages:
                    page_num = page.page_number  # 1-indexed (matches frontend)

                    # Extract text words → TextWord dataclasses
                    words = page.extract_words()
                    for word in words:
                        # Clean fontname (can be PSLiteral)
                        fontname = self._clean_pdf_value(word.get('fontname', ''))

                        text_words.append(TextWord(
                            page=page_num,
                            bbox=(word['x0'], word['top'], word['x1'], word['bottom']),
                            text=word['text'],
                            fontname=str(fontname),  # Ensure string
                            fontsize=float(word.get('size', 0.0))  # Ensure float
                        ))

                    # Extract lines → TextLine dataclasses
                    lines = page.lines
                    for line in lines:
                        text_lines.append(TextLine(
                            page=page_num,
                            bbox=(line['x0'], line['top'], line['x1'], line['bottom'])
                        ))

                    # Extract rectangles → GraphicRect dataclasses
                    rects = page.rects
                    for rect in rects:
                        graphic_rects.append(GraphicRect(
                            page=page_num,
                            bbox=(rect['x0'], rect['top'], rect['x1'], rect['bottom']),
                            linewidth=rect.get('linewidth', 1.0)
                        ))

                    # Extract curves → GraphicCurve dataclasses
                    curves = page.curves
                    for curve in curves:
                        graphic_curves.append(GraphicCurve(
                            page=page_num,
                            bbox=(curve['x0'], curve['top'], curve['x1'], curve['bottom']),
                            points=[tuple(pt) for pt in curve.get('points', [])],
                            linewidth=curve.get('linewidth', 1.0)
                        ))

                    # Extract images → Image dataclasses
                    imgs = page.images
                    for img in imgs:
                        # Clean colorspace (can be PSLiteral)
                        colorspace = self._clean_pdf_value(img.get('colorspace', ''))

                        # Extract format from name
                        img_name = img.get('name', '')
                        img_format = str(img_name).split('.')[-1].upper() if img_name else ''

                        images.append(Image(
                            page=page_num,
                            bbox=(img['x0'], img['top'], img['x1'], img['bottom']),
                            format=img_format,
                            colorspace=str(colorspace),  # Ensure string
                            bits=int(img.get('bits', 0))  # Ensure int
                        ))

                    # Extract tables → Table dataclasses
                    tables_found = page.find_tables()
                    for table in tables_found:
                        table_data = table.extract()
                        tables.append(Table(
                            page=page_num,
                            bbox=table.bbox,
                            rows=len(table_data),
                            cols=len(table_data[0]) if table_data else 0
                        ))

            total_objects = (
                len(text_words) + len(text_lines) + len(graphic_rects) +
                len(graphic_lines) + len(graphic_curves) + len(images) + len(tables)
            )
            logger.debug(
                f"Extracted {total_objects} objects from {filename} "
                f"({len(pdf.pages)} pages)"
            )

            # Return typed container
            return PdfObjects(
                text_words=text_words,
                text_lines=text_lines,
                graphic_rects=graphic_rects,
                graphic_lines=graphic_lines,
                graphic_curves=graphic_curves,
                images=images,
                tables=tables
            )

        except Exception as e:
            logger.error(f"Error extracting objects from {filename}: {e}", exc_info=True)
            raise ServiceError(f"PDF extraction failed: {str(e)}")

    def _validate_pdf(self, file_bytes: bytes) -> tuple[bool, str | None]:
        """
        Validate that the file is a valid PDF.

        Args:
            file_bytes: File content to validate

        Returns:
            Tuple of (is_valid, error_message)
        """
        # Check PDF header
        if not file_bytes.startswith(b'%PDF'):
            return False, "File does not have PDF header"

        # Try to open with pdfplumber
        try:
            import pdfplumber
            from io import BytesIO

            with pdfplumber.open(BytesIO(file_bytes)) as pdf:
                # Check if we can access pages
                if len(pdf.pages) == 0:
                    return False, "PDF has no pages"
            return True, None

        except Exception as e:
            return False, f"Invalid PDF: {str(e)}"
