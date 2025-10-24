"""
PDF Files Mappers
Convert between domain dataclasses and API Pydantic models
"""
from shared.types.pdf_files import PdfMetadata, PdfObjects as PdfObjectsDomain
from api.schemas.pdf_files import (
    GetPdfMetadataResponse,
    GetPdfObjectsResponse,
    ProcessPdfObjectsResponse,
    PdfObjects as PdfObjectsSchema,
    TextWordObject,
    TextLineObject,
    GraphicRectObject,
    GraphicLineObject,
    GraphicCurveObject,
    ImageObject,
    TableObject,
)

# ========== Domain → API (Response) Conversions ==========

def convert_pdf_metadata(metadata: PdfMetadata) -> GetPdfMetadataResponse:
    """Convert domain PdfMetadata to API GetPdfMetadataResponse"""
    return GetPdfMetadataResponse(
        id=metadata.id,
        email_id=metadata.email_id,
        filename=metadata.original_filename,
        original_filename=metadata.original_filename,
        relative_path=metadata.file_path,
        file_size=metadata.file_size_bytes,
        file_hash=metadata.file_hash,
        page_count=metadata.page_count
    )


def convert_pdf_objects(objects: PdfObjectsDomain) -> PdfObjectsSchema:
    """Convert domain PdfObjects to API PdfObjects schema"""
    return PdfObjectsSchema(
        text_words=[
            TextWordObject(
                page=obj.page,
                bbox=obj.bbox,
                text=obj.text,
                fontname=obj.fontname,
                fontsize=obj.fontsize
            )
            for obj in objects.text_words
        ],
        text_lines=[
            TextLineObject(page=obj.page, bbox=obj.bbox)
            for obj in objects.text_lines
        ],
        graphic_rects=[
            GraphicRectObject(page=obj.page, bbox=obj.bbox, linewidth=obj.linewidth)
            for obj in objects.graphic_rects
        ],
        graphic_lines=[
            GraphicLineObject(page=obj.page, bbox=obj.bbox, linewidth=obj.linewidth)
            for obj in objects.graphic_lines
        ],
        graphic_curves=[
            GraphicCurveObject(
                page=obj.page,
                bbox=obj.bbox,
                points=list(obj.points),
                linewidth=obj.linewidth
            )
            for obj in objects.graphic_curves
        ],
        images=[
            ImageObject(
                page=obj.page,
                bbox=obj.bbox,
                format=obj.format,
                colorspace=obj.colorspace,
                bits=obj.bits
            )
            for obj in objects.images
        ],
        tables=[
            TableObject(
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
    objects: PdfObjectsDomain
) -> GetPdfObjectsResponse:
    """Convert domain data to GetPdfObjectsResponse"""
    return GetPdfObjectsResponse(
        pdf_file_id=pdf_file_id,
        page_count=page_count,
        objects=convert_pdf_objects(objects)
    )


def convert_process_pdf_objects_response(
    page_count: int,
    objects: PdfObjectsDomain
) -> ProcessPdfObjectsResponse:
    """Convert domain data to ProcessPdfObjectsResponse"""
    return ProcessPdfObjectsResponse(
        page_count=page_count,
        objects=convert_pdf_objects(objects)
    )
