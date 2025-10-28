"""
PDF Text Extraction Utilities
Extract text from PDF using bounding boxes for data extraction
"""
import logging
from typing import List, Dict, Tuple, Any

logger = logging.getLogger(__name__)


# Type alias for bbox coordinates
BBox = Tuple[float, float, float, float]  # [x0, y0, x1, y1]


def extract_text_from_bbox(
    text_words: List[Dict[str, Any]],
    bbox: BBox,
    page: int
) -> str:
    """
    Extract and concatenate text from words within a bounding box.

    Args:
        text_words: List of text word objects from PDF (pdfplumber format)
                   Each word should have: page, bbox, text
        bbox: [x0, y0, x1, y1] coordinates of extraction area
        page: Page number (1-indexed)

    Returns:
        Concatenated text from all words within the bounding box

    Example word dict:
        {
            "type": "text_word",
            "page": 1,
            "bbox": [100.0, 200.0, 150.0, 220.0],
            "text": "HAWB",
            "fontname": "Arial",
            "fontsize": 12.0
        }
    """
    logger.debug(f"Extracting text from bbox {bbox} on page {page}")

    # Filter words by page
    page_words = [word for word in text_words if word.get("page") == page]
    logger.debug(f"Found {len(page_words)} text words on page {page}")

    # Find words within bounding box
    words_in_box = []
    for word in page_words:
        if _is_word_in_bbox(word, bbox):
            words_in_box.append(word)

    logger.debug(f"Found {len(words_in_box)} words within bounding box")

    if not words_in_box:
        logger.debug(f"No words found in bounding box {bbox} on page {page}")
        return ""

    # Sort words by position (top to bottom, left to right)
    # pdfplumber coordinates: y=0 at top, so sort by Y ascending
    words_in_box.sort(key=lambda w: (w["bbox"][1], w["bbox"][0]))

    # Group words into lines based on y-coordinate proximity
    lines = _group_words_into_lines(words_in_box, y_tolerance=5.0)

    # Build the final text
    result_lines = []
    for line in lines:
        # Sort words in line by x-coordinate
        line.sort(key=lambda w: w["bbox"][0])
        # Join words with spaces
        line_text = " ".join(word["text"] for word in line)
        result_lines.append(line_text)

    # Join lines with newlines and clean up
    result = "\n".join(result_lines)
    return result.strip()


def _is_word_in_bbox(
    word: Dict[str, Any],
    bbox: BBox,
    tolerance: float = 2.0
) -> bool:
    """
    Check if a text word falls within an extraction field's bounding box.

    Uses overlap-based checking: word is considered inside if it has
    significant overlap with the extraction field.

    Args:
        word: Text word dict with bbox
        bbox: [x0, y0, x1, y1] extraction field coordinates
        tolerance: Pixel tolerance for boundary checking

    Returns:
        True if word is within the bounding box, False otherwise
    """
    # Extract coordinates with tolerance
    field_x0, field_y0, field_x1, field_y1 = bbox
    field_x0 -= tolerance
    field_y0 -= tolerance
    field_x1 += tolerance
    field_y1 += tolerance

    word_bbox = word.get("bbox")
    if not word_bbox or len(word_bbox) != 4:
        return False

    word_x0, word_y0, word_x1, word_y1 = word_bbox

    # Check if there's no overlap at all (early exit)
    if (word_x1 < field_x0 or word_x0 > field_x1 or
        word_y1 < field_y0 or word_y0 > field_y1):
        return False

    # Calculate overlap area
    overlap_x0 = max(word_x0, field_x0)
    overlap_y0 = max(word_y0, field_y0)
    overlap_x1 = min(word_x1, field_x1)
    overlap_y1 = min(word_y1, field_y1)

    overlap_area = (overlap_x1 - overlap_x0) * (overlap_y1 - overlap_y0)
    word_area = (word_x1 - word_x0) * (word_y1 - word_y0)

    # Consider word inside if >50% overlap OR if center point is inside
    overlap_ratio = overlap_area / word_area if word_area > 0 else 0

    # Also check if word center is within field
    word_center_x = (word_x0 + word_x1) / 2
    word_center_y = (word_y0 + word_y1) / 2
    center_inside = (field_x0 <= word_center_x <= field_x1 and
                    field_y0 <= word_center_y <= field_y1)

    return overlap_ratio > 0.5 or center_inside


def _group_words_into_lines(
    words: List[Dict[str, Any]],
    y_tolerance: float = 5.0
) -> List[List[Dict[str, Any]]]:
    """
    Group words into lines based on y-coordinate proximity.

    Args:
        words: List of word dicts (already sorted)
        y_tolerance: Tolerance for considering words on the same line

    Returns:
        List of lines, where each line is a list of word dicts
    """
    lines = []
    current_line = []
    current_y = None

    for word in words:
        word_bbox = word.get("bbox")
        if not word_bbox:
            continue

        word_y = (word_bbox[1] + word_bbox[3]) / 2  # Use center y-coordinate

        if current_y is None or abs(word_y - current_y) <= y_tolerance:
            current_line.append(word)
            if current_y is None:
                current_y = word_y
        else:
            # New line detected
            if current_line:
                lines.append(current_line)
            current_line = [word]
            current_y = word_y

    # Add the last line
    if current_line:
        lines.append(current_line)

    return lines


def extract_data_from_pdf_objects(
    pdf_objects: List[Dict[str, Any]],
    extraction_fields: List[Dict[str, Any]]
) -> Dict[str, str]:
    """
    Extract data from PDF objects using extraction fields.

    Args:
        pdf_objects: List of PDF object dicts (from pdfplumber extraction)
        extraction_fields: List of extraction field dicts with:
            - name: Field name
            - bbox: [x0, y0, x1, y1]
            - page: Page number (1-indexed)

    Returns:
        Dict mapping field names to extracted text

    Example:
        extraction_fields = [
            {"name": "hawb", "bbox": [100, 200, 300, 220], "page": 1},
            {"name": "weight", "bbox": [100, 250, 200, 270], "page": 1}
        ]

        Returns: {"hawb": "ABC123", "weight": "150.5"}
    """
    # Filter for text_word objects
    text_words = [obj for obj in pdf_objects if obj.get("type") == "text_word"]

    extracted_data: Dict[str, str] = {}

    for field in extraction_fields:
        field_name = field.get("name")
        bbox = field.get("bbox")
        page = field.get("page")

        if not field_name or not bbox or page is None:
            logger.warning(f"Skipping invalid extraction field: {field}")
            extracted_data[field_name or "unknown"] = ""
            continue

        try:
            extracted_text = extract_text_from_bbox(text_words, tuple(bbox), page)
            extracted_data[field_name] = extracted_text
            logger.debug(f"Field '{field_name}' extracted: '{extracted_text}'")
        except Exception as e:
            logger.error(f"Error extracting field '{field_name}': {e}")
            extracted_data[field_name] = ""

    return extracted_data
