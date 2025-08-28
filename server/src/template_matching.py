"""
PDF Template Matching Service
Implements exact subset matching algorithm for PDF templates
"""

import json
import hashlib
import logging
from typing import List, Dict, Any, Optional, Tuple
from .database import get_db_service, PdfTemplate

logger = logging.getLogger(__name__)

class TemplateMatchingService:
    """Service for matching PDF objects against known templates using exact subset matching"""
    
    def __init__(self):
        self.db_service = None
    
    def set_database_service(self, db_service):
        """Set database service for template operations"""
        self.db_service = db_service
        logger.info("Database service configured for template matching")
    
    def extract_fields_from_pdf(self, pdf_objects: List[Dict[str, Any]], template_id: int) -> Dict[str, Any]:
        """
        Extract field data from PDF using spatial bounding boxes from matched template.
        
        Args:
            pdf_objects: List of extracted PDF objects 
            template_id: ID of matched template with extraction field definitions
            
        Returns:
            Dictionary with extracted field data by label name
        """
        try:
            if not self.db_service:
                raise RuntimeError("Database service not configured")
            
            # Get template with extraction fields
            template = self._get_template_by_id(template_id)
            if not template or not template.extraction_fields:
                logger.warning(f"Template {template_id} has no extraction fields defined")
                return {}
            
            extraction_fields = json.loads(template.extraction_fields)
            if not extraction_fields:
                logger.info(f"Template {template_id} has empty extraction fields")
                return {}
            
            logger.info(f"Extracting {len(extraction_fields)} fields from PDF with {len(pdf_objects)} objects")
            
            # Filter to only text objects for extraction
            text_objects = [obj for obj in pdf_objects if obj.get('type') in ['word', 'text_line']]
            logger.info(f"Found {len(text_objects)} text objects for extraction")
            
            extracted_data = {}
            
            # Process each extraction field
            for field in extraction_fields:
                try:
                    field_label = field.get('label', '')
                    field_page = field.get('page', 0) 
                    field_bbox = field.get('boundingBox', [0, 0, 0, 0])
                    
                    if not field_label or not field_bbox:
                        logger.warning(f"Invalid extraction field: missing label or bbox")
                        continue
                    
                    # Extract text within this field's bounding box
                    extracted_text = self._extract_text_in_bbox(text_objects, field_page, field_bbox)
                    
                    extracted_data[field_label] = {
                        'text': extracted_text,
                        'page': field_page,
                        'bbox': field_bbox,
                        'required': field.get('required', False),
                        'description': field.get('description', ''),
                        'validation_regex': field.get('validationRegex', None)
                    }
                    
                    logger.info(f"Extracted field '{field_label}': '{extracted_text[:50]}{'...' if len(extracted_text) > 50 else ''}'")
                    
                except Exception as field_error:
                    logger.error(f"Error extracting field {field.get('label', 'unknown')}: {field_error}")
                    continue
            
            logger.info(f"Successfully extracted {len(extracted_data)} fields")
            return extracted_data
            
        except Exception as e:
            logger.error(f"Error in field extraction: {e}")
            return {}
    
    def _extract_text_in_bbox(self, text_objects: List[Dict[str, Any]], target_page: int, bbox: List[float]) -> str:
        """
        Extract all text within a spatial bounding box on a specific page.
        
        Args:
            text_objects: List of text objects (words/text_lines) from PDF
            target_page: Page number (0-based)
            bbox: Bounding box [x0, y0, x1, y1] in PDF coordinates
            
        Returns:
            Concatenated text found within the bounding box
        """
        x0, y0, x1, y1 = bbox
        matching_texts = []
        
        for obj in text_objects:
            try:
                # Check if object is on the target page
                if obj.get('page', 0) != target_page:
                    continue
                
                obj_bbox = obj.get('bbox', [0, 0, 0, 0])
                ox0, oy0, ox1, oy1 = obj_bbox
                
                # Check if object is completely or mostly contained within the extraction bbox
                # Use center point method: include text if its center point is within the bounding box
                center_x = (ox0 + ox1) / 2
                center_y = (oy0 + oy1) / 2
                
                # Alternative approach: check if text is mostly within bounds (at least 30% overlap)
                overlap_x0 = max(ox0, x0)
                overlap_y0 = max(oy0, y0) 
                overlap_x1 = min(ox1, x1)
                overlap_y1 = min(oy1, y1)
                
                should_include = False
                
                # Calculate overlap area vs original object area
                if overlap_x1 > overlap_x0 and overlap_y1 > overlap_y0:
                    overlap_area = (overlap_x1 - overlap_x0) * (overlap_y1 - overlap_y0)
                    object_area = (ox1 - ox0) * (oy1 - oy0)
                    overlap_ratio = overlap_area / object_area if object_area > 0 else 0
                    
                    # Include text if center is within bounds OR significant overlap (>30%)
                    if ((center_x >= x0 and center_x <= x1 and center_y >= y0 and center_y <= y1) or 
                        overlap_ratio > 0.3):
                        should_include = True
                
                if should_include:
                    obj_text = obj.get('text', '').strip()
                    if obj_text:
                        matching_texts.append({
                            'text': obj_text,
                            'bbox': obj_bbox,
                            'y': (oy0 + oy1) / 2,  # Center Y for sorting
                            'x': (ox0 + ox1) / 2   # Center X for sorting
                        })
                
            except Exception as obj_error:
                logger.warning(f"Error checking text object: {obj_error}")
                continue
        
        if not matching_texts:
            return ""
        
        # Sort by Y coordinate (top to bottom), then by X coordinate (left to right)
        # Note: In PDF coordinates, Y increases upward, so higher Y = higher on page
        matching_texts.sort(key=lambda t: (-t['y'], t['x']))  # Negative Y for top-to-bottom sorting
        
        # Combine text with appropriate spacing
        extracted_text = ' '.join([t['text'] for t in matching_texts])
        return extracted_text.strip()
    
    def _get_template_by_id(self, template_id: int) -> Optional[PdfTemplate]:
        """Get template by ID"""
        session = self.db_service.get_session()
        try:
            return session.query(PdfTemplate).filter(
                PdfTemplate.id == template_id,
                PdfTemplate.status == 'active'
            ).first()
        finally:
            session.close()

    def find_best_template_match(self, pdf_objects: List[Dict[str, Any]], exclude_types: List[str] = None) -> Dict[str, Any]:
        """
        Find the best template match using exact subset matching algorithm.
        
        A template matches if ALL of its objects are found as exact matches in the PDF.
        The "best" match is the template with the LARGEST number of matching objects.
        
        This ensures that:
        - If a PDF has extra fields on top of an existing template, no match is found
        - If a PDF is missing even one field from a template, no match is found
        - Only exact subsets are considered matches
        
        Args:
            pdf_objects: List of extracted PDF objects
            
        Returns:
        {
            "matched": bool,
            "template_id": int (if matched),
            "template_name": str (if matched),
            "confidence": float,
            "match_count": int,
            "total_template_objects": int,
            "match_details": Dict,
            "candidates": List[Dict] (templates that were considered)
        }
        """
        try:
            if not self.db_service:
                raise RuntimeError("Database service not configured")
            
            # Filter out excluded object types (if any)
            if exclude_types is None:
                exclude_types = []  # Default: no exclusions, images now use geometric signatures
            
            filtered_pdf_objects = [obj for obj in pdf_objects if obj.get('type') not in exclude_types] if exclude_types else pdf_objects
            if exclude_types:
                logger.info(f"Filtered PDF objects: {len(pdf_objects)} -> {len(filtered_pdf_objects)} (excluded: {exclude_types})")
            else:
                logger.info(f"Using all {len(pdf_objects)} PDF objects (no exclusions)")
            
            # Get all active templates
            templates = self._get_all_active_templates()
            if not templates:
                logger.info("No active templates found for matching")
                return self._no_match_result()
            
            logger.info(f"Checking {len(filtered_pdf_objects)} PDF objects against {len(templates)} templates")
            
            # Convert PDF objects to comparable format
            pdf_signatures = self._objects_to_signatures(filtered_pdf_objects)
            
            # Check each template for exact subset match
            match_candidates = []
            
            for template in templates:
                try:
                    template_objects = json.loads(template.signature_objects) if template.signature_objects else []
                    # Filter template objects with same exclusions (if any)
                    filtered_template_objects = [obj for obj in template_objects if obj.get('type') not in exclude_types] if exclude_types else template_objects
                    template_signatures = self._objects_to_signatures(filtered_template_objects)
                    
                    match_result = self._check_exact_subset_match(pdf_signatures, template_signatures, template)
                    
                    if match_result['is_exact_match']:
                        match_candidates.append(match_result)
                        logger.info(f"Template '{template.name}' is exact subset match with {match_result['match_count']} objects")
                    else:
                        logger.debug(f"Template '{template.name}' not exact match: {match_result['match_count']}/{match_result['template_object_count']} objects matched")
                        
                except Exception as template_error:
                    logger.error(f"Error checking template {template.id}: {template_error}")
                    continue
            
            # Find the best match (largest exact subset)
            if not match_candidates:
                logger.info("No exact template matches found")
                return self._no_match_result(candidates=[])
            
            # Sort by match count (largest first), then by template age (newest first)
            best_match = max(match_candidates, key=lambda x: (x['match_count'], x['template']['created_at']))
            
            logger.info(f"Best template match: '{best_match['template']['name']}' with {best_match['match_count']} matching objects")
            
            return {
                "matched": True,
                "template_id": best_match['template']['id'],
                "template_name": best_match['template']['name'],
                "confidence": 1.0,  # Exact match always has 100% confidence
                "match_count": best_match['match_count'],
                "total_template_objects": best_match['template_object_count'],
                "match_details": {
                    "exact_subset_match": True,
                    "matching_objects": best_match['match_count'],
                    "template_objects": best_match['template_object_count'],
                    "pdf_objects": len(pdf_objects),
                    "template_id": best_match['template']['id']
                },
                "candidates": match_candidates
            }
            
        except Exception as e:
            logger.error(f"Error in template matching: {e}")
            return {
                "matched": False,
                "error": str(e),
                "candidates": []
            }
    
    def _check_exact_subset_match(self, pdf_signatures: List[str], template_signatures: List[str], template: PdfTemplate) -> Dict[str, Any]:
        """
        Check if template signatures are an exact subset of PDF signatures.
        
        For a match:
        - ALL template signatures must be found in PDF signatures
        - Template can be smaller than PDF (PDF can have extra objects)
        - But template cannot be larger than PDF (PDF cannot miss template objects)
        """
        template_signature_set = set(template_signatures)
        pdf_signature_set = set(pdf_signatures)
        
        # Find matching signatures
        matching_signatures = template_signature_set.intersection(pdf_signature_set)
        match_count = len(matching_signatures)
        template_object_count = len(template_signatures)
        
        # Exact subset match: ALL template objects must be found in PDF
        is_exact_match = match_count == template_object_count and template_object_count > 0
        
        return {
            'is_exact_match': is_exact_match,
            'match_count': match_count,
            'template_object_count': template_object_count,
            'matching_signatures': list(matching_signatures),
            'missing_signatures': list(template_signature_set - pdf_signature_set),
            'extra_pdf_signatures': list(pdf_signature_set - template_signature_set),
            'template': {
                'id': template.id,
                'name': template.name,
                'created_at': template.created_at.isoformat() if template.created_at else None
            }
        }
    
    def _objects_to_signatures(self, objects: List[Dict[str, Any]]) -> List[str]:
        """
        Convert PDF objects to signature strings for matching.
        
        Each object gets converted to a unique string that captures its
        essential characteristics for template matching.
        """
        signatures = []
        
        for obj in objects:
            try:
                # Create signature based on object type and key properties
                # Use rounded coordinates and dimensions for more flexible matching
                bbox = obj.get('bbox', [0, 0, 0, 0])
                # Ensure bbox values are consistently formatted as floats with 1 decimal place
                formatted_bbox = [f"{round(coord, 1):.1f}" for coord in bbox] if bbox else ["0.0", "0.0", "0.0", "0.0"]
                
                signature_parts = [
                    obj.get('type', ''),
                    f"{round(obj.get('page', 0), 0):.0f}",  # Page as float with 0 decimals
                    json.dumps(formatted_bbox, sort_keys=True),  # Use string-formatted bbox values
                    f"{round(obj.get('width', 0), 1):.1f}",  # Force 1 decimal place
                    f"{round(obj.get('height', 0), 1):.1f}"   # Force 1 decimal place
                ]
                
                # Add type-specific signature components
                if obj.get('type') in ['word', 'text_line']:
                    signature_parts.extend([
                        obj.get('fontname', ''),
                        f"{round(obj.get('fontsize', 0), 1):.1f}",
                        f"{round(obj.get('char_count', 0), 0):.0f}"  # Char count as float with 0 decimals
                    ])
                elif obj.get('type') == 'rect':
                    signature_parts.extend([
                        f"{round(obj.get('linewidth', 0), 1):.1f}",
                        str(obj.get('has_stroke', False)),
                        str(obj.get('has_fill', False))
                    ])
                elif obj.get('type') == 'graphic_line':
                    signature_parts.extend([
                        f"{round(obj.get('linewidth', 0), 1):.1f}",
                        str(obj.get('is_horizontal', False)),
                        str(obj.get('is_vertical', False)),
                        f"{round(obj.get('length', 0), 1):.1f}"
                    ])
                elif obj.get('type') == 'table':
                    signature_parts.extend([
                        f"{round(obj.get('rows', 0), 0):.0f}",      # Rows as float with 0 decimals
                        f"{round(obj.get('cols', 0), 0):.0f}",      # Cols as float with 0 decimals
                        json.dumps(obj.get('column_types', []), sort_keys=True)
                    ])
                elif obj.get('type') == 'image':
                    # For images, focus on geometric properties rather than content properties
                    # This makes image matching more reliable across extractions
                    signature_parts.extend([
                        f"{round(obj.get('aspect_ratio', 0), 2):.2f}",  # Force 2 decimal places
                        # Skip format as it can be inconsistent
                        # Skip pixel dimensions as they can vary, width/height already included above
                    ])
                elif obj.get('type') == 'curve':
                    signature_parts.extend([
                        f"{round(obj.get('point_count', 0), 0):.0f}",  # Point count as float with 0 decimals
                        f"{round(obj.get('path_length', 0), 1):.1f}",
                        str(obj.get('is_closed', False))
                    ])
                
                # Create hash of signature parts
                signature_string = '|'.join(signature_parts)
                signature_hash = hashlib.md5(signature_string.encode()).hexdigest()
                signatures.append(signature_hash)
                
            except Exception as e:
                logger.warning(f"Error creating signature for object {obj.get('type', 'unknown')}: {e}")
                continue
        
        return signatures
    
    def _get_signature_components(self, obj: Dict[str, Any]) -> Dict[str, Any]:
        """
        Get the signature components for an object without hashing (for debugging).
        Returns the actual values that would be used to create the signature.
        """
        try:
            # Create signature based on object type and key properties
            # Use rounded coordinates and dimensions for more flexible matching
            bbox = obj.get('bbox', [0, 0, 0, 0])
            # Use same formatting as actual signature generation
            formatted_bbox = [f"{round(coord, 1):.1f}" for coord in bbox] if bbox else ["0.0", "0.0", "0.0", "0.0"]
            
            components = {
                'type': obj.get('type', ''),
                'page': round(obj.get('page', 0), 0),  # Float with 0 decimals for consistency
                'bbox': formatted_bbox,  # Use string-formatted bbox like signature generation
                'width': round(obj.get('width', 0), 1),
                'height': round(obj.get('height', 0), 1)
            }
            
            # Add type-specific signature components
            if obj.get('type') in ['word', 'text_line']:
                components.update({
                    'fontname': obj.get('fontname', ''),
                    'fontsize': round(obj.get('fontsize', 0), 1),
                    'char_count': round(obj.get('char_count', 0), 0)  # Float with 0 decimals
                })
            elif obj.get('type') == 'rect':
                components.update({
                    'linewidth': round(obj.get('linewidth', 0), 1),
                    'has_stroke': obj.get('has_stroke', False),
                    'has_fill': obj.get('has_fill', False)
                })
            elif obj.get('type') == 'graphic_line':
                components.update({
                    'linewidth': round(obj.get('linewidth', 0), 1),
                    'is_horizontal': obj.get('is_horizontal', False),
                    'is_vertical': obj.get('is_vertical', False),
                    'length': round(obj.get('length', 0), 1)
                })
            elif obj.get('type') == 'table':
                components.update({
                    'rows': round(obj.get('rows', 0), 0),      # Float with 0 decimals
                    'cols': round(obj.get('cols', 0), 0),      # Float with 0 decimals
                    'column_types': obj.get('column_types', [])
                })
            elif obj.get('type') == 'image':
                components.update({
                    'aspect_ratio': round(obj.get('aspect_ratio', 0), 2)
                    # Note: format, width_pixels, height_pixels excluded for reliable matching
                })
            elif obj.get('type') == 'curve':
                components.update({
                    'point_count': round(obj.get('point_count', 0), 0),  # Float with 0 decimals
                    'path_length': round(obj.get('path_length', 0), 1),
                    'is_closed': obj.get('is_closed', False)
                })
            
            return components
            
        except Exception as e:
            logger.warning(f"Error creating signature components for object {obj.get('type', 'unknown')}: {e}")
            return {'error': str(e)}
    
    def _get_all_active_templates(self) -> List[PdfTemplate]:
        """Get all active PDF templates from database"""
        session = self.db_service.get_session()
        try:
            templates = session.query(PdfTemplate).filter(
                PdfTemplate.status == 'active'
            ).order_by(PdfTemplate.created_at.desc()).all()
            
            return templates
            
        finally:
            session.close()
    
    def _no_match_result(self, candidates: List[Dict] = None) -> Dict[str, Any]:
        """Return standard no-match result"""
        return {
            "matched": False,
            "template_id": None,
            "template_name": None,
            "confidence": 0.0,
            "match_count": 0,
            "total_template_objects": 0,
            "match_details": {
                "exact_subset_match": False,
                "reason": "No templates found with exact subset match"
            },
            "candidates": candidates or []
        }
    
    def create_template_from_objects(self, name: str, description: str, customer_name: str, 
                                   pdf_objects: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Create a new PDF template from extracted objects.
        This will be called by the client application.
        
        Args:
            name: Template name
            description: Template description
            customer_name: Customer name (optional)
            pdf_objects: List of PDF objects that define the template
            
        Returns:
            Dictionary with template creation result
        """
        try:
            if not self.db_service:
                raise RuntimeError("Database service not configured")
            
            # Create template record
            session = self.db_service.get_session()
            try:
                template = PdfTemplate(
                    name=name,
                    description=description,
                    customer_name=customer_name,
                    signature_objects=json.dumps(pdf_objects, sort_keys=True),
                    signature_object_count=len(pdf_objects),
                    status='active'
                )
                
                session.add(template)
                session.commit()
                session.refresh(template)
                
                logger.info(f"Created new template '{name}' with ID {template.id} and {len(pdf_objects)} objects")
                
                return {
                    "success": True,
                    "template_id": template.id,
                    "template_name": template.name,
                    "object_count": len(pdf_objects)
                }
                
            finally:
                session.close()
                
        except Exception as e:
            logger.error(f"Error creating template: {e}")
            return {
                "success": False,
                "error": str(e)
            }
    
    def get_template_statistics(self) -> Dict[str, Any]:
        """Get statistics about templates and matching"""
        try:
            session = self.db_service.get_session()
            try:
                from .database import EtoRun
                
                total_templates = session.query(PdfTemplate).filter(PdfTemplate.status == 'active').count()
                
                # Get matching statistics from ETO runs
                template_matches = session.query(EtoRun).filter(
                    EtoRun.template_match_result == 'matched'
                ).count()
                
                no_matches = session.query(EtoRun).filter(
                    EtoRun.template_match_result == 'no_match'
                ).count()
                
                pending_matches = session.query(EtoRun).filter(
                    EtoRun.status == 'unprocessed'
                ).count()
                
                return {
                    "total_templates": total_templates,
                    "successful_matches": template_matches,
                    "no_matches": no_matches,
                    "pending_matches": pending_matches,
                    "match_rate": round(template_matches / (template_matches + no_matches) * 100, 1) if (template_matches + no_matches) > 0 else 0
                }
                
            finally:
                session.close()
                
        except Exception as e:
            logger.error(f"Error getting template statistics: {e}")
            return {"error": str(e)}

# Global template matching service instance  
template_matcher = None

def init_template_matching(db_service):
    """Initialize template matching service"""
    global template_matcher
    template_matcher = TemplateMatchingService()
    template_matcher.set_database_service(db_service)
    logger.info("Template matching service initialized")
    return template_matcher

def get_template_matcher():
    """Get the global template matcher instance"""
    if template_matcher is None:
        raise RuntimeError("Template matcher not initialized. Call init_template_matching() first.")
    return template_matcher