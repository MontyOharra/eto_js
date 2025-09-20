"""
PDF Object Extraction Service
Extracts objects from PDFs for template creation and matching
Based on pdfplumber extraction with enhanced object details
"""

import pdfplumber
import io
import hashlib
import json
import logging
from pathlib import Path
from typing import List, Dict, Any, Optional
from shared.domain import PdfObject, PdfObjectExtractionResult

logger = logging.getLogger(__name__)

def _round(val, ndigits=3):
    """Round float values for consistent object comparison"""
    return round(val, ndigits) if isinstance(val, float) else val

class PdfObjectExtractionService:
    """Service for extracting PDF objects for template matching"""
    
    def __init__(self):
        self.rounding_precision = 3
    
    def extract_objects_from_file_path(self, file_path: str) -> PdfObjectExtractionResult:
        """Extract objects from PDF file path"""
        try:
            with open(file_path, 'rb') as f:
                pdf_bytes = f.read()
            return self.extract_objects_from_bytes(pdf_bytes)
        except Exception as e:
            logger.error(f"Error reading PDF file {file_path}: {e}")
            return PdfObjectExtractionResult(
                success=False,
                objects=[],
                signature_hash=None,
                page_count=0,
                object_count=0,
                error_message=str(e)
            )
    
    def extract_objects_from_bytes(self, pdf_bytes: bytes) -> PdfObjectExtractionResult:
        """
        Extract all PDF objects from bytes and return with signature

        Returns:
            PdfObjectExtractionResult with success status, objects, and metadata
        """
        try:
            objects = []

            with pdfplumber.open(io.BytesIO(pdf_bytes)) as pdf:
                page_count = len(pdf.pages)

                for page_num, page in enumerate(pdf.pages):
                    page_objects = self._extract_page_objects(page, page_num)
                    objects.extend(page_objects)

            # Generate signature hash from objects
            signature_hash = self._generate_signature_hash(objects)

            logger.info(f"Extracted {len(objects)} objects from {page_count} pages. Signature: {signature_hash[:8]}...")

            return PdfObjectExtractionResult(
                success=True,
                objects=objects,
                signature_hash=signature_hash,
                page_count=page_count,
                object_count=len(objects)
            )

        except Exception as e:
            logger.error(f"Error extracting PDF objects: {e}")
            return PdfObjectExtractionResult(
                success=False,
                objects=[],
                signature_hash=None,
                page_count=0,
                object_count=0,
                error_message=str(e)
            )
    
    def _extract_page_objects(self, page, page_num: int) -> List[PdfObject]:
        """Extract all objects from a single page"""
        objects = []
        page_height = page.height
        
        # Words - Enhanced with more font details
        words = page.extract_words(x_tolerance=3, y_tolerance=3)
        for word in words:
            word_obj = self._extract_word_object(word, page_num, page_height)
            if word_obj:
                objects.append(word_obj)
        
        # Text lines - Enhanced with line characteristics  
        lines = page.extract_text_lines(layout=True)
        for line in lines:
            line_obj = self._extract_text_line_object(line, page_num, page_height)
            if line_obj:
                objects.append(line_obj)
        
        # Rectangles
        for rect in page.rects:
            rect_obj = self._extract_rect_object(rect, page_num)
            if rect_obj:
                objects.append(rect_obj)

        # Lines
        for line in page.lines:
            line_obj = self._extract_line_object(line, page_num)
            if line_obj:
                objects.append(line_obj)

        # Curves
        for curve in page.curves:
            curve_obj = self._extract_curve_object(curve, page_num, page_height)
            if curve_obj:
                objects.append(curve_obj)

        # Images
        for image in page.images:
            image_obj = self._extract_image_object(image, page_num)
            if image_obj:
                objects.append(image_obj)

        # Tables - Enhanced with table structure
        tables = page.extract_tables()
        for i, table in enumerate(tables):
            table_obj = self._extract_table_object(table, page, page_num, page_height, i)
            if table_obj:
                objects.append(table_obj)

        return objects
    
    def _extract_word_object(self, word: Dict, page_num: int, page_height: float) -> Optional[PdfObject]:
        """Extract word object with enhanced font details"""
        try:
            x0, x1 = word.get('x0'), word.get('x1')

            # Handle different coordinate systems like the working version
            if 'y0' in word and 'y1' in word:
                y0, y1 = word['y0'], word['y1']
            elif 'top' in word and 'bottom' in word:
                y0 = page_height - word['bottom']
                y1 = page_height - word['top']
            else:
                return None

            content = word.get('text', '').strip()
            if not content or x0 is None or x1 is None or y0 is None or y1 is None:
                return None

            return PdfObject(
                type="word",
                page=page_num,  # Use 0-based page numbering like working version
                text=content,
                x=_round(x0, self.rounding_precision),
                y=_round(y0, self.rounding_precision),
                width=_round(x1 - x0, self.rounding_precision),
                height=_round(y1 - y0, self.rounding_precision),
                font_name=word.get('fontname', ''),
                font_size=_round(word.get('size', 0), self.rounding_precision),
                char_count=len(content),
                bbox=[_round(x0, self.rounding_precision), _round(y0, self.rounding_precision),
                      _round(x1, self.rounding_precision), _round(y1, self.rounding_precision)]
            )
        except Exception as e:
            logger.debug(f"Error extracting word object: {e}")
            return None
    
    def _extract_text_line_object(self, line: Dict, page_num: int, page_height: float) -> Optional[PdfObject]:
        """Extract text line object with line characteristics"""
        try:
            x0, x1 = line.get('x0'), line.get('x1')

            # Handle different coordinate systems like the working version
            if 'y0' in line and 'y1' in line:
                y0, y1 = line['y0'], line['y1']
            elif 'top' in line and 'bottom' in line:
                y0 = page_height - line['bottom']
                y1 = page_height - line['top']
            else:
                return None

            content = line.get('text', '').strip()
            if not content or x0 is None or x1 is None or y0 is None or y1 is None:
                return None

            return PdfObject(
                type="text_line",
                page=page_num,  # Use 0-based page numbering like working version
                text=content,
                x=_round(x0, self.rounding_precision),
                y=_round(y0, self.rounding_precision),
                width=_round(x1 - x0, self.rounding_precision),
                height=_round(y1 - y0, self.rounding_precision),
                char_count=len(content),
                bbox=[_round(x0, self.rounding_precision), _round(y0, self.rounding_precision),
                      _round(x1, self.rounding_precision), _round(y1, self.rounding_precision)]
            )
        except Exception as e:
            logger.debug(f"Error extracting text line object: {e}")
            return None
    
    def _extract_rect_object(self, rect: Dict, page_num: int) -> Optional[PdfObject]:
        """Extract rectangle object"""
        try:
            return PdfObject(
                type='rect',
                page=page_num,
                text="",
                x=_round(rect['x0'], self.rounding_precision),
                y=_round(rect['y0'], self.rounding_precision),
                width=_round(rect['x1'] - rect['x0'], self.rounding_precision),
                height=_round(rect['y1'] - rect['y0'], self.rounding_precision),
                bbox=[_round(rect['x0'], self.rounding_precision), _round(rect['y0'], self.rounding_precision),
                      _round(rect['x1'], self.rounding_precision), _round(rect['y1'], self.rounding_precision)]
            )
        except Exception as e:
            logger.debug(f"Error extracting rect object: {e}")
            return None

    def _extract_line_object(self, line: Dict, page_num: int) -> Optional[PdfObject]:
        """Extract graphic line object with enhanced properties like working version"""
        try:
            x0, y0 = min(line['x0'], line['x1']), min(line['y0'], line['y1'])
            x1, y1 = max(line['x0'], line['x1']), max(line['y0'], line['y1'])

            # Add padding for better selection like working version
            padding = 2
            bbox = [x0 - padding, y0 - padding, x1 + padding, y1 + padding]

            return PdfObject(
                type='line',  # Keep as 'line' to match domain object
                page=page_num,
                text="",
                x=_round(x0, self.rounding_precision),
                y=_round(y0, self.rounding_precision),
                width=_round(x1 - x0, self.rounding_precision),
                height=_round(y1 - y0, self.rounding_precision),
                bbox=[_round(coord, self.rounding_precision) for coord in bbox]
            )
        except Exception as e:
            logger.debug(f"Error extracting line object: {e}")
            return None

    def _extract_curve_object(self, curve: Dict, page_num: int, page_height: float) -> Optional[PdfObject]:
        """Extract curve object with enhanced geometry like working version"""
        try:
            if 'pts' not in curve or not curve['pts']:
                return None

            # Flip y-coordinates like in working version
            flipped_pts = [(_round(pt[0], self.rounding_precision), _round(page_height - pt[1], self.rounding_precision)) for pt in curve['pts']]
            x_coords = [pt[0] for pt in flipped_pts]
            y_coords = [pt[1] for pt in flipped_pts]
            x0, x1 = min(x_coords), max(x_coords)
            y0, y1 = min(y_coords), max(y_coords)

            return PdfObject(
                type='curve',
                page=page_num,
                text="",
                x=_round(x0, self.rounding_precision),
                y=_round(y0, self.rounding_precision),
                width=_round(x1 - x0, self.rounding_precision),
                height=_round(y1 - y0, self.rounding_precision),
                bbox=[_round(x0, self.rounding_precision), _round(y0, self.rounding_precision),
                      _round(x1, self.rounding_precision), _round(y1, self.rounding_precision)]
            )
        except Exception as e:
            logger.debug(f"Error extracting curve object: {e}")
            return None
    
    def _extract_image_object(self, image: Dict, page_num: int) -> Optional[PdfObject]:
        """Extract image object"""
        try:
            x0, x1 = image.get('x0'), image.get('x1')
            y0, y1 = image.get('y0'), image.get('y1')

            if x0 is None or x1 is None or y0 is None or y1 is None:
                return None

            return PdfObject(
                type="image",
                page=page_num,
                text="",
                x=_round(x0, self.rounding_precision),
                y=_round(y0, self.rounding_precision),
                width=_round(x1 - x0, self.rounding_precision),
                height=_round(y1 - y0, self.rounding_precision),
                bbox=[_round(x0, self.rounding_precision), _round(y0, self.rounding_precision),
                      _round(x1, self.rounding_precision), _round(y1, self.rounding_precision)]
            )
        except Exception as e:
            logger.debug(f"Error extracting image object: {e}")
            return None

    def _extract_table_object(self, table: list, page, page_num: int, page_height: float, table_index: int) -> Optional[PdfObject]:
        """Extract table object with enhanced structure analysis like working version"""
        try:
            if not table:
                return None

            # Default bbox
            table_bbox = [_round(coord, self.rounding_precision) for coord in page.bbox]

            # Try to get actual table bbox like in working version
            try:
                table_finder = page.debug_tablefinder()
                if hasattr(table_finder, 'tables') and table_finder.tables:
                    if table_index < len(table_finder.tables):
                        table_obj = table_finder.tables[table_index]
                        if hasattr(table_obj, 'bbox'):
                            tb = table_obj.bbox
                            if tb[1] < tb[3]:
                                y0_flipped = _round(page_height - tb[3], self.rounding_precision)
                                y1_flipped = _round(page_height - tb[1], self.rounding_precision)
                                table_bbox = [_round(tb[0], self.rounding_precision), y0_flipped,
                                            _round(tb[2], self.rounding_precision), y1_flipped]
                            else:
                                table_bbox = [_round(coord, self.rounding_precision) for coord in tb]
            except Exception:
                pass

            # Analyze table structure
            rows = len(table)
            cols = len(table[0]) if table else 0

            return PdfObject(
                type='table',
                page=page_num,
                text="",  # Tables don't have simple text content
                x=_round(table_bbox[0], self.rounding_precision),
                y=_round(table_bbox[1], self.rounding_precision),
                width=_round(table_bbox[2] - table_bbox[0], self.rounding_precision),
                height=_round(table_bbox[3] - table_bbox[1], self.rounding_precision),
                bbox=table_bbox
            )
        except Exception as e:
            logger.debug(f"Error extracting table object: {e}")
            return None
    
    def _generate_signature_hash(self, objects: List[PdfObject]) -> str:
        """Generate signature hash from objects for template matching"""
        try:
            # Create a simplified representation for hashing
            signature_data = []

            for obj in objects:
                if obj.type in ['word', 'text_line']:
                    # For text objects, include position and some text characteristics
                    signature_data.append({
                        'type': obj.type,
                        'x': obj.x,
                        'y': obj.y,
                        'width': obj.width,
                        'height': obj.height,
                        'char_count': obj.char_count or 0,
                        'font_size': obj.font_size
                    })
                elif obj.type in ['rect', 'line', 'curve', 'image']:
                    # For shapes and images, include position and dimensions
                    signature_data.append({
                        'type': obj.type,
                        'x': obj.x,
                        'y': obj.y,
                        'width': obj.width,
                        'height': obj.height
                    })

            # Create hash from signature data
            signature_string = json.dumps(signature_data, sort_keys=True)
            return hashlib.sha256(signature_string.encode()).hexdigest()

        except Exception as e:
            logger.error(f"Error generating signature hash: {e}")
            return hashlib.sha256(b"error").hexdigest()