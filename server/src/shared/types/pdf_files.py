from dataclasses import dataclass
from datetime import datetime


# ========== PDF Object Type Dataclasses ==========

@dataclass(frozen=True)
class TextWord:
    """Single text word extracted from PDF"""
    page: int
    bbox: tuple[float, float, float, float]  # (x0, y0, x1, y1)
    text: str
    fontname: str
    fontsize: float


@dataclass(frozen=True)
class GraphicRect:
    """Rectangle graphic object"""
    page: int
    bbox: tuple[float, float, float, float]
    linewidth: float


@dataclass(frozen=True)
class GraphicLine:
    """Line graphic object"""
    page: int
    bbox: tuple[float, float, float, float]
    linewidth: float


@dataclass(frozen=True)
class GraphicCurve:
    """Curve graphic object with control points"""
    page: int
    bbox: tuple[float, float, float, float]
    points: list[tuple[float, float]]  # Array of (x, y) coordinate pairs
    linewidth: float


@dataclass(frozen=True)
class Image:
    """Image object with metadata"""
    page: int
    bbox: tuple[float, float, float, float]
    format: str  # e.g., "JPEG", "PNG"
    colorspace: str  # e.g., "RGB", "CMYK"
    bits: int  # Bit depth


@dataclass(frozen=True)
class Table:
    """Table structure with dimensions"""
    page: int
    bbox: tuple[float, float, float, float]
    rows: int
    cols: int


@dataclass(frozen=True)
class PdfObjects:
    """
    Container for all extracted PDF objects, grouped by type.
    Replaces raw dict with strongly-typed structure.
    """
    text_words: list[TextWord]
    graphic_rects: list[GraphicRect]
    graphic_lines: list[GraphicLine]
    graphic_curves: list[GraphicCurve]
    images: list[Image]
    tables: list[Table]

# ========== PDF File Dataclasses ==========

@dataclass(frozen=True)
class PdfFile:
    """
    Complete PDF File (database record).
    Used by services and repositories for PDF file data.

    The extracted_objects field contains strongly-typed PDF objects grouped by type.

    Note: Source tracking (email/manual) is now handled at the eto_runs level,
    not at the PDF file level. PDFs are just storage entities.
    """
    id: int
    original_filename: str
    file_hash: str
    file_size_bytes: int
    file_path: str
    page_count: int | None
    stored_at: datetime
    extracted_objects: PdfObjects
    created_at: datetime
    updated_at: datetime


@dataclass(frozen=True)
class PdfFileCreate:
    """
    Data for creating a new PDF record.
    Used by store_pdf service method.

    The extracted_objects field contains strongly-typed PDF objects grouped by type.

    Note: email_id removed - source tracking now handled at eto_runs level.
    """
    original_filename: str
    file_hash: str
    file_size_bytes: int
    file_path: str
    stored_at: datetime
    extracted_objects: PdfObjects
    page_count: int | None = None
