"""
PDF Files API Router
API endpoints for PDF file access and object extraction
"""
import logging
from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File
from fastapi.responses import Response

from api.schemas.pdf_files import (
    GetPdfMetadataResponse,
    GetPdfObjectsResponse,
    ProcessPdfObjectsResponse,
    PdfObjects,
    TextWordObject,
    TextLineObject,
    GraphicRectObject,
    GraphicLineObject,
    GraphicCurveObject,
    ImageObject,
    TableObject,
)

from shared.services.service_container import ServiceContainer
from features.pdf_files.service import PdfFilesService
from shared.types.pdf_files import PdfExtractedObjects
from shared.exceptions import ObjectNotFoundError, ServiceError, ValidationError

logger = logging.getLogger(__name__)


def _convert_to_pydantic_objects(objects: PdfExtractedObjects) -> PdfObjects:
    """Convert dataclass PdfExtractedObjects to Pydantic PdfObjects"""
    return PdfObjects(
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
                page=obj.page, bbox=obj.bbox,
                points=list(obj.points), linewidth=obj.linewidth
            )
            for obj in objects.graphic_curves
        ],
        images=[
            ImageObject(
                page=obj.page, bbox=obj.bbox,
                format=obj.format, colorspace=obj.colorspace, bits=obj.bits
            )
            for obj in objects.images
        ],
        tables=[
            TableObject(page=obj.page, bbox=obj.bbox, rows=obj.rows, cols=obj.cols)
            for obj in objects.tables
        ]
    )

router = APIRouter(
    prefix="/pdf-files",
    tags=["PDF Files"]
)


@router.get("/{id}", response_model=GetPdfMetadataResponse)
async def get_pdf_metadata(
    id: int,
    pdf_service: PdfFilesService = Depends(
        lambda: ServiceContainer.get_pdf_files_service()
    )
) -> GetPdfMetadataResponse:
    """Get PDF file metadata (filename, size, page count, etc.)"""

    try:
        metadata = pdf_service.get_pdf_metadata(id)

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

    except ObjectNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"PDF file {id} not found"
        )


@router.get("/{id}/download")
async def download_pdf(
    id: int,
    pdf_service: PdfFilesService = Depends(
        lambda: ServiceContainer.get_pdf_files_service()
    )
):
    """Download or stream PDF file bytes for viewing"""

    try:
        file_bytes, filename = pdf_service.get_pdf_file_bytes(id)

        return Response(
            content=file_bytes,
            media_type="application/pdf",
            headers={
                "Content-Disposition": f'inline; filename="{filename}"'
            }
        )

    except ObjectNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"PDF file {id} not found"
        )

    except FileNotFoundError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )

    except ServiceError as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


@router.get("/{id}/objects", response_model=GetPdfObjectsResponse)
async def get_pdf_objects(
    id: int,
    object_type: str | None = None,
    pdf_service: PdfFilesService = Depends(
        lambda: ServiceContainer.get_pdf_files_service()
    )
) -> GetPdfObjectsResponse:
    """Get extracted PDF objects for template building"""

    try:
        # Get typed objects from service
        objects = pdf_service.get_pdf_objects(id, object_type)

        # Get metadata for page count
        metadata = pdf_service.get_pdf_metadata(id)

        # Convert dataclasses to Pydantic models
        pydantic_objects = _convert_to_pydantic_objects(objects)

        return GetPdfObjectsResponse(
            pdf_file_id=id,
            page_count=metadata.page_count or 0,
            objects=pydantic_objects
        )

    except ObjectNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"PDF file {id} not found"
        )

    except Exception as e:
        logger.error(f"Error retrieving PDF objects for {id}: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve PDF objects"
        )


@router.post("/process-objects", response_model=ProcessPdfObjectsResponse)
async def process_pdf_objects(
    pdf_file: UploadFile = File(...),
    pdf_service: PdfFilesService = Depends(
        lambda: ServiceContainer.get_pdf_files_service()
    )
) -> ProcessPdfObjectsResponse:
    """Process uploaded PDF and extract objects (no persistence)"""

    try:
        # Validate file upload
        if not pdf_file or not pdf_file.filename or not pdf_file.filename.endswith('.pdf'):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Missing PDF file or invalid file type"
            )

        # Read file bytes
        pdf_bytes = await pdf_file.read()

        # Extract objects (returns typed PdfExtractedObjects)
        objects = pdf_service.extract_objects_from_bytes(
            pdf_bytes,
            pdf_file.filename or "uploaded.pdf"
        )

        # Calculate page count from objects
        page_count = 0
        for obj_list in [
            objects.text_words, objects.text_lines, objects.graphic_rects,
            objects.graphic_lines, objects.graphic_curves, objects.images, objects.tables
        ]:
            for obj in obj_list:
                page_count = max(page_count, obj.page + 1)

        # Convert dataclasses to Pydantic models
        pydantic_objects = _convert_to_pydantic_objects(objects)

        return ProcessPdfObjectsResponse(
            page_count=page_count,
            objects=pydantic_objects
        )

    except ValidationError as e:
        # PDF validation failed (corrupt file, invalid format, etc.)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )

    except ServiceError as e:
        # Infrastructure failure (filesystem, etc.)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )

    except Exception as e:
        logger.error(f"Error processing PDF {pdf_file.filename}: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to process PDF file"
        )
