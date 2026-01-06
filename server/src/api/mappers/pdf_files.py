"""
PDF Files Mappers

Convert between domain types and API response schemas.
Since domain types are now Pydantic models, most conversions are pass-through.
"""
from shared.types.pdf_files import PdfFile, PdfObjects
from api.schemas.pdf_files import (
    PdfFileResponse,
    GetPdfObjectsResponse,
    ProcessPdfObjectsResponse,
)


def pdf_file_to_api(pdf: PdfFile) -> PdfFileResponse:
    """
    Convert domain PdfFile to API PdfFileResponse.

    Main conversion: datetime → ISO 8601 string for stored_at.
    PdfObjects is now a shared type, no conversion needed.
    """
    return PdfFileResponse(
        id=pdf.id,
        original_filename=pdf.original_filename,
        file_hash=pdf.file_hash,
        file_size_bytes=pdf.file_size_bytes,
        file_path=pdf.file_path,
        page_count=pdf.page_count,
        stored_at=pdf.stored_at.isoformat(),
        extracted_objects=pdf.extracted_objects,  # Same type, no conversion
    )


def convert_pdf_objects_response(
    pdf_file_id: int,
    page_count: int,
    objects: PdfObjects
) -> GetPdfObjectsResponse:
    """Build GetPdfObjectsResponse from parts."""
    return GetPdfObjectsResponse(
        pdf_file_id=pdf_file_id,
        page_count=page_count,
        objects=objects,  # Same type, no conversion
    )


def convert_process_pdf_objects_response(
    page_count: int,
    objects: PdfObjects
) -> ProcessPdfObjectsResponse:
    """Build ProcessPdfObjectsResponse from parts."""
    return ProcessPdfObjectsResponse(
        page_count=page_count,
        objects=objects,  # Same type, no conversion
    )
