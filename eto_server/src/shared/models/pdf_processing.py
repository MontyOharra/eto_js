"""
PDF Processing Domain Models - Nested Object Type System
Structured approach with base class and specific object types grouped by category
"""

from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from datetime import datetime
import json

# ===== COORDINATE TYPES =====

BBox = List[float]  # [x0, y0, x1, y1]

# ===== BASE PDF OBJECT =====

class BasePdfObject(BaseModel):
    """Base PDF object with core fields all objects share"""
    page: int = Field(..., description="Page number (1-based)")
    bbox: BBox = Field(..., min_length=4, max_length=4, description="Bounding box [x0, y0, x1, y1]")

    class Config:
        from_attributes = True

# ===== SPECIFIC OBJECT TYPES =====

class TextWordPdfObject(BasePdfObject):
    """Text word object with font information"""
    text: str = Field(..., description="Text content")
    fontname: str = Field(..., description="Font name")
    fontsize: float = Field(..., description="Font size")

class TextLinePdfObject(BasePdfObject):
    """Text line object - only has base fields (page, bbox)"""
    pass

class GraphicRectPdfObject(BasePdfObject):
    """Graphic rectangle object"""
    linewidth: float = Field(..., description="Line width")

class GraphicLinePdfObject(BasePdfObject):
    """Graphic line object"""
    linewidth: float = Field(..., description="Line width")

class GraphicCurvePdfObject(BasePdfObject):
    """Graphic curve object with points"""
    points: List[List[float]] = Field(..., description="Points defining the curve")
    linewidth: float = Field(..., description="Line width")

class ImagePdfObject(BasePdfObject):
    """Image object with format information"""
    format: str = Field(..., description="Image format")
    colorspace: str = Field(..., description="Image colorspace")
    bits: int = Field(..., description="Image bit depth")

class TablePdfObject(BasePdfObject):
    """Table object with dimensions"""
    rows: int = Field(..., description="Number of table rows")
    cols: int = Field(..., description="Number of table columns")

# ===== NESTED CONTAINER TYPE =====

class PdfObjects(BaseModel):
    """Container organizing PDF objects by their specific types"""
    text_words: List[TextWordPdfObject] = Field(default_factory=list, description="Text word objects")
    text_lines: List[TextLinePdfObject] = Field(default_factory=list, description="Text line objects")
    graphic_rects: List[GraphicRectPdfObject] = Field(default_factory=list, description="Graphic rectangle objects")
    graphic_lines: List[GraphicLinePdfObject] = Field(default_factory=list, description="Graphic line objects")
    graphic_curves: List[GraphicCurvePdfObject] = Field(default_factory=list, description="Graphic curve objects")
    images: List[ImagePdfObject] = Field(default_factory=list, description="Image objects")
    tables: List[TablePdfObject] = Field(default_factory=list, description="Table objects")

    def get_total_count(self) -> int:
        """Get total count of all objects across all types"""
        return (
            len(self.text_words) +
            len(self.text_lines) +
            len(self.graphic_rects) +
            len(self.graphic_lines) +
            len(self.graphic_curves) +
            len(self.images) +
            len(self.tables)
        )

    def get_counts_by_type(self) -> Dict[str, int]:
        """Get count of objects for each type"""
        return {
            'text_words': len(self.text_words),
            'text_lines': len(self.text_lines),
            'graphic_rects': len(self.graphic_rects),
            'graphic_lines': len(self.graphic_lines),
            'graphic_curves': len(self.graphic_curves),
            'images': len(self.images),
            'tables': len(self.tables)
        }

    @classmethod
    def from_json(cls, json_objects: str) -> 'PdfObjects':
        """
        Convert from the old unified object list to new nested structure
        Used during migration from old storage format

        Args:
            objects: List of object dictionaries with 'type' field

        Returns:
            PdfObjects with objects grouped by type
        """
        result = cls()

        try:
            objects_list = json.loads(json_objects)
            if not isinstance(objects_list, list):
                return result

            for obj_dict in objects_list:
                obj_type = obj_dict.get('type', '')

                try:
                    if obj_type == 'text_word':
                        result.text_words.append(TextWordPdfObject(**obj_dict))
                    elif obj_type == 'text_line':
                        result.text_lines.append(TextLinePdfObject(**obj_dict))
                    elif obj_type == 'graphic_rect':
                        result.graphic_rects.append(GraphicRectPdfObject(**obj_dict))
                    elif obj_type == 'graphic_line':
                        result.graphic_lines.append(GraphicLinePdfObject(**obj_dict))
                    elif obj_type == 'graphic_curve':
                        result.graphic_curves.append(GraphicCurvePdfObject(**obj_dict))
                    elif obj_type == 'image':
                        result.images.append(ImagePdfObject(**obj_dict))
                    elif obj_type == 'table':
                        result.tables.append(TablePdfObject(**obj_dict))
                except Exception:
                    # Skip invalid objects
                    continue

        except (json.JSONDecodeError, TypeError):
            # Return empty container if JSON is invalid
            pass

        return result


    def to_json(self) -> str:
        """
        Convert PdfObjects to JSON string containing flat object list

        Returns:
            JSON string with list of object dictionaries
        """
        all_objects = []

        # Add all object types to the flat list
        for obj in self.text_words:
            obj_dict = obj.model_dump()
            obj_dict['type'] = 'text_word'
            all_objects.append(obj_dict)

        for obj in self.text_lines:
            obj_dict = obj.model_dump()
            obj_dict['type'] = 'text_line'
            all_objects.append(obj_dict)

        for obj in self.graphic_rects:
            obj_dict = obj.model_dump()
            obj_dict['type'] = 'graphic_rect'
            all_objects.append(obj_dict)

        for obj in self.graphic_lines:
            obj_dict = obj.model_dump()
            obj_dict['type'] = 'graphic_line'
            all_objects.append(obj_dict)

        for obj in self.graphic_curves:
            obj_dict = obj.model_dump()
            obj_dict['type'] = 'graphic_curve'
            all_objects.append(obj_dict)

        for obj in self.images:
            obj_dict = obj.model_dump()
            obj_dict['type'] = 'image'
            all_objects.append(obj_dict)

        for obj in self.tables:
            obj_dict = obj.model_dump()
            obj_dict['type'] = 'table'
            all_objects.append(obj_dict)

        return json.dumps(all_objects)
