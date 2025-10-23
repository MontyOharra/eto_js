from dataclasses import dataclass, asdict
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
class TextLine:
    """Single text line boundary"""
    page: int
    bbox: tuple[float, float, float, float]


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
class PdfExtractedObjects:
    """
    Container for all extracted PDF objects, grouped by type.
    Replaces raw dict with strongly-typed structure.
    """
    text_words: list[TextWord]
    text_lines: list[TextLine]
    graphic_rects: list[GraphicRect]
    graphic_lines: list[GraphicLine]
    graphic_curves: list[GraphicCurve]
    images: list[Image]
    tables: list[Table]


# ========== Serialization Helpers ==========

def serialize_extracted_objects(objects: PdfExtractedObjects) -> dict:
    """
    Convert PdfExtractedObjects dataclass to dict for JSON serialization.
    Used by repository before storing in database.
    """
    return asdict(objects)


def deserialize_extracted_objects(objects_dict: dict) -> PdfExtractedObjects:
    """
    Convert dict from JSON to PdfExtractedObjects dataclass.
    Used by repository after loading from database.

    Validates structure and raises ValueError if invalid.
    """
    return PdfExtractedObjects(
        text_words=[
            TextWord(
                page=obj["page"],
                bbox=tuple(obj["bbox"]),
                text=obj["text"],
                fontname=obj["fontname"],
                fontsize=obj["fontsize"]
            )
            for obj in objects_dict.get("text_words", [])
        ],
        text_lines=[
            TextLine(
                page=obj["page"],
                bbox=tuple(obj["bbox"])
            )
            for obj in objects_dict.get("text_lines", [])
        ],
        graphic_rects=[
            GraphicRect(
                page=obj["page"],
                bbox=tuple(obj["bbox"]),
                linewidth=obj["linewidth"]
            )
            for obj in objects_dict.get("graphic_rects", [])
        ],
        graphic_lines=[
            GraphicLine(
                page=obj["page"],
                bbox=tuple(obj["bbox"]),
                linewidth=obj["linewidth"]
            )
            for obj in objects_dict.get("graphic_lines", [])
        ],
        graphic_curves=[
            GraphicCurve(
                page=obj["page"],
                bbox=tuple(obj["bbox"]),
                points=[tuple(pt) for pt in obj["points"]],
                linewidth=obj["linewidth"]
            )
            for obj in objects_dict.get("graphic_curves", [])
        ],
        images=[
            Image(
                page=obj["page"],
                bbox=tuple(obj["bbox"]),
                format=obj["format"],
                colorspace=obj["colorspace"],
                bits=obj["bits"]
            )
            for obj in objects_dict.get("images", [])
        ],
        tables=[
            Table(
                page=obj["page"],
                bbox=tuple(obj["bbox"]),
                rows=obj["rows"],
                cols=obj["cols"]
            )
            for obj in objects_dict.get("tables", [])
        ]
    )


# ========== PDF Metadata Dataclasses ==========

@dataclass(frozen=True)
class PdfMetadata:
    """
    Complete PDF metadata (database record).
    Used by services and repositories for PDF file data.

    The extracted_objects field contains strongly-typed PDF objects grouped by type.
    """
    id: int
    email_id: int | None
    original_filename: str
    file_hash: str
    file_size_bytes: int
    file_path: str
    page_count: int | None
    stored_at: datetime
    extracted_objects: PdfExtractedObjects
    created_at: datetime
    updated_at: datetime


@dataclass(frozen=True)
class PdfCreate:
    """
    Data for creating a new PDF record.
    Used by store_pdf service method.

    The extracted_objects field contains strongly-typed PDF objects grouped by type.
    """
    original_filename: str
    file_hash: str
    file_size_bytes: int
    file_path: str
    email_id: int | None
    stored_at: datetime
    extracted_objects: PdfExtractedObjects
    page_count: int | None = None
