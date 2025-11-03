"""
PDF Files API Router
API endpoints for PDF file access and object extraction
"""
import logging
from fastapi import APIRouter, Depends, UploadFile, File, status
from fastapi.responses import Response

from api.schemas.pdf_files import (
    PdfFile,
    GetPdfObjectsResponse,
    ProcessPdfObjectsResponse,
)
from api.mappers.pdf_files import (
    pdf_file_to_api,
    convert_pdf_objects_response,
    convert_process_pdf_objects_response,
)

from shared.services.service_container import ServiceContainer
from features.pdf_files.service import PdfFilesService
from shared.exceptions.service import ValidationError

logger = logging.getLogger(__name__)


router = APIRouter(
    prefix="/pdf-files",
    tags=["PDF Files"]
)


@router.post("", response_model=PdfFile, status_code=status.HTTP_201_CREATED)
async def upload_pdf_file(
    pdf_file: UploadFile = File(...),
    pdf_service: PdfFilesService = Depends(lambda: ServiceContainer.get_pdf_files_service())
) -> PdfFile:
    """
    Upload and store PDF file with automatic object extraction.

    Process:
    - Validates PDF format
    - Calculates SHA-256 hash for deduplication
    - Stores file in date-based directory structure (YYYY/MM/DD/hash.pdf)
    - Extracts objects using pdfplumber
    - Returns complete PDF metadata

    Note: email_id is not accepted here - only set by email ingestion service
    """
    # Validate file type
    if not pdf_file.filename or not pdf_file.filename.endswith('.pdf'):
        raise ValidationError("Invalid file type - must be a PDF")

    # Read file bytes
    pdf_bytes = await pdf_file.read()

    # Store PDF (service handles validation, extraction, deduplication)
    pdf = pdf_service.store_pdf(
        file_bytes=pdf_bytes,
        filename=pdf_file.filename,
        email_id=None  # Manual uploads have no email association
    )

    return pdf_file_to_api(pdf)


@router.get("/{id}", response_model=PdfFile)
async def get_pdf_file(
    id: int,
    pdf_service: PdfFilesService = Depends(
        lambda: ServiceContainer.get_pdf_files_service()
    )
) -> PdfFile:
    """Get PDF file metadata (filename, size, page count, etc.)"""
    pdf = pdf_service.get_pdf_file(id)
    return pdf_file_to_api(pdf)


@router.get("/{id}/download")
async def download_pdf(
    id: int,
    pdf_service: PdfFilesService = Depends(
        lambda: ServiceContainer.get_pdf_files_service()
    )
):
    """Download or stream PDF file bytes for viewing"""
    file_bytes, filename = pdf_service.get_pdf_file_bytes(id)

    return Response(
        content=file_bytes,
        media_type="application/pdf",
        headers={
            "Content-Disposition": f'inline; filename="{filename}"'
        }
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
    objects = pdf_service.get_pdf_objects(id, object_type)
    pdf = pdf_service.get_pdf_file(id)
    return convert_pdf_objects_response(
        pdf_file_id=id,
        page_count=pdf.page_count or 0,
        objects=objects
    )


@router.post("/process-objects", response_model=ProcessPdfObjectsResponse)
async def process_pdf_objects(
    pdf_file: UploadFile = File(...),
    pdf_service: PdfFilesService = Depends(
        lambda: ServiceContainer.get_pdf_files_service()
    )
) -> ProcessPdfObjectsResponse:
    """Process uploaded PDF and extract objects (no persistence)"""
    # Validate file upload
    if not pdf_file or not pdf_file.filename or not pdf_file.filename.endswith('.pdf'):
        raise ValidationError("Missing PDF file or invalid file type")

    # Read file bytes
    pdf_bytes = await pdf_file.read()

    # Extract objects (returns typed PdfObjects)
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

    return convert_process_pdf_objects_response(
        page_count=page_count,
        objects=objects
    )
