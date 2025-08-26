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

logger = logging.getLogger(__name__)

def _round(val, ndigits=3):
    """Round float values for consistent object comparison"""
    return round(val, ndigits) if isinstance(val, float) else val

class PdfObjectExtractor:
    """Service for extracting PDF objects for template matching"""
    
    def __init__(self):
        self.rounding_precision = 3
    
    def extract_objects_from_file_path(self, file_path: str) -> Dict[str, Any]:
        """Extract objects from PDF file path"""
        try:
            with open(file_path, 'rb') as f:
                pdf_bytes = f.read()
            return self.extract_objects_from_bytes(pdf_bytes)
        except Exception as e:
            logger.error(f"Error reading PDF file {file_path}: {e}")
            return {"success": False, "error": str(e), "objects": []}
    
    def extract_objects_from_bytes(self, pdf_bytes: bytes) -> Dict[str, Any]:
        """
        Extract all PDF objects from bytes and return with signature
        
        Returns:
        {
            "success": bool,
            "objects": List[Dict],
            "signature_hash": str,
            "page_count": int,
            "object_count": int,
            "error": str (if failed)
        }
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
            
            return {
                "success": True,
                "objects": objects,
                "signature_hash": signature_hash,
                "page_count": page_count,
                "object_count": len(objects)
            }
            
        except Exception as e:
            logger.error(f"Error extracting PDF objects: {e}")
            return {
                "success": False,
                "error": str(e),
                "objects": [],
                "signature_hash": None,
                "page_count": 0,
                "object_count": 0
            }
    
    def _extract_page_objects(self, page, page_num: int) -> List[Dict[str, Any]]:
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
        
        # Rectangles - Enhanced with styling details
        for rect in page.rects:
            rect_obj = self._extract_rect_object(rect, page_num)
            if rect_obj:
                objects.append(rect_obj)
        
        # Graphic lines - Enhanced with line properties
        for line in page.lines:
            line_obj = self._extract_graphic_line_object(line, page_num)
            if line_obj:
                objects.append(line_obj)
        
        # Curves - Enhanced with curve characteristics
        for curve in page.curves:
            curve_obj = self._extract_curve_object(curve, page_num, page_height)
            if curve_obj:
                objects.append(curve_obj)
        
        # Images - Enhanced with image metadata
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
    
    def _extract_word_object(self, word: Dict, page_num: int, page_height: float) -> Optional[Dict[str, Any]]:
        """Extract word object with enhanced font and position details"""
        try:
            x0, x1 = word.get('x0'), word.get('x1')
            
            # Handle different coordinate systems
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
            
            # Enhanced word object with more details
            return {
                'type': 'word',
                'page': page_num,
                'bbox': [_round(x0), _round(y0), _round(x1), _round(y1)],
                'text': content,
                'fontname': word.get('fontname', ''),
                'fontsize': _round(word.get('size', 0)),
                'width': _round(x1 - x0),
                'height': _round(y1 - y0),
                # Enhanced attributes for better matching
                'font_family': self._extract_font_family(word.get('fontname', '')),
                'is_bold': self._is_bold_font(word.get('fontname', '')),
                'is_italic': self._is_italic_font(word.get('fontname', '')),
                'char_count': len(content),
                'is_numeric': content.replace('.', '').replace(',', '').replace('-', '').isdigit(),
                'text_hash': hashlib.md5(content.encode()).hexdigest()[:8]  # For template matching
            }
        except Exception as e:
            logger.warning(f"Error extracting word object: {e}")
            return None
    
    def _extract_text_line_object(self, line: Dict, page_num: int, page_height: float) -> Optional[Dict[str, Any]]:
        """Extract text line object with enhanced characteristics"""
        try:
            x0, x1 = line.get('x0'), line.get('x1')
            
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
            
            return {
                'type': 'text_line',
                'page': page_num,
                'bbox': [_round(x0), _round(y0), _round(x1), _round(y1)],
                'text': content,
                'width': _round(x1 - x0),
                'height': _round(y1 - y0),
                # Enhanced attributes
                'word_count': len(content.split()),
                'char_count': len(content),
                'is_all_caps': content.isupper(),
                'contains_numbers': any(c.isdigit() for c in content),
                'text_hash': hashlib.md5(content.encode()).hexdigest()[:8]
            }
        except Exception as e:
            logger.warning(f"Error extracting text line object: {e}")
            return None
    
    def _extract_rect_object(self, rect: Dict, page_num: int) -> Optional[Dict[str, Any]]:
        """Extract rectangle object with enhanced styling"""
        try:
            return {
                'type': 'rect',
                'page': page_num,
                'bbox': [_round(rect['x0']), _round(rect['y0']), _round(rect['x1']), _round(rect['y1'])],
                'width': _round(rect['x1'] - rect['x0']),
                'height': _round(rect['y1'] - rect['y0']),
                'linewidth': _round(rect.get('linewidth', 0)),
                'stroke_color': str(rect.get('stroke', '')),
                'fill_color': str(rect.get('fill', '')),
                # Enhanced attributes
                'area': _round((rect['x1'] - rect['x0']) * (rect['y1'] - rect['y0'])),
                'aspect_ratio': _round((rect['x1'] - rect['x0']) / (rect['y1'] - rect['y0']) if rect['y1'] - rect['y0'] > 0 else 0),
                'has_stroke': bool(rect.get('stroke')),
                'has_fill': bool(rect.get('fill'))
            }
        except Exception as e:
            logger.warning(f"Error extracting rect object: {e}")
            return None
    
    def _extract_graphic_line_object(self, line: Dict, page_num: int) -> Optional[Dict[str, Any]]:
        """Extract graphic line object with enhanced properties"""
        try:
            x0, y0 = min(line['x0'], line['x1']), min(line['y0'], line['y1'])
            x1, y1 = max(line['x0'], line['x1']), max(line['y0'], line['y1'])
            
            # Add padding for better selection
            padding = 2
            bbox = [x0 - padding, y0 - padding, x1 + padding, y1 + padding]
            
            return {
                'type': 'graphic_line',
                'page': page_num,
                'bbox': [_round(coord) for coord in bbox],
                'start': [_round(line['x0']), _round(line['y0'])],
                'end': [_round(line['x1']), _round(line['y1'])],
                'width': _round(x1 - x0),
                'height': _round(y1 - y0),
                'linewidth': _round(line.get('linewidth', 0)),
                'stroke_color': str(line.get('stroke', '')),
                # Enhanced attributes
                'length': _round(((line['x1'] - line['x0'])**2 + (line['y1'] - line['y0'])**2)**0.5),
                'is_horizontal': abs(line['y1'] - line['y0']) < 1,
                'is_vertical': abs(line['x1'] - line['x0']) < 1,
                'angle': _round(self._calculate_angle(line['x0'], line['y0'], line['x1'], line['y1']))
            }
        except Exception as e:
            logger.warning(f"Error extracting graphic line object: {e}")
            return None
    
    def _extract_curve_object(self, curve: Dict, page_num: int, page_height: float) -> Optional[Dict[str, Any]]:
        """Extract curve object with enhanced geometry"""
        try:
            if 'pts' not in curve or not curve['pts']:
                return None
            
            # Flip y-coordinates
            flipped_pts = [(_round(pt[0]), _round(page_height - pt[1])) for pt in curve['pts']]
            x_coords = [pt[0] for pt in flipped_pts]
            y_coords = [pt[1] for pt in flipped_pts]
            x0, x1 = min(x_coords), max(x_coords)
            y0, y1 = min(y_coords), max(y_coords)
            
            return {
                'type': 'curve',
                'page': page_num,
                'bbox': [_round(x0), _round(y0), _round(x1), _round(y1)],
                'points': flipped_pts,
                'width': _round(x1 - x0),
                'height': _round(y1 - y0),
                'linewidth': _round(curve.get('linewidth', 0)),
                'stroke_color': str(curve.get('stroke', '')),
                # Enhanced attributes
                'point_count': len(flipped_pts),
                'path_length': self._calculate_curve_length(flipped_pts),
                'is_closed': flipped_pts[0] == flipped_pts[-1] if len(flipped_pts) > 1 else False
            }
        except Exception as e:
            logger.warning(f"Error extracting curve object: {e}")
            return None
    
    def _extract_image_object(self, image: Dict, page_num: int) -> Optional[Dict[str, Any]]:
        """Extract image object with enhanced metadata"""
        try:
            x0, x1 = image.get('x0'), image.get('x1')
            y0, y1 = image.get('y0'), image.get('y1')
            
            if x0 is None or x1 is None or y0 is None or y1 is None:
                return None
            
            return {
                'type': 'image',
                'page': page_num,
                'bbox': [_round(x0), _round(y0), _round(x1), _round(y1)],
                'width': _round(x1 - x0),
                'height': _round(y1 - y0),
                'name': str(image.get('name', '')),
                'format': str(image.get('format', '')),
                'colorspace': str(image.get('colorspace', '')),
                'bits': image.get('bits', 0),
                'width_pixels': image.get('width', 0),
                'height_pixels': image.get('height', 0),
                # Enhanced attributes
                'area': _round((x1 - x0) * (y1 - y0)),
                'aspect_ratio': _round((x1 - x0) / (y1 - y0) if y1 - y0 > 0 else 0),
                'pixel_density': _round((image.get('width', 0) * image.get('height', 0)) / ((x1 - x0) * (y1 - y0)) if (x1 - x0) * (y1 - y0) > 0 else 0)
            }
        except Exception as e:
            logger.warning(f"Error extracting image object: {e}")
            return None
    
    def _extract_table_object(self, table: List, page, page_num: int, page_height: float, table_index: int) -> Optional[Dict[str, Any]]:
        """Extract table object with enhanced structure analysis"""
        try:
            if not table:
                return None
            
            # Default bbox
            table_bbox = [_round(coord) for coord in page.bbox]
            
            # Try to get actual table bbox
            try:
                table_finder = page.debug_tablefinder()
                if hasattr(table_finder, 'tables') and table_finder.tables:
                    if table_index < len(table_finder.tables):
                        table_obj = table_finder.tables[table_index]
                        if hasattr(table_obj, 'bbox'):
                            tb = table_obj.bbox
                            if tb[1] < tb[3]:
                                y0_flipped = _round(page_height - tb[3])
                                y1_flipped = _round(page_height - tb[1])
                                table_bbox = [_round(tb[0]), y0_flipped, _round(tb[2]), y1_flipped]
                            else:
                                table_bbox = [_round(coord) for coord in tb]
            except Exception:
                pass
            
            # Analyze table structure
            rows = len(table)
            cols = len(table[0]) if table else 0
            non_empty_cells = sum(1 for row in table for cell in row if cell and str(cell).strip())
            
            return {
                'type': 'table',
                'page': page_num,
                'bbox': table_bbox,
                'width': _round(table_bbox[2] - table_bbox[0]),
                'height': _round(table_bbox[3] - table_bbox[1]),
                'rows': rows,
                'cols': cols,
                'preview': table[:3] if table else [],  # First 3 rows for debugging
                # Enhanced attributes
                'total_cells': rows * cols,
                'non_empty_cells': non_empty_cells,
                'fill_ratio': _round(non_empty_cells / (rows * cols) if rows * cols > 0 else 0),
                'has_header': self._table_has_header(table),
                'column_types': self._analyze_table_columns(table),
                'table_hash': hashlib.md5(json.dumps(table, sort_keys=True).encode()).hexdigest()[:8]
            }
        except Exception as e:
            logger.warning(f"Error extracting table object: {e}")
            return None
    
    def _generate_signature_hash(self, objects: List[Dict[str, Any]]) -> str:
        """Generate a deterministic signature hash from PDF objects"""
        try:
            # Create signature from object structure (excluding variable text content)
            signature_data = []
            
            for obj in objects:
                # Include structural elements that don't change between similar documents
                signature_obj = {
                    'type': obj['type'],
                    'page': obj['page'],
                    'bbox': obj['bbox'],
                    'width': obj.get('width'),
                    'height': obj.get('height')
                }
                
                # Add type-specific structural attributes
                if obj['type'] in ['word', 'text_line']:
                    # For text objects, include font info but not actual text (for template matching)
                    signature_obj['fontname'] = obj.get('fontname', '')
                    signature_obj['fontsize'] = obj.get('fontsize', 0)
                    signature_obj['char_count'] = obj.get('char_count', 0)
                elif obj['type'] == 'rect':
                    signature_obj['linewidth'] = obj.get('linewidth')
                    signature_obj['has_stroke'] = obj.get('has_stroke')
                    signature_obj['has_fill'] = obj.get('has_fill')
                elif obj['type'] == 'graphic_line':
                    signature_obj['linewidth'] = obj.get('linewidth')
                    signature_obj['is_horizontal'] = obj.get('is_horizontal')
                    signature_obj['is_vertical'] = obj.get('is_vertical')
                elif obj['type'] == 'table':
                    signature_obj['rows'] = obj.get('rows')
                    signature_obj['cols'] = obj.get('cols')
                elif obj['type'] == 'image':
                    signature_obj['format'] = obj.get('format')
                    signature_obj['aspect_ratio'] = obj.get('aspect_ratio')
                
                signature_data.append(signature_obj)
            
            # Sort for consistent hash generation
            signature_data.sort(key=lambda x: (x['page'], x['bbox'][0], x['bbox'][1], x['type']))
            
            # Generate SHA-256 hash
            signature_json = json.dumps(signature_data, sort_keys=True)
            return hashlib.sha256(signature_json.encode()).hexdigest()
            
        except Exception as e:
            logger.error(f"Error generating signature hash: {e}")
            return hashlib.sha256(str(len(objects)).encode()).hexdigest()  # Fallback
    
    # Helper methods for enhanced object analysis
    def _extract_font_family(self, fontname: str) -> str:
        """Extract font family from font name"""
        if not fontname:
            return ''
        # Remove common suffixes
        family = fontname.split('+')[-1] if '+' in fontname else fontname
        family = family.split('-')[0] if '-' in family else family
        return family
    
    def _is_bold_font(self, fontname: str) -> bool:
        """Check if font is bold"""
        if not fontname:
            return False
        return any(keyword in fontname.lower() for keyword in ['bold', 'black', 'heavy'])
    
    def _is_italic_font(self, fontname: str) -> bool:
        """Check if font is italic"""
        if not fontname:
            return False
        return any(keyword in fontname.lower() for keyword in ['italic', 'oblique'])
    
    def _calculate_angle(self, x0: float, y0: float, x1: float, y1: float) -> float:
        """Calculate angle of a line in degrees"""
        import math
        if x1 - x0 == 0:
            return 90.0 if y1 > y0 else -90.0
        return math.degrees(math.atan((y1 - y0) / (x1 - x0)))
    
    def _calculate_curve_length(self, points: List[tuple]) -> float:
        """Calculate approximate length of a curve"""
        if len(points) < 2:
            return 0.0
        
        total_length = 0.0
        for i in range(1, len(points)):
            dx = points[i][0] - points[i-1][0]
            dy = points[i][1] - points[i-1][1]
            total_length += (dx**2 + dy**2)**0.5
        
        return _round(total_length)
    
    def _table_has_header(self, table: List) -> bool:
        """Analyze if table has header row"""
        if len(table) < 2:
            return False
        
        # Simple heuristic: if first row is different from second row pattern
        first_row = table[0]
        second_row = table[1]
        
        # Check if first row has more non-empty cells or different pattern
        first_non_empty = sum(1 for cell in first_row if cell and str(cell).strip())
        second_non_empty = sum(1 for cell in second_row if cell and str(cell).strip())
        
        return first_non_empty >= second_non_empty
    
    def _analyze_table_columns(self, table: List) -> List[str]:
        """Analyze column types in table"""
        if not table or not table[0]:
            return []
        
        col_types = []
        for col_idx in range(len(table[0])):
            col_values = [row[col_idx] for row in table if col_idx < len(row) and row[col_idx]]
            
            if not col_values:
                col_types.append('empty')
                continue
            
            # Analyze column content
            numeric_count = sum(1 for val in col_values if str(val).replace('.', '').replace(',', '').replace('-', '').isdigit())
            
            if numeric_count > len(col_values) * 0.8:
                col_types.append('numeric')
            elif any(keyword in str(val).lower() for val in col_values for keyword in ['date', '/', '-']):
                col_types.append('date')
            else:
                col_types.append('text')
        
        return col_types

# Global PDF object extractor instance
pdf_extractor = None

def init_pdf_extractor():
    """Initialize PDF object extractor service"""
    global pdf_extractor
    pdf_extractor = PdfObjectExtractor()
    logger.info("PDF object extractor initialized")
    return pdf_extractor

def get_pdf_extractor():
    """Get the global PDF extractor instance"""
    if pdf_extractor is None:
        return init_pdf_extractor()
    return pdf_extractor