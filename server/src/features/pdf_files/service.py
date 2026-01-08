"""
PDF Files Service
Manages PDF file storage, object extraction, and retrieval
"""
import hashlib
import logging
import tempfile
from collections import defaultdict
from datetime import datetime, timezone
from io import BytesIO
from pathlib import Path
from typing import Any

import pdfplumber

from features.pdf_files.utils import extract_data_from_pdf_objects
from shared.config import StorageConfig
from shared.database import DatabaseConnectionManager
from shared.database.repositories import PdfFileRepository
from shared.exceptions.service import ObjectNotFoundError, ServiceError, ValidationError
from shared.types.pdf_files import (
    GraphicCurve,
    GraphicLine,
    GraphicRect,
    Image,
    PdfFile,
    PdfFileCreate,
    PdfObjects,
    Table,
    TextWord,
)

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

    def get_pdf_file(self, pdf_id: int) -> PdfFile:
        """
        Get PDF file by ID.

        Returns complete file data including metadata, hash,
        storage path, and extracted objects.

        Args:
            pdf_id: PDF record ID

        Returns:
            PdfFile dataclass

        Raises:
            ObjectNotFoundError: If PDF not found
        """
        pdf = self.pdf_repository.get_by_id(pdf_id)

        if not pdf:
            raise ObjectNotFoundError(f"PDF {pdf_id} not found")

        return pdf

    def get_by_ids(self, pdf_ids: list[int]) -> dict[int, PdfFile]:
        """
        Batch fetch PDF files by IDs.

        Args:
            pdf_ids: List of PDF record IDs

        Returns:
            Dict mapping pdf_id to PdfFile dataclass
        """
        if not pdf_ids:
            return {}

        pdfs = self.pdf_repository.get_by_ids(pdf_ids)
        return {pdf.id: pdf for pdf in pdfs}

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
                # Extract objects from temporary file
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

    def extract_text_from_pdf(
        self,
        pdf_bytes: bytes,
        extraction_fields: list[dict[str, Any]]
    ) -> dict[str, str]:
        """
        Extract text from PDF using extraction fields (text words only).

        More efficient than extract_objects_from_bytes - only extracts text words,
        not graphics, images, tables, etc.

        Args:
            pdf_bytes: Raw PDF file bytes
            extraction_fields: List of extraction field dicts with:
                - name: Field name
                - bbox: [x0, y0, x1, y1]
                - page: Page number

        Returns:
            Dict mapping field names to extracted text

        Raises:
            ValidationError: If PDF is invalid
            ServiceError: If extraction fails
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
                # Extract ONLY text words (not all objects)
                text_words = []

                with pdfplumber.open(tmp_path) as pdf:
                    for page in pdf.pages:
                        page_num = page.page_number  # Keep 1-indexed

                        # Extract only text words
                        words = page.extract_words()
                        for word in words:
                            text_words.append({
                                "type": "text_word",
                                "page": page_num,
                                "bbox": [word['x0'], word['top'], word['x1'], word['bottom']],
                                "text": word['text'],
                                "fontname": self._clean_pdf_value(word.get('fontname', '')),
                                "fontsize": float(word.get('size', 0.0))
                            })

                # Use extraction utility to extract data from text words
                extracted_data = extract_data_from_pdf_objects(
                    pdf_objects=text_words,
                    extraction_fields=extraction_fields
                )

                return extracted_data

            finally:
                # Always delete temporary file
                tmp_path.unlink(missing_ok=True)

        except ValidationError:
            # Re-raise validation errors unchanged
            raise

        except Exception as e:
            logger.error(f"Failed to extract text from PDF: {e}")
            raise ServiceError(f"Failed to extract text from PDF: {e}")

    def store_pdf(
        self,
        file_bytes: bytes,
        filename: str
    ) -> PdfFile:
        """
        Store PDF file with hash-based deduplication and extract objects.

        Process:
        1. Validate PDF
        2. Calculate SHA-256 hash
        3. Check if hash already exists (deduplication)
        4. If exists: return existing file record
        5. If new:
           - Save file to date-based path (YYYY/MM/DD/hash.pdf)
           - Extract objects using pdfplumber (returns typed PdfObjects)
           - Create database record with typed extracted_objects
           - Return file record

        Args:
            file_bytes: Raw PDF file bytes
            filename: Original filename

        Returns:
            PdfFile dataclass with complete file data

        Note:
            Source tracking (email/manual) is now handled at the eto_runs level,
            not at the PDF file level. PDFs are deduplicated storage entities only.

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
                len(extracted_objects.text_words) +
                len(extracted_objects.graphic_rects) + len(extracted_objects.graphic_lines) +
                len(extracted_objects.graphic_curves) + len(extracted_objects.images) +
                len(extracted_objects.tables)
            )

            # Calculate page count from objects (pages are 1-indexed)
            page_count = 0
            for obj_list in [
                extracted_objects.text_words,
                extracted_objects.graphic_rects, extracted_objects.graphic_lines,
                extracted_objects.graphic_curves, extracted_objects.images,
                extracted_objects.tables
            ]:
                for obj in obj_list:
                    page_count = max(page_count, obj.page)

            # Create database record with typed extracted_objects
            pdf_create = PdfFileCreate(
                original_filename=filename,
                file_hash=file_hash,
                file_size_bytes=len(file_bytes),
                file_path=str(relative_path),
                stored_at=now,
                extracted_objects=extracted_objects,
                page_count=page_count if page_count > 0 else None
            )

            # Single repository call - no UoW needed
            pdf = self.pdf_repository.create(pdf_create)

            logger.info(
                f"Extracted {total_objects} objects from {filename} "
                f"(PDF ID: {pdf.id})"
            )

            return pdf

        except ValidationError:
            # Re-raise validation errors unchanged
            raise

        except Exception as e:
            logger.error(f"Error storing PDF {filename}: {e}", exc_info=True)
            raise ServiceError(f"Failed to store PDF: {str(e)}")

    def _clean_pdf_value(self, value: Any) -> Any:
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
        graphic_rects: list[GraphicRect] = []
        graphic_lines: list[GraphicLine] = []
        graphic_curves: list[GraphicCurve] = []
        images: list[Image] = []
        tables: list[Table] = []

        try:
            with pdfplumber.open(file_path) as pdf:
                for page in pdf.pages:
                    page_num = page.page_number  # 1-indexed

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

                    # Extract graphic lines → GraphicLine dataclasses
                    lines = page.lines
                    for line in lines:
                        graphic_lines.append(GraphicLine(
                            page=page_num,
                            bbox=(line['x0'], line['y0'], line['x1'], line['y1']),
                            linewidth=line.get('linewidth', 1.0)
                        ))

                    # Extract rectangles → GraphicRect or GraphicLine dataclasses
                    # Filter out full-page rectangles (useless and block other objects)
                    # Reclassify thin rectangles as lines (many PDFs use thin rects for borders)
                    rects = page.rects
                    page_width = page.width
                    page_height = page.height
                    page_area = page_width * page_height

                    # Thresholds for thin rectangle → line reclassification
                    THIN_DIMENSION_THRESHOLD = 3.0  # Points - rects thinner than this become lines
                    ASPECT_RATIO_THRESHOLD = 15.0   # Ratio - rects more extreme than this become lines

                    for rect in rects:
                        # Calculate rectangle dimensions
                        rect_width = rect['x1'] - rect['x0']
                        rect_height = rect['y1'] - rect['y0']
                        rect_area = rect_width * rect_height

                        # Skip rectangles that cover ≥95% of page area
                        area_ratio = rect_area / page_area if page_area > 0 else 0
                        if area_ratio >= 0.95:
                            logger.debug(
                                f"Skipping full-page rectangle on page {page_num} "
                                f"(covers {area_ratio:.1%} of page)"
                            )
                            continue

                        # Check if rectangle should be reclassified as a line
                        # A rectangle is "line-like" if:
                        # 1. Its minimum dimension is very small (< threshold), OR
                        # 2. Its aspect ratio is extreme (> threshold)
                        min_dimension = min(rect_width, rect_height)
                        max_dimension = max(rect_width, rect_height)
                        aspect_ratio = max_dimension / max(min_dimension, 0.01)  # Avoid division by zero

                        is_line_like = (
                            min_dimension < THIN_DIMENSION_THRESHOLD or
                            aspect_ratio > ASPECT_RATIO_THRESHOLD
                        )

                        if is_line_like:
                            # Reclassify as a line
                            # Use CENTER coordinates to avoid stroke-width offset issues
                            # For horizontal lines (thin height): use center Y
                            # For vertical lines (thin width): use center X
                            if rect_height < rect_width:
                                # Horizontal line - use center Y
                                y_center = (rect['y0'] + rect['y1']) / 2
                                line_bbox = (rect['x0'], y_center, rect['x1'], y_center)
                            else:
                                # Vertical line - use center X
                                x_center = (rect['x0'] + rect['x1']) / 2
                                line_bbox = (x_center, rect['y0'], x_center, rect['y1'])

                            graphic_lines.append(GraphicLine(
                                page=page_num,
                                bbox=line_bbox,
                                linewidth=rect.get('linewidth', 1.0)
                            ))
                        else:
                            # Keep as rectangle
                            graphic_rects.append(GraphicRect(
                                page=page_num,
                                bbox=(rect['x0'], rect['y0'], rect['x1'], rect['y1']),
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
                            bbox=(img['x0'], img['y0'], img['x1'], img['y1']),
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

            # Merge collinear connected lines into single lines
            # This consolidates fragmented line segments (common in PDFs)
            lines_before_merge = len(graphic_lines)
            graphic_lines = self._merge_collinear_lines(graphic_lines, tolerance=2.0)

            total_objects = (
                len(text_words) + len(graphic_rects) +
                len(graphic_lines) + len(graphic_curves) + len(images) + len(tables)
            )
            logger.debug(
                f"Extracted {total_objects} objects from {filename} "
                f"({len(pdf.pages)} pages, lines: {lines_before_merge} → {len(graphic_lines)} after merge)"
            )

            # Return typed container
            return PdfObjects(
                text_words=text_words,
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
            with pdfplumber.open(BytesIO(file_bytes)) as pdf:
                # Check if we can access pages
                if len(pdf.pages) == 0:
                    return False, "PDF has no pages"
            return True, None

        except Exception as e:
            return False, f"Invalid PDF: {str(e)}"

    def _merge_collinear_lines(
        self,
        lines: list[GraphicLine],
        tolerance: float = 2.0
    ) -> list[GraphicLine]:
        """
        Merge collinear lines that share endpoints into single longer lines.

        Many PDFs create visual "lines" as multiple small connected segments.
        This method consolidates them into single lines for better usability.

        Only merges lines that:
        1. Are on the same page
        2. Have the same direction (horizontal, vertical, or same diagonal slope)
        3. Share an endpoint (are connected) or overlap

        Args:
            lines: List of GraphicLine objects to merge
            tolerance: Coordinate tolerance for grouping and endpoint matching

        Returns:
            List of merged GraphicLine objects
        """
        if not lines:
            return []

        # Group lines by page first
        lines_by_page: dict[int, list[GraphicLine]] = defaultdict(list)
        for line in lines:
            lines_by_page[line.page].append(line)

        merged_lines: list[GraphicLine] = []

        for page_num, page_lines in lines_by_page.items():
            # Classify lines by direction
            horizontal: list[GraphicLine] = []  # Height ≈ 0
            vertical: list[GraphicLine] = []    # Width ≈ 0
            diagonal: list[GraphicLine] = []    # Others

            for line in page_lines:
                x0, y0, x1, y1 = line.bbox
                width = abs(x1 - x0)
                height = abs(y1 - y0)

                if height < tolerance:  # Horizontal line
                    horizontal.append(line)
                elif width < tolerance:  # Vertical line
                    vertical.append(line)
                else:  # Diagonal line
                    diagonal.append(line)

            # Merge horizontal lines (group by y-coordinate, merge along x)
            merged_horizontal = self._merge_lines_along_axis(
                horizontal, axis='horizontal', tolerance=tolerance
            )

            # Merge vertical lines (group by x-coordinate, merge along y)
            merged_vertical = self._merge_lines_along_axis(
                vertical, axis='vertical', tolerance=tolerance
            )

            # Merge diagonal lines (group by slope and intercept)
            merged_diagonal = self._merge_diagonal_lines(diagonal, tolerance=tolerance)

            merged_lines.extend(merged_horizontal)
            merged_lines.extend(merged_vertical)
            merged_lines.extend(merged_diagonal)

        logger.debug(
            f"Line merging: {len(lines)} input lines → {len(merged_lines)} merged lines"
        )

        return merged_lines

    def _merge_lines_along_axis(
        self,
        lines: list[GraphicLine],
        axis: str,
        tolerance: float
    ) -> list[GraphicLine]:
        """
        Merge lines along a specific axis (horizontal or vertical).

        Groups lines by their perpendicular coordinate, then merges
        segments that touch or overlap within each group.

        Args:
            lines: Lines to merge (should all be same direction)
            axis: 'horizontal' or 'vertical'
            tolerance: Coordinate tolerance for grouping

        Returns:
            List of merged lines
        """
        if not lines:
            return []

        # Group by the perpendicular coordinate
        # For horizontal lines: group by y-coordinate
        # For vertical lines: group by x-coordinate
        groups: dict[float, list[GraphicLine]] = defaultdict(list)

        for line in lines:
            x0, y0, x1, y1 = line.bbox

            if axis == 'horizontal':
                # Use midpoint y for grouping (handles thin rects)
                key = round((y0 + y1) / 2 / tolerance) * tolerance
            else:  # vertical
                # Use midpoint x for grouping
                key = round((x0 + x1) / 2 / tolerance) * tolerance

            groups[key].append(line)

        merged: list[GraphicLine] = []

        for coord_key, group_lines in groups.items():
            # Merge connected segments in this group
            merged_group = self._merge_connected_segments(
                group_lines, axis, coord_key, tolerance
            )
            merged.extend(merged_group)

        return merged

    def _merge_connected_segments(
        self,
        lines: list[GraphicLine],
        axis: str,
        perpendicular_coord: float,
        tolerance: float
    ) -> list[GraphicLine]:
        """
        Merge line segments that touch or overlap along a single axis line.

        Args:
            lines: Lines on the same axis line (same y for horizontal, same x for vertical)
            axis: 'horizontal' or 'vertical'
            perpendicular_coord: The shared coordinate (y for horizontal, x for vertical) - used for grouping only
            tolerance: Distance tolerance for considering segments connected

        Returns:
            List of merged line segments
        """
        if len(lines) <= 1:
            return lines

        # Extract segments as (start, end, perp_coord, linewidth, page)
        # IMPORTANT: Preserve the ACTUAL perpendicular coordinate from each line,
        # not the rounded group key, to maintain accurate positioning
        segments: list[tuple[float, float, float, float, int]] = []

        for line in lines:
            x0, y0, x1, y1 = line.bbox

            if axis == 'horizontal':
                start, end = min(x0, x1), max(x0, x1)
                # Use actual Y coordinate (average of y0 and y1 for the line)
                actual_perp = (y0 + y1) / 2
            else:  # vertical
                start, end = min(y0, y1), max(y0, y1)
                # Use actual X coordinate
                actual_perp = (x0 + x1) / 2

            segments.append((start, end, actual_perp, line.linewidth, line.page))

        # Sort by start position
        segments.sort(key=lambda s: s[0])

        # Merge overlapping/touching segments
        # Track actual perpendicular coordinates to compute weighted average for merged lines
        merged: list[GraphicLine] = []
        current_start, current_end, current_perp, current_linewidth, current_page = segments[0]
        current_perp_sum = current_perp * (current_end - current_start)  # Weighted by length
        current_length_sum = current_end - current_start

        for start, end, perp, linewidth, page in segments[1:]:
            # Check if this segment connects with or overlaps current
            if start <= current_end + tolerance:
                # Extend current segment
                segment_length = end - start
                current_perp_sum += perp * segment_length
                current_length_sum += segment_length
                current_end = max(current_end, end)
                current_linewidth = max(current_linewidth, linewidth)
            else:
                # Save current segment and start new one
                # Use weighted average of perpendicular coordinates
                avg_perp = current_perp_sum / current_length_sum if current_length_sum > 0 else current_perp
                merged.append(self._create_line_from_segment(
                    axis, avg_perp, current_start, current_end,
                    current_linewidth, current_page
                ))
                current_start, current_end = start, end
                current_perp = perp
                current_perp_sum = perp * (end - start)
                current_length_sum = end - start
                current_linewidth = linewidth

        # Don't forget the last segment
        avg_perp = current_perp_sum / current_length_sum if current_length_sum > 0 else current_perp
        merged.append(self._create_line_from_segment(
            axis, avg_perp, current_start, current_end,
            current_linewidth, current_page
        ))

        return merged

    def _create_line_from_segment(
        self,
        axis: str,
        perpendicular_coord: float,
        start: float,
        end: float,
        linewidth: float,
        page: int
    ) -> GraphicLine:
        """Create a GraphicLine from segment data."""
        if axis == 'horizontal':
            # Horizontal line: y is fixed, x varies
            return GraphicLine(
                page=page,
                bbox=(start, perpendicular_coord, end, perpendicular_coord),
                linewidth=linewidth
            )
        else:
            # Vertical line: x is fixed, y varies
            return GraphicLine(
                page=page,
                bbox=(perpendicular_coord, start, perpendicular_coord, end),
                linewidth=linewidth
            )

    def _merge_diagonal_lines(
        self,
        lines: list[GraphicLine],
        tolerance: float
    ) -> list[GraphicLine]:
        """
        Merge diagonal lines that are collinear and connected.

        Groups lines by slope and y-intercept, then merges connected segments.

        Args:
            lines: Diagonal lines to merge
            tolerance: Coordinate tolerance

        Returns:
            List of merged diagonal lines
        """
        if not lines:
            return []

        # Group by (slope, intercept) - rounded for tolerance
        # Line equation: y = mx + b, where m is slope and b is y-intercept
        groups: dict[tuple[float, float], list[GraphicLine]] = defaultdict(list)

        for line in lines:
            x0, y0, x1, y1 = line.bbox

            # Calculate slope
            dx = x1 - x0
            dy = y1 - y0

            if abs(dx) < 0.001:  # Nearly vertical, shouldn't be here but handle anyway
                slope_key = float('inf')
                intercept_key = round(x0 / tolerance) * tolerance
            else:
                slope = dy / dx
                # Round slope to reduce floating point issues
                slope_key = round(slope * 100) / 100

                # Calculate y-intercept: b = y - mx
                intercept = y0 - slope * x0
                intercept_key = round(intercept / tolerance) * tolerance

            groups[(slope_key, intercept_key)].append(line)

        merged: list[GraphicLine] = []

        for (slope_key, intercept_key), group_lines in groups.items():
            if len(group_lines) == 1:
                merged.extend(group_lines)
                continue

            # For diagonal lines, merge by projecting onto the line direction
            # and finding connected segments
            merged_group = self._merge_diagonal_segments(
                group_lines, slope_key, tolerance
            )
            merged.extend(merged_group)

        return merged

    def _merge_diagonal_segments(
        self,
        lines: list[GraphicLine],
        slope: float,
        tolerance: float
    ) -> list[GraphicLine]:
        """
        Merge connected diagonal line segments.

        Projects segments onto their direction vector and merges overlapping ones.

        Args:
            lines: Collinear diagonal lines
            slope: The slope of these lines
            tolerance: Connection tolerance

        Returns:
            List of merged diagonal lines
        """
        if len(lines) <= 1:
            return lines

        # For diagonal lines, project onto the x-axis for simplicity
        # (could also project onto the line direction for more accuracy)
        # Tuple: (x0, y0, x1, y1, linewidth, page)
        segments: list[tuple[float, float, float, float, float, int]] = []

        for line in lines:
            x0, y0, x1, y1 = line.bbox
            # Ensure x0 <= x1 for consistent ordering
            if x0 > x1:
                x0, y0, x1, y1 = x1, y1, x0, y0
            segments.append((x0, y0, x1, y1, line.linewidth, line.page))

        # Sort by x0 (start x)
        segments.sort(key=lambda s: s[0])

        merged: list[GraphicLine] = []
        curr_x0, curr_y0, curr_x1, curr_y1, curr_lw, curr_page = segments[0]

        for x0, y0, x1, y1, lw, page in segments[1:]:
            # Check if segments connect (x0 of next ≈ x1 of current)
            if x0 <= curr_x1 + tolerance:
                # Extend current segment
                if x1 > curr_x1:
                    curr_x1, curr_y1 = x1, y1
                curr_lw = max(curr_lw, lw)
            else:
                # Save current and start new
                merged.append(GraphicLine(
                    page=curr_page,
                    bbox=(curr_x0, curr_y0, curr_x1, curr_y1),
                    linewidth=curr_lw
                ))
                curr_x0, curr_y0, curr_x1, curr_y1 = x0, y0, x1, y1
                curr_lw = lw

        # Don't forget the last segment
        merged.append(GraphicLine(
            page=curr_page,
            bbox=(curr_x0, curr_y0, curr_x1, curr_y1),
            linewidth=curr_lw
        ))

        return merged
