"""
PDF Data Extraction Utilities for ETO Process

Core extraction logic shared between:
- ETO process (via EtoRunsService._process_data_extraction)
- Template simulation (via PdfTemplateService.simulate)
"""
import logging
from typing import TypedDict

from features.pdf_files.service import PdfFilesService
from shared.types.pdf_templates import ExtractionField
from shared.types.pdf_files import PdfObjects

logger = logging.getLogger(__name__)


class ExtractedFieldData(TypedDict):
    """Single extraction field result with bbox for visual display"""
    name: str
    description: str | None
    bbox: tuple[float, float, float, float]
    page: int
    extracted_value: str


def extract_data_from_pdf(
    pdf_file_service: 'PdfFilesService',
    pdf_file_id: int,
    extraction_fields: list['ExtractionField']
) -> list[ExtractedFieldData]:
    """
    Extract text from PDF using extraction fields.

    This is the CORE extraction logic used by both:
    - ETO process (via EtoRunsService)
    - Simulate endpoint (via PdfTemplateService)

    Args:
        pdf_file_service: PDF files service for accessing PDF objects
        pdf_file_id: PDF file ID to extract from
        extraction_fields: List of ExtractionField domain objects

    Returns:
        List of ExtractedFieldData with name, bbox, page, and extracted value
    """
    from features.pdf_files.utils.extraction import extract_text_from_bbox

    logger.debug(f"Extracting data from PDF file {pdf_file_id} with {len(extraction_fields)} fields")

    # Get PDF objects from file
    pdf_objects = pdf_file_service.get_pdf_objects(pdf_file_id)

    # Extract text using same logic as simulate endpoint
    extraction_results: list[ExtractedFieldData] = []
    for field in extraction_fields:
        # Convert domain TextWord objects to dict format for extraction utility
        text_words_dicts = [
            {
                "page": word.page,
                "bbox": word.bbox,
                "text": word.text
            }
            for word in pdf_objects.text_words
            if word.page == field.page
        ]

        # Extract text using existing utility
        extracted_text = extract_text_from_bbox(
            text_words=text_words_dicts,
            bbox=field.bbox,
            page=field.page
        )

        # Build full extraction result with bbox data
        extraction_results.append({
            "name": field.name,
            "description": field.description,
            "bbox": field.bbox,
            "page": field.page,
            "extracted_value": extracted_text
        })
        logger.debug(f"Field '{field.name}' extracted: '{extracted_text}'")

    return extraction_results


def extract_data_from_pdf_objects(
    pdf_objects: PdfObjects,
    extraction_fields: list['ExtractionField']
) -> list[ExtractedFieldData]:
    """
    Extract text from PDF objects using extraction fields.

    Alternative version that accepts PDF objects directly instead of fetching them.
    Used by template simulation where PDF objects are already loaded.

    Args:
        pdf_objects: PdfObjects domain object with text_words
        extraction_fields: List of ExtractionField domain objects

    Returns:
        List of ExtractedFieldData with name, bbox, page, and extracted value
    """
    from features.pdf_files.utils.extraction import extract_text_from_bbox

    logger.debug(f"Extracting data from PDF objects with {len(extraction_fields)} fields")

    # Extract text using same logic
    extraction_results: list[ExtractedFieldData] = []
    for field in extraction_fields:
        # Convert domain TextWord objects to dict format for extraction utility
        text_words_dicts = [
            {
                "page": word.page,
                "bbox": word.bbox,
                "text": word.text
            }
            for word in pdf_objects.text_words
            if word.page == field.page
        ]

        # Extract text using existing utility
        extracted_text = extract_text_from_bbox(
            text_words=text_words_dicts,
            bbox=field.bbox,
            page=field.page
        )

        # Build full extraction result with bbox data
        extraction_results.append({
            "name": field.name,
            "description": field.description,
            "bbox": field.bbox,
            "page": field.page,
            "extracted_value": extracted_text
        })
        logger.debug(f"Field '{field.name}' extracted: '{extracted_text}'")

    return extraction_results
