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
        
        # Rectangles and lines
        shapes = page.rects + page.lines + page.curves
        for shape in shapes:
            shape_obj = self._extract_shape_object(shape, page_num, page_height)
            if shape_obj:
                objects.append(shape_obj)
        
        # Images
        images = page.images
        for image in images:
            image_obj = self._extract_image_object(image, page_num, page_height)
            if image_obj:
                objects.append(image_obj)
        
        return objects
    
    def _extract_word_object(self, word: Dict, page_num: int, page_height: float) -> Optional[PdfObject]:
        """Extract word object with enhanced font details"""
        try:
            return PdfObject(
                type="word",
                page=page_num + 1,
                text=word.get('text', ''),
                x=_round(word.get('x0', 0), self.rounding_precision),
                y=_round(page_height - word.get('y1', 0), self.rounding_precision),  # Convert to top-down
                width=_round(word.get('x1', 0) - word.get('x0', 0), self.rounding_precision),
                height=_round(word.get('y1', 0) - word.get('y0', 0), self.rounding_precision),
                font_name=word.get('fontname', ''),
                font_size=_round(word.get('size', 0), self.rounding_precision),
                char_count=len(word.get('text', '')),
                bbox=[
                    _round(word.get('x0', 0), self.rounding_precision),
                    _round(word.get('y0', 0), self.rounding_precision),
                    _round(word.get('x1', 0), self.rounding_precision),
                    _round(word.get('y1', 0), self.rounding_precision)
                ]
            )
        except Exception as e:
            logger.debug(f"Error extracting word object: {e}")
            return None
    
    def _extract_text_line_object(self, line: Dict, page_num: int, page_height: float) -> Optional[PdfObject]:
        """Extract text line object with line characteristics"""
        try:
            return PdfObject(
                type="text_line",
                page=page_num + 1,
                text=line.get('text', ''),
                x=_round(line.get('x0', 0), self.rounding_precision),
                y=_round(page_height - line.get('y1', 0), self.rounding_precision),  # Convert to top-down
                width=_round(line.get('x1', 0) - line.get('x0', 0), self.rounding_precision),
                height=_round(line.get('y1', 0) - line.get('y0', 0), self.rounding_precision),
                char_count=len(line.get('text', '')),
                bbox=[
                    _round(line.get('x0', 0), self.rounding_precision),
                    _round(line.get('y0', 0), self.rounding_precision),
                    _round(line.get('x1', 0), self.rounding_precision),
                    _round(line.get('y1', 0), self.rounding_precision)
                ]
            )
        except Exception as e:
            logger.debug(f"Error extracting text line object: {e}")
            return None
    
    def _extract_shape_object(self, shape: Dict, page_num: int, page_height: float) -> Optional[PdfObject]:
        """Extract shape object (rectangle, line, curve)"""
        try:
            object_type = shape.get('object_type', 'shape')
            if object_type in ['rect', 'line', 'curve']:
                return PdfObject(
                    type=object_type,
                    page=page_num + 1,
                    text="",  # Shapes don't have text content
                    x=_round(shape.get('x0', 0), self.rounding_precision),
                    y=_round(page_height - shape.get('y1', 0), self.rounding_precision),  # Convert to top-down
                    width=_round(shape.get('x1', 0) - shape.get('x0', 0), self.rounding_precision),
                    height=_round(shape.get('y1', 0) - shape.get('y0', 0), self.rounding_precision),
                    bbox=[
                        _round(shape.get('x0', 0), self.rounding_precision),
                        _round(shape.get('y0', 0), self.rounding_precision),
                        _round(shape.get('x1', 0), self.rounding_precision),
                        _round(shape.get('y1', 0), self.rounding_precision)
                    ]
                )
        except Exception as e:
            logger.debug(f"Error extracting shape object: {e}")
            return None
    
    def _extract_image_object(self, image: Dict, page_num: int, page_height: float) -> Optional[PdfObject]:
        """Extract image object"""
        try:
            return PdfObject(
                type="image",
                page=page_num + 1,
                text="",  # Images don't have text content
                x=_round(image.get('x0', 0), self.rounding_precision),
                y=_round(page_height - image.get('y1', 0), self.rounding_precision),  # Convert to top-down
                width=_round(image.get('x1', 0) - image.get('x0', 0), self.rounding_precision),
                height=_round(image.get('y1', 0) - image.get('y0', 0), self.rounding_precision),
                bbox=[
                    _round(image.get('x0', 0), self.rounding_precision),
                    _round(image.get('y0', 0), self.rounding_precision),
                    _round(image.get('x1', 0), self.rounding_precision),
                    _round(image.get('y1', 0), self.rounding_precision)
                ]
            )
        except Exception as e:
            logger.debug(f"Error extracting image object: {e}")
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