"""
PDF file domain types.
"""
from datetime import datetime

from pydantic import BaseModel, ConfigDict


# ========== PDF Object Types ==========

class TextWord(BaseModel):
    """Single text word extracted from PDF."""
    model_config = ConfigDict(frozen=True)

    page: int
    bbox: tuple[float, float, float, float]  # (x0, y0, x1, y1)
    text: str
    fontname: str
    fontsize: float


class GraphicRect(BaseModel):
    """Rectangle graphic object."""
    model_config = ConfigDict(frozen=True)

    page: int
    bbox: tuple[float, float, float, float]
    linewidth: float


class GraphicLine(BaseModel):
    """Line graphic object."""
    model_config = ConfigDict(frozen=True)

    page: int
    bbox: tuple[float, float, float, float]
    linewidth: float


class GraphicCurve(BaseModel):
    """Curve graphic object with control points."""
    model_config = ConfigDict(frozen=True)

    page: int
    bbox: tuple[float, float, float, float]
    points: list[tuple[float, float]]  # Array of (x, y) coordinate pairs
    linewidth: float


class Image(BaseModel):
    """Image object with metadata."""
    model_config = ConfigDict(frozen=True)

    page: int
    bbox: tuple[float, float, float, float]
    format: str  # e.g., "JPEG", "PNG"
    colorspace: str  # e.g., "RGB", "CMYK"
    bits: int  # Bit depth


class Table(BaseModel):
    """Table structure with dimensions."""
    model_config = ConfigDict(frozen=True)

    page: int
    bbox: tuple[float, float, float, float]
    rows: int
    cols: int


class PdfObjects(BaseModel):
    """Container for all extracted PDF objects, grouped by type."""
    model_config = ConfigDict(frozen=True)

    text_words: list[TextWord]
    graphic_rects: list[GraphicRect]
    graphic_lines: list[GraphicLine]
    graphic_curves: list[GraphicCurve]
    images: list[Image]
    tables: list[Table]


# ========== PDF File Types ==========

class PdfFile(BaseModel):
    """
    Complete PDF File (database record).

    The extracted_objects field contains strongly-typed PDF objects grouped by type.

    Note: Source tracking (email/manual) is now handled at the eto_runs level,
    not at the PDF file level. PDFs are just storage entities.
    """
    model_config = ConfigDict(frozen=True)

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


class PdfFileCreate(BaseModel):
    """
    Data for creating a new PDF record.

    The extracted_objects field contains strongly-typed PDF objects grouped by type.

    Note: email_id removed - source tracking now handled at eto_runs level.
    """
    model_config = ConfigDict(frozen=True)

    original_filename: str
    file_hash: str
    file_size_bytes: int
    file_path: str
    stored_at: datetime
    extracted_objects: PdfObjects
    page_count: int | None = None
