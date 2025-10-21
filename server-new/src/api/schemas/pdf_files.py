"""
PDF Files API Schemas
Pydantic models for PDF file access endpoints
"""
from typing import Optional, List, Tuple
from pydantic import BaseModel


# GET /pdf-files/{id} - Metadata Response
class GetPdfMetadataResponse(BaseModel):
    id: int
    email_id: Optional[int] = None
    filename: str
    original_filename: str
    relative_path: str
    file_size: Optional[int] = None  # bytes
    file_hash: Optional[str] = None
    page_count: Optional[int] = None


# GET /pdf-files/{id}/download
# Returns StreamingResponse with raw PDF bytes - no Pydantic model needed


# GET /pdf-files/{id}/objects - Objects Response
class TextWordObject(BaseModel):
    page: int
    bbox: Tuple[float, float, float, float]  # [x0, y0, x1, y1]
    text: str
    fontname: str
    fontsize: float


class TextLineObject(BaseModel):
    page: int
    bbox: Tuple[float, float, float, float]  # [x0, y0, x1, y1]


class GraphicRectObject(BaseModel):
    page: int
    bbox: Tuple[float, float, float, float]  # [x0, y0, x1, y1]
    linewidth: float


class GraphicLineObject(BaseModel):
    page: int
    bbox: Tuple[float, float, float, float]  # [x0, y0, x1, y1]
    linewidth: float


class GraphicCurveObject(BaseModel):
    page: int
    bbox: Tuple[float, float, float, float]  # [x0, y0, x1, y1]
    points: List[Tuple[float, float]]  # Array of [x, y] coordinate pairs
    linewidth: float


class ImageObject(BaseModel):
    page: int
    bbox: Tuple[float, float, float, float]  # [x0, y0, x1, y1]
    format: str  # e.g., "JPEG", "PNG"
    colorspace: str  # e.g., "RGB", "CMYK"
    bits: int  # Bit depth


class TableObject(BaseModel):
    page: int
    bbox: Tuple[float, float, float, float]  # [x0, y0, x1, y1]
    rows: int
    cols: int


class PdfObjects(BaseModel):
    text_words: List[TextWordObject]
    text_lines: List[TextLineObject]
    graphic_rects: List[GraphicRectObject]
    graphic_lines: List[GraphicLineObject]
    graphic_curves: List[GraphicCurveObject]
    images: List[ImageObject]
    tables: List[TableObject]


class GetPdfObjectsResponse(BaseModel):
    pdf_file_id: int
    page_count: int
    objects: PdfObjects


# POST /pdf-files/process-objects - Process Objects Response
class ProcessPdfObjectsResponse(BaseModel):
    page_count: int
    objects: PdfObjects
