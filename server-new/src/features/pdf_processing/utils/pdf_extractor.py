"""
Enhanced PDF Object Extraction Service
Extracts comprehensive PDF objects for template creation and matching
Based on proven methods from old extractor with streamlined object models
"""

import pdfplumber
import io
import hashlib
import json
import logging
from typing import List, Dict, Any, Optional, Union, TypedDict, Literal
from io import BytesIO

# pdfplumber type imports
from pdfplumber.page import Page

logger = logging.getLogger(__name__)

# ===== TYPE DEFINITIONS =====

# Coordinate type
BBox = List[float]  # [x0, y0, x1, y1]

def _round(val: Union[float, int, Any], ndigits: int = 3) -> Union[float, int, Any]:
    """Round float values for consistent object comparison"""
    return round(val, ndigits) if isinstance(val, float) else val

# ===== TYPEDDICT DEFINITIONS =====

class BasePdfObjectDict(TypedDict):
    type: str
    page: int
    bbox: BBox

class TextWordDict(BasePdfObjectDict):
    type: Literal["text_word"]
    text: str
    fontname: str
    fontsize: float

class TextLineDict(BasePdfObjectDict):
    type: Literal["text_line"]

class GraphicRectDict(BasePdfObjectDict):
    type: Literal["graphic_rect"]
    linewidth: float

class GraphicLineDict(BasePdfObjectDict):
    type: Literal["graphic_line"]
    linewidth: float

class GraphicCurveDict(BasePdfObjectDict):
    type: Literal["graphic_curve"]
    points: List[List[float]]
    linewidth: float

class ImageDict(BasePdfObjectDict):
    type: Literal["image"]
    format: str
    colorspace: str
    bits: int

class TableDict(BasePdfObjectDict):
    type: Literal["table"]
    rows: int
    cols: int

# Union type for all dict representations
PdfObjectDict = Union[
    TextWordDict,
    TextLineDict,
    GraphicRectDict,
    GraphicLineDict,
    GraphicCurveDict,
    ImageDict,
    TableDict
]

# ===== EXTRACTION RESULT =====

class PdfExtractionResult(TypedDict):
    success: bool
    objects: List[PdfObjectDict]
    signature_hash: str
    page_count: int
    object_count: int
    error_message: Optional[str]

# ===== MAIN EXTRACTOR CLASS =====

class EnhancedPdfObjectExtractor:
    """Service for extracting comprehensive PDF objects for template matching"""

    def __init__(self):
        self.rounding_precision = 3

    def extract_objects_from_file_path(self, file_path: str) -> PdfExtractionResult:
        """Extract objects from PDF file path"""
        try:
            with open(file_path, 'rb') as f:
                pdf_bytes = f.read()
            return self.extract_objects_from_bytes(pdf_bytes)
        except Exception as e:
            logger.error(f"Error reading PDF file {file_path}: {e}")
            return {
                "success": False,
                "error_message": str(e),
                "objects": [],
                "signature_hash": "",
                "page_count": 0,
                "object_count": 0
            }

    def extract_objects_from_bytes(self, pdf_bytes: bytes) -> PdfExtractionResult:
        """
        Extract all PDF objects from bytes and return with signature

        Returns:
            PdfExtractionResult with all extracted objects
        """
        try:
            objects: List[PdfObjectDict] = []

            with pdfplumber.open(io.BytesIO(pdf_bytes)) as pdf:
                page_count = len(pdf.pages)

                for page_num, page in enumerate(pdf.pages, start=1):
                    page_objects = self._extract_page_objects(page, page_num)
                    objects.extend(page_objects)

            # Generate signature hash from objects
            signature_hash = self._generate_signature_hash(objects)

            logger.info(f"Extracted {len(objects)} objects from {page_count} pages. Signature: {signature_hash[:8]}...")

            return {
                "success": True,
                "objects": objects,
                "signature_hash": signature_hash,
                "page_count": page_count,
                "object_count": len(objects),
                "error_message": None
            }

        except Exception as e:
            logger.error(f"Error extracting PDF objects: {e}")
            return {
                "success": False,
                "error_message": str(e),
                "objects": [],
                "signature_hash": "",
                "page_count": 0,
                "object_count": 0
            }

    def _extract_page_objects(self, page: Page, page_num: int) -> List[PdfObjectDict]:
        """Extract all objects from a single page using proven methods"""
        objects: List[PdfObjectDict] = []

        # 1. Text Words (using old method)
        words = page.extract_words(x_tolerance=3, y_tolerance=3)
        for word in words:
            word_obj = self._extract_text_word_object(word, page_num)
            if word_obj:
                objects.append(word_obj)

        # 2. Text Lines (using old method)
        lines = page.extract_text_lines(layout=True)
        for line in lines:
            line_obj = self._extract_text_line_object(line, page_num)
            if line_obj:
                objects.append(line_obj)

        # 3. Rectangles (using old method)
        for rect in page.rects:
            rect_obj = self._extract_graphic_rect_object(rect, page_num)
            if rect_obj:
                objects.append(rect_obj)

        # 4. Graphic Lines (using old method)
        for line in page.lines:
            line_obj = self._extract_graphic_line_object(line, page_num)
            if line_obj:
                objects.append(line_obj)

        # 5. Curves (using old method)
        for curve in page.curves:
            curve_obj = self._extract_graphic_curve_object(curve, page_num)
            if curve_obj:
                objects.append(curve_obj)

        # 6. Images (using old method)
        for image in page.images:
            image_obj = self._extract_image_object(image, page_num)
            if image_obj:
                objects.append(image_obj)

        # 7. Tables (using old method - need page object)
        tables = page.extract_tables()
        for i, table in enumerate(tables):
            table_obj = self._extract_table_object(table, page, page_num, i)
            if table_obj:
                objects.append(table_obj)

        return objects

    def _extract_text_word_object(self, word: Dict[str, Any], page_num: int) -> Optional[TextWordDict]:
        """Extract text_word object with font details - based on old method"""
        try:
            x0, x1 = word.get('x0'), word.get('x1')

            # Handle different coordinate systems (keep as extracted)
            if 'y0' in word and 'y1' in word:
                y0, y1 = word['y0'], word['y1']
            elif 'top' in word and 'bottom' in word:
                y0, y1 = word['top'], word['bottom']  # Store as extracted
            else:
                return None

            content = word.get('text', '').strip()
            if not content or x0 is None or x1 is None or y0 is None or y1 is None:
                return None

            return {
                'type': 'text_word',
                'page': page_num,
                'bbox': [_round(x0), _round(y0), _round(x1), _round(y1)],
                'text': content,
                'fontname': word.get('fontname', ''),
                'fontsize': _round(word.get('size', 0))
            }
        except Exception as e:
            logger.warning(f"Error extracting text_word object: {e}")
            return None

    def _extract_text_line_object(self, line: Dict[str, Any], page_num: int) -> Optional[TextLineDict]:
        """Extract text_line object with bounds only - based on old method"""
        try:
            x0, x1 = line.get('x0'), line.get('x1')

            # Handle different coordinate systems (keep as extracted)
            if 'y0' in line and 'y1' in line:
                y0, y1 = line['y0'], line['y1']
            elif 'top' in line and 'bottom' in line:
                y0, y1 = line['top'], line['bottom']
            else:
                return None

            content = line.get('text', '').strip()
            if not content or x0 is None or x1 is None or y0 is None or y1 is None:
                return None

            return {
                'type': 'text_line',
                'page': page_num,
                'bbox': [_round(x0), _round(y0), _round(x1), _round(y1)]
            }
        except Exception as e:
            logger.warning(f"Error extracting text_line object: {e}")
            return None

    def _extract_graphic_rect_object(self, rect: Dict[str, Any], page_num: int) -> Optional[GraphicRectDict]:
        """Extract graphic_rect object - based on old method"""
        try:
            return {
                'type': 'graphic_rect',
                'page': page_num,
                'bbox': [_round(rect['x0']), _round(rect['y0']), _round(rect['x1']), _round(rect['y1'])],
                'linewidth': _round(rect.get('linewidth', 0))
            }
        except Exception as e:
            logger.warning(f"Error extracting graphic_rect object: {e}")
            return None

    def _extract_graphic_line_object(self, line: Dict[str, Any], page_num: int) -> Optional[GraphicLineDict]:
        """Extract graphic_line object with exact bounds - no padding"""
        try:
            # Use exact coordinates from old method - no padding
            x0, y0 = min(line['x0'], line['x1']), min(line['y0'], line['y1'])
            x1, y1 = max(line['x0'], line['x1']), max(line['y0'], line['y1'])

            return {
                'type': 'graphic_line',
                'page': page_num,
                'bbox': [_round(x0), _round(y0), _round(x1), _round(y1)],
                'linewidth': _round(line.get('linewidth', 0))
            }
        except Exception as e:
            logger.warning(f"Error extracting graphic_line object: {e}")
            return None

    def _extract_graphic_curve_object(self, curve: Dict[str, Any], page_num: int) -> Optional[GraphicCurveDict]:
        """Extract graphic_curve object - no Y-flipping, keep as extracted"""
        try:
            if 'pts' not in curve or not curve['pts']:
                return None

            # Store points as extracted - no Y manipulation
            points = [[_round(pt[0]), _round(pt[1])] for pt in curve['pts']]

            # Calculate bbox from points
            x_coords = [pt[0] for pt in points]
            y_coords = [pt[1] for pt in points]
            x0, x1 = min(x_coords), max(x_coords)
            y0, y1 = min(y_coords), max(y_coords)

            return {
                'type': 'graphic_curve',
                'page': page_num,
                'bbox': [_round(x0), _round(y0), _round(x1), _round(y1)],
                'points': points,
                'linewidth': _round(curve.get('linewidth', 0))
            }
        except Exception as e:
            logger.warning(f"Error extracting graphic_curve object: {e}")
            return None

    def _extract_image_object(self, image: Dict[str, Any], page_num: int) -> Optional[ImageDict]:
        """Extract image object with essential metadata"""
        try:
            x0, x1 = image.get('x0'), image.get('x1')
            y0, y1 = image.get('y0'), image.get('y1')

            if x0 is None or x1 is None or y0 is None or y1 is None:
                return None

            return {
                'type': 'image',
                'page': page_num,
                'bbox': [_round(x0), _round(y0), _round(x1), _round(y1)],
                'format': str(image.get('format', '')),
                'colorspace': str(image.get('colorspace', '')),
                'bits': image.get('bits', 0)
            }
        except Exception as e:
            logger.warning(f"Error extracting image object: {e}")
            return None

    def _extract_table_object(self, table: List[List[Optional[str]]], page: Page, page_num: int, table_index: int) -> Optional[TableDict]:
        """Extract table object with structure info - using page object as in old method"""
        try:
            if not table:
                return None

            # Get table bbox using old method (need page object for this)
            table_bbox = [_round(coord) for coord in page.bbox]  # Default

            # Try to get actual table bbox using old method
            try:
                table_finder = page.debug_tablefinder()
                if hasattr(table_finder, 'tables') and table_finder.tables:
                    if table_index < len(table_finder.tables):
                        table_obj = table_finder.tables[table_index]
                        if hasattr(table_obj, 'bbox'):
                            tb = table_obj.bbox
                            # Store as extracted - no coordinate manipulation
                            table_bbox = [_round(coord) for coord in tb]
            except Exception:
                # Fallback to page bbox if table bbox extraction fails
                pass

            return {
                'type': 'table',
                'page': page_num,
                'bbox': table_bbox,
                'rows': len(table),
                'cols': len(table[0]) if table else 0
            }
        except Exception as e:
            logger.warning(f"Error extracting table object: {e}")
            return None

    def _generate_signature_hash(self, objects: List[PdfObjectDict]) -> str:
        """Generate a deterministic signature hash from PDF objects - based on old method"""
        try:
            # Create signature from object structure (excluding variable text content)
            signature_data = []

            for obj in objects:
                # Include structural elements that don't change between similar documents
                signature_obj = {
                    'type': obj['type'],
                    'page': obj['page'],
                    'bbox': obj['bbox']
                }

                # Add type-specific structural attributes for template matching
                if obj['type'] == 'text_word':
                    # Include font info for structural matching
                    signature_obj['fontname'] = obj.get('fontname', '')
                    signature_obj['fontsize'] = obj.get('fontsize', 0)
                elif obj['type'] == 'graphic_rect':
                    signature_obj['linewidth'] = obj.get('linewidth')
                elif obj['type'] == 'graphic_line':
                    signature_obj['linewidth'] = obj.get('linewidth')
                elif obj['type'] == 'graphic_curve':
                    signature_obj['linewidth'] = obj.get('linewidth')
                    signature_obj['point_count'] = len(obj.get('points', []))
                elif obj['type'] == 'table':
                    signature_obj['rows'] = obj.get('rows')
                    signature_obj['cols'] = obj.get('cols')
                elif obj['type'] == 'image':
                    signature_obj['format'] = obj.get('format')

                signature_data.append(signature_obj)

            # Sort for consistent hash generation
            signature_data.sort(key=lambda x: (x['page'], x['bbox'][0], x['bbox'][1], x['type']))

            # Generate SHA-256 hash
            signature_json = json.dumps(signature_data, sort_keys=True)
            return hashlib.sha256(signature_json.encode()).hexdigest()

        except Exception as e:
            logger.error(f"Error generating signature hash: {e}")
            return hashlib.sha256(str(len(objects)).encode()).hexdigest()  # Fallback

# ===== GLOBAL EXTRACTOR INSTANCE =====

enhanced_pdf_extractor: Optional[EnhancedPdfObjectExtractor] = None

def init_enhanced_pdf_extractor() -> EnhancedPdfObjectExtractor:
    """Initialize enhanced PDF object extractor service"""
    global enhanced_pdf_extractor
    enhanced_pdf_extractor = EnhancedPdfObjectExtractor()
    logger.info("Enhanced PDF object extractor initialized")
    return enhanced_pdf_extractor

def get_enhanced_pdf_extractor() -> EnhancedPdfObjectExtractor:
    """Get the global enhanced PDF extractor instance"""
    if enhanced_pdf_extractor is None:
        return init_enhanced_pdf_extractor()
    return enhanced_pdf_extractor

# ===== CONVENIENCE FUNCTION =====

def extract_pdf_objects(file_content: bytes) -> PdfExtractionResult:
    """
    Convenience function to extract PDF objects from bytes

    Args:
        file_content: PDF file content as bytes

    Returns:
        PdfExtractionResult with all extracted objects
    """
    extractor = get_enhanced_pdf_extractor()
    return extractor.extract_objects_from_bytes(file_content)


def extract_pdf_metadata(file_content: bytes) -> Dict[str, Any]:
    """
    Extract basic metadata from PDF
    
    Args:
        file_content: PDF file content as bytes
        
    Returns:
        Dictionary with page_count, file_size, and other metadata
    """
    try:
        with pdfplumber.open(BytesIO(file_content)) as pdf:
            metadata = {
                'page_count': len(pdf.pages),
                'file_size': len(file_content),
                'pdf_metadata': pdf.metadata if pdf.metadata else {}
            }
            
            # Add any useful metadata fields
            if pdf.metadata:
                metadata['author'] = pdf.metadata.get('Author', None)
                metadata['title'] = pdf.metadata.get('Title', None)
                metadata['subject'] = pdf.metadata.get('Subject', None)
                metadata['creator'] = pdf.metadata.get('Creator', None)
                
            return metadata
            
    except Exception as e:
        logger.error(f"Error extracting PDF metadata: {e}")
        # Return minimal metadata on error
        return {
            'page_count': 1,  # Assume at least 1 page
            'file_size': len(file_content),
            'pdf_metadata': {},
            'extraction_error': str(e)
        }


def calculate_file_hash(file_content: bytes) -> str:
    """
    Calculate SHA256 hash for deduplication
    
    Args:
        file_content: PDF file content as bytes
        
    Returns:
        SHA256 hash as hex string
    """
    return hashlib.sha256(file_content).hexdigest()


def validate_pdf(file_content: bytes) -> tuple[bool, Optional[str]]:
    """
    Validate that the file is a valid PDF
    
    Args:
        file_content: File content to validate
        
    Returns:
        Tuple of (is_valid, error_message)
    """
    # Check PDF header
    if not file_content.startswith(b'%PDF'):
        return False, "File does not have PDF header"
    
    # Try to open with pdfplumber
    try:
        with pdfplumber.open(BytesIO(file_content)) as pdf:
            # Check if we can access pages
            if len(pdf.pages) == 0:
                return False, "PDF has no pages"
        return True, None
        
    except Exception as e:
        return False, f"Invalid PDF: {str(e)}"