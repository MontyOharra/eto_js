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
    
    def find_best_template_match(self, pdf_objects: List[Dict[str, Any]]) -> Dict[str, Any]:
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
            
            # Get all active templates
            templates = self._get_all_active_templates()
            if not templates:
                logger.info("No active templates found for matching")
                return self._no_match_result()
            
            logger.info(f"Checking {len(pdf_objects)} PDF objects against {len(templates)} templates")
            
            # Convert PDF objects to comparable format
            pdf_signatures = self._objects_to_signatures(pdf_objects)
            
            # Check each template for exact subset match
            match_candidates = []
            
            for template in templates:
                try:
                    template_objects = json.loads(template.signature_data) if template.signature_data else []
                    template_signatures = self._objects_to_signatures(template_objects)
                    
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
                    "signature_hash": best_match['template']['signature_hash']
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
                'signature_hash': template.signature_hash,
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
                signature_parts = [
                    obj.get('type', ''),
                    str(obj.get('page', 0)),
                    json.dumps(obj.get('bbox', []), sort_keys=True),
                    str(obj.get('width', 0)),
                    str(obj.get('height', 0))
                ]
                
                # Add type-specific signature components
                if obj.get('type') in ['word', 'text_line']:
                    signature_parts.extend([
                        obj.get('fontname', ''),
                        str(obj.get('fontsize', 0)),
                        str(obj.get('char_count', 0))
                    ])
                elif obj.get('type') == 'rect':
                    signature_parts.extend([
                        str(obj.get('linewidth', 0)),
                        str(obj.get('has_stroke', False)),
                        str(obj.get('has_fill', False))
                    ])
                elif obj.get('type') == 'graphic_line':
                    signature_parts.extend([
                        str(obj.get('linewidth', 0)),
                        str(obj.get('is_horizontal', False)),
                        str(obj.get('is_vertical', False)),
                        str(obj.get('length', 0))
                    ])
                elif obj.get('type') == 'table':
                    signature_parts.extend([
                        str(obj.get('rows', 0)),
                        str(obj.get('cols', 0)),
                        json.dumps(obj.get('column_types', []), sort_keys=True)
                    ])
                elif obj.get('type') == 'image':
                    signature_parts.extend([
                        obj.get('format', ''),
                        str(obj.get('aspect_ratio', 0)),
                        str(obj.get('width_pixels', 0)),
                        str(obj.get('height_pixels', 0))
                    ])
                elif obj.get('type') == 'curve':
                    signature_parts.extend([
                        str(obj.get('point_count', 0)),
                        str(obj.get('path_length', 0)),
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
                                   pdf_objects: List[Dict[str, Any]], signature_hash: str) -> Dict[str, Any]:
        """
        Create a new PDF template from extracted objects.
        This will be called by the client application.
        
        Args:
            name: Template name
            description: Template description
            customer_name: Customer name (optional)
            pdf_objects: List of PDF objects that define the template
            signature_hash: SHA-256 hash of the PDF signature
            
        Returns:
            Dictionary with template creation result
        """
        try:
            if not self.db_service:
                raise RuntimeError("Database service not configured")
            
            # Check if template with same signature already exists
            existing_template = self._find_template_by_signature(signature_hash)
            if existing_template:
                return {
                    "success": False,
                    "error": f"Template with identical signature already exists: '{existing_template.name}'",
                    "existing_template_id": existing_template.id
                }
            
            # Create template record
            session = self.db_service.get_session()
            try:
                template = PdfTemplate(
                    name=name,
                    description=description,
                    customer_name=customer_name,
                    signature_hash=signature_hash,
                    signature_data=json.dumps(pdf_objects, sort_keys=True),
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
                    "object_count": len(pdf_objects),
                    "signature_hash": signature_hash
                }
                
            finally:
                session.close()
                
        except Exception as e:
            logger.error(f"Error creating template: {e}")
            return {
                "success": False,
                "error": str(e)
            }
    
    def _find_template_by_signature(self, signature_hash: str) -> Optional[PdfTemplate]:
        """Find template by signature hash"""
        session = self.db_service.get_session()
        try:
            return session.query(PdfTemplate).filter(
                PdfTemplate.signature_hash == signature_hash,
                PdfTemplate.status == 'active'
            ).first()
        finally:
            session.close()
    
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