"""
PDF Files API Schemas
Pydantic models for PDF file access endpoints
"""
from typing import Optional, List, Tuple
from pydantic import BaseModel


# Nested Object Schemas
class TextWord(BaseModel):
    page: int
    bbox: Tuple[float, float, float, float]  # [x0, y0, x1, y1]
    text: str
    fontname: str
    fontsize: float


class GraphicRect(BaseModel):
    page: int
    bbox: Tuple[float, float, float, float]  # [x0, y0, x1, y1]
    linewidth: float


class GraphicLine(BaseModel):
    page: int
    bbox: Tuple[float, float, float, float]  # [x0, y0, x1, y1]
    linewidth: float


class GraphicCurve(BaseModel):
    page: int
    bbox: Tuple[float, float, float, float]  # [x0, y0, x1, y1]
    points: List[Tuple[float, float]]  # Array of [x, y] coordinate pairs
    linewidth: float


class Image(BaseModel):
    page: int
    bbox: Tuple[float, float, float, float]  # [x0, y0, x1, y1]
    format: str  # e.g., "JPEG", "PNG"
    colorspace: str  # e.g., "RGB", "CMYK"
    bits: int  # Bit depth


class Table(BaseModel):
    page: int
    bbox: Tuple[float, float, float, float]  # [x0, y0, x1, y1]
    rows: int
    cols: int


class PdfObjects(BaseModel):
    text_words: List[TextWord]
    graphic_rects: List[GraphicRect]
    graphic_lines: List[GraphicLine]
    graphic_curves: List[GraphicCurve]
    images: List[Image]
    tables: List[Table]



class PdfFile(BaseModel):
    """
    Complete PDF File API schema (matches domain PdfFile).
    Used for GET /pdf-files/{id} endpoint response.

    Note:
    - created_at/updated_at are audit fields and not included in API responses
    - Source tracking (email/manual) moved to eto_runs table
    """
    id: int
    original_filename: str
    file_hash: str
    file_size_bytes: int
    file_path: str
    page_count: Optional[int] = None
    stored_at: str  # ISO 8601
    extracted_objects: PdfObjects



class GetPdfObjectsResponse(BaseModel):
    pdf_file_id: int
    page_count: int
    objects: PdfObjects


# POST /pdf-files/process-objects - Process Objects Response
class ProcessPdfObjectsResponse(BaseModel):
    page_count: int
    objects: PdfObjects