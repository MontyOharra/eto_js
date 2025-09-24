"""
New PDF Processing Domain Models
Unified PdfObject model for all PDF object types
"""

from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any, Union
from datetime import datetime

# ===== COORDINATE TYPES =====

BBox = List[float]  # [x0, y0, x1, y1]

# ===== UNIFIED PDF OBJECT MODEL =====

class PdfObject(BaseModel):
    """Unified PDF object model supporting all object types"""
    # Core fields (always present)
    type: str = Field(..., description="Object type (text_word, text_line, graphic_rect, etc.)")
    page: int = Field(..., description="Page number (1-based)")
    bbox: BBox = Field(..., min_length=4, max_length=4, description="Bounding box [x0, y0, x1, y1]")

    # Text-specific fields (text_word)
    text: Optional[str] = Field(None, description="Text content for text objects")
    fontname: Optional[str] = Field(None, description="Font name for text objects")
    fontsize: Optional[float] = Field(None, description="Font size for text objects")

    # Graphic-specific fields (graphic_rect, graphic_line, graphic_curve)
    linewidth: Optional[float] = Field(None, description="Line width for graphic objects")
    points: Optional[List[List[float]]] = Field(None, description="Points for curve objects")

    # Image-specific fields
    format: Optional[str] = Field(None, description="Image format")
    colorspace: Optional[str] = Field(None, description="Image colorspace")
    bits: Optional[int] = Field(None, description="Image bit depth")

    # Table-specific fields
    rows: Optional[int] = Field(None, description="Number of table rows")
    cols: Optional[int] = Field(None, description="Number of table columns")

    class Config:
        from_attributes = True

    @classmethod
    def from_db_model(cls, obj_dict: Dict[str, Any]) -> 'PdfObject':
        """
        Create PdfObject from stored JSON object dict

        Args:
            obj_dict: Dictionary from database JSON field

        Returns:
            PdfObject instance
        """
        return cls(
            type=obj_dict.get('type', ''),
            page=obj_dict.get('page', 1),
            bbox=obj_dict.get('bbox', [0, 0, 0, 0]),
            text=obj_dict.get('text'),
            fontname=obj_dict.get('fontname'),
            fontsize=obj_dict.get('fontsize'),
            linewidth=obj_dict.get('linewidth'),
            points=obj_dict.get('points'),
            format=obj_dict.get('format'),
            colorspace=obj_dict.get('colorspace'),
            bits=obj_dict.get('bits'),
            rows=obj_dict.get('rows'),
            cols=obj_dict.get('cols')
        )

# ===== REPOSITORY RESPONSE MODELS =====

class PdfDetailData(BaseModel):
    """PDF file detail data for template builder"""
    # PDF file info
    pdf_id: int
    filename: str
    original_filename: str
    file_size: int

    # PDF objects grouped by type
    objects_by_type: Dict[str, List[PdfObject]] = Field(default_factory=dict)
    total_object_count: int = Field(default=0)

    # Email context (nullable)
    email_subject: Optional[str] = None
    sender_email: Optional[str] = None
    received_date: Optional[Any] = None  # datetime, but allowing Any for flexibility


class EtoRunWithPdfData(BaseModel):
    """ETO run with complete PDF and email data"""

    # ETO run data
    run_id: int
    status: str
    processing_step: Optional[str] = None
    matched_template_id: Optional[int] = None
    extracted_data: Optional[Dict[str, Any]] = None
    transformation_audit: Optional[Dict[str, Any]] = None
    target_data: Optional[Dict[str, Any]] = None
    error_type: Optional[str] = None
    error_message: Optional[str] = None
    created_at: datetime
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None

    # PDF file data
    pdf_id: int
    filename: str
    original_filename: str
    file_size: int
    page_count: int
    object_count: int
    sha256_hash: str
    pdf_objects: List[PdfObject] = Field(default_factory=list)

    # Email context (nullable for manual uploads)
    email_subject: Optional[str] = None
    sender_email: Optional[str] = None
    received_date: Optional[datetime] = None

    class Config:
        from_attributes = True

    @classmethod
    def from_repository_data(cls, combined_data: Dict[str, Any]) -> 'EtoRunWithPdfData':
        """
        Create EtoRunWithPdfData from repository combined data dict

        Args:
            combined_data: Dictionary from repository method

        Returns:
            EtoRunWithPdfData instance
        """
        # Parse PDF objects from JSON string if needed
        pdf_objects = []
        if combined_data.get('pdf_objects'):
            import json
            try:
                # If it's a string, parse it
                if isinstance(combined_data['pdf_objects'], str):
                    object_dicts = json.loads(combined_data['pdf_objects'])
                # If it's already a list, use it directly
                elif isinstance(combined_data['pdf_objects'], list):
                    object_dicts = combined_data['pdf_objects']
                else:
                    object_dicts = []

                # Convert to PdfObject instances
                pdf_objects = [PdfObject.from_db_model(obj_dict) for obj_dict in object_dicts]
            except (json.JSONDecodeError, TypeError, KeyError) as e:
                # Log warning but continue with empty list
                import logging
                logger = logging.getLogger(__name__)
                logger.warning(f"Failed to parse PDF objects for ETO run {combined_data.get('run_id')}: {e}")
                pdf_objects = []

        return cls(
            # ETO run data
            run_id=combined_data['run_id'],
            status=combined_data['status'],
            processing_step=combined_data.get('processing_step'),
            matched_template_id=combined_data.get('matched_template_id'),
            extracted_data=combined_data.get('extracted_data'),
            transformation_audit=combined_data.get('transformation_audit'),
            target_data=combined_data.get('target_data'),
            error_type=combined_data.get('error_type'),
            error_message=combined_data.get('error_message'),
            created_at=combined_data['created_at'],
            started_at=combined_data.get('started_at'),
            completed_at=combined_data.get('completed_at'),

            # PDF file data
            pdf_id=combined_data['pdf_id'],
            filename=combined_data['filename'],
            original_filename=combined_data['original_filename'],
            file_size=combined_data['file_size'],
            page_count=combined_data['page_count'],
            object_count=combined_data.get('object_count', 0),
            sha256_hash=combined_data['sha256_hash'],
            pdf_objects=pdf_objects,

            # Email context (nullable)
            email_subject=combined_data.get('email_subject'),
            sender_email=combined_data.get('sender_email'),
            received_date=combined_data.get('received_date')
        )