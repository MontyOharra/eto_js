"""
PDF Files Mappers
Convert between domain dataclasses and API Pydantic models
"""
from shared.types.pdf_files import PdfFile, PdfObjects, TextWord, GraphicRect, GraphicLine, GraphicCurve, Image, Table
from api.schemas.pdf_files import (
    PdfFile as PdfFilePydantic,
    GetPdfObjectsResponse,
    ProcessPdfObjectsResponse,
    PdfObjects as PdfObjectsPydantic,
    TextWord as TextWordPydantic,
    GraphicRect as GraphicRectPydantic,
    GraphicLine as GraphicLinePydantic,
    GraphicCurve as GraphicCurvePydantic,
    Image as ImagePydantic,
    Table as TablePydantic,
)

# ========== Domain → API (Response) Conversions ==========

def pdf_file_to_api(pdf: PdfFile) -> PdfFilePydantic:
    """Convert domain PdfFile to API PdfFile schema"""
    return PdfFilePydantic(
        id=pdf.id,
        email_id=pdf.email_id,
        original_filename=pdf.original_filename,
        file_hash=pdf.file_hash,
        file_size_bytes=pdf.file_size_bytes,
        file_path=pdf.file_path,
        page_count=pdf.page_count,
        stored_at=pdf.stored_at.isoformat(),
        extracted_objects=convert_pdf_objects(pdf.extracted_objects)
    )


def convert_pdf_objects(objects: PdfObjects) -> PdfObjectsPydantic:
    """Convert domain PdfObjects to API PdfObjects schema"""
    return PdfObjectsPydantic(
        text_words=[
            TextWordPydantic(
                page=obj.page,
                bbox=obj.bbox,
                text=obj.text,
                fontname=obj.fontname,
                fontsize=obj.fontsize
            )
            for obj in objects.text_words
        ],
        graphic_rects=[
            GraphicRectPydantic(page=obj.page, bbox=obj.bbox, linewidth=obj.linewidth)
            for obj in objects.graphic_rects
        ],
        graphic_lines=[
            GraphicLinePydantic(page=obj.page, bbox=obj.bbox, linewidth=obj.linewidth)
            for obj in objects.graphic_lines
        ],
        graphic_curves=[
            GraphicCurvePydantic(
                page=obj.page,
                bbox=obj.bbox,
                points=list(obj.points),
                linewidth=obj.linewidth
            )
            for obj in objects.graphic_curves
        ],
        images=[
            ImagePydantic(
                page=obj.page,
                bbox=obj.bbox,
                format=obj.format,
                colorspace=obj.colorspace,
                bits=obj.bits
            )
            for obj in objects.images
        ],
        tables=[
            TablePydantic(
                page=obj.page,
                bbox=obj.bbox,
                rows=obj.rows,
                cols=obj.cols
            )
            for obj in objects.tables
        ]
    )


def convert_pdf_objects_response(
    pdf_file_id: int,
    page_count: int,
    objects: PdfObjects
) -> GetPdfObjectsResponse:
    """Convert domain data to GetPdfObjectsResponse"""
    return GetPdfObjectsResponse(
        pdf_file_id=pdf_file_id,
        page_count=page_count,
        objects=convert_pdf_objects(objects)
    )


def convert_process_pdf_objects_response(
    page_count: int,
    objects: PdfObjects
) -> ProcessPdfObjectsResponse:
    """Convert domain data to ProcessPdfObjectsResponse"""
    return ProcessPdfObjectsResponse(
        page_count=page_count,
        objects=convert_pdf_objects(objects)
    )
