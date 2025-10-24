from dataclasses import dataclass, asdict
from datetime import datetime
from typing import Any


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
class PdfObjects:
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
    extracted_objects: PdfObjects
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
    extracted_objects: PdfObjects
    page_count: int | None = None


# ========== Serialization Helpers ==========

def serialize_pdf_objects(obj: PdfObjects) -> dict[str, Any]:
    """
    Convert PdfObjects dataclass to JSON-serializable dict.

    Uses dataclasses.asdict to recursively convert all nested dataclasses.
    Tuples (like bbox) are automatically converted to lists.
    """
    return asdict(obj)


def deserialize_pdf_objects(data: dict[str, Any]) -> PdfObjects:
    """
    Convert dict back to PdfObjects dataclass.

    Reconstructs all nested dataclasses from dict representation.
    Lists are converted back to appropriate dataclass types.
    """
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
        text_lines=[
            TextLine(
                page=l["page"],
                bbox=tuple(l["bbox"])
            )
            for l in data.get("text_lines", [])
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
