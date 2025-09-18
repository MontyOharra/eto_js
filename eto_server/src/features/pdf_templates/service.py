"""
PDF Template Service
Service for template matching and management operations
"""
import json
import logging
from typing import Optional, List, Dict, Any

from shared.database import get_connection_manager
from shared.database.repositories.pdf_template_repository import PdfTemplateRepository
from shared.utils import get_service, ServiceNames

from shared.domain import ( 
    TemplateMatchResult, PdfObject, TemplateCreateRequest,
    TemplateVersionRequest, PdfTemplate, ExtractionField
)

logger = logging.getLogger(__name__)


class PdfTemplateService:
    """Service for PDF template matching and management"""

    def __init__(self):
        # Database infrastructure
        self.connection_manager = get_service(ServiceNames.CONNECTION_MANAGER)
        if not self.connection_manager:
            raise RuntimeError("Database connection manager is required")

        # Repository layer
        self.pdf_template_repo = PdfTemplateRepository(self.connection_manager)

        logger.info("PDF Template Service initialized")

    # === Template Matching ===

    def find_best_template_match(self, pdf_objects: List[PdfObject]) -> TemplateMatchResult:
        """
        Find the best matching template for a PDF document

        A template matches if ALL signature objects are found in the PDF.
        Among matching templates, choose the one with the most signature objects.

        Args:
            pdf_objects: List of PDF objects extracted from the document

        Returns:
            TemplateMatchResult with match details
        """
        try:
            # Get all active templates
            active_templates = self.pdf_template_repo.get_active_templates()

            if not active_templates:
                logger.info("No active templates found for matching")
                return TemplateMatchResult(template_found=False)

            best_match = None
            most_signature_objects = 0

            # Check each template for complete match
            for template in active_templates:
                try:
                    all_objects_found = self._check_all_template_objects_found(pdf_objects, template)
                    signature_object_count = template.signature_object_count or 0

                    logger.debug(f"Template {template.id}: all objects found = {all_objects_found}, signature count = {signature_object_count}")

                    # Only consider templates where ALL signature objects are found
                    if all_objects_found and signature_object_count > most_signature_objects:
                        best_match = template
                        most_signature_objects = signature_object_count

                except Exception as e:
                    logger.warning(f"Error checking template {template.id}: {e}")
                    continue

            # Build result
            if best_match:
                # Update template usage statistics
                self.pdf_template_repo.increment_usage_count(best_match.id)

                logger.info(f"Template match found: {best_match.id} with {most_signature_objects} signature objects (all matched)")

                return TemplateMatchResult(
                    template_found=True,
                    template_id=best_match.id,
                    template_version=best_match.version,
                    coverage_percentage=100.0,  # Always 100% since all objects must be found
                    unmatched_object_count=None,  # Not needed
                    match_details=json.dumps({
                        "template_name": best_match.name,
                        "customer_name": best_match.customer_name,
                        "total_pdf_objects": len(pdf_objects),
                        "matched_signature_objects": most_signature_objects,
                        "match_type": "complete_match"
                    })
                )
            else:
                logger.info("No template match found - no templates had all signature objects present")
                return TemplateMatchResult(template_found=False)

        except Exception as e:
            logger.error(f"Error in template matching: {e}")
            return TemplateMatchResult(template_found=False)

    def _check_all_template_objects_found(self, pdf_objects: List[PdfObject], template: PdfTemplate) -> bool:
        """
        Check if ALL template signature objects are found in the PDF

        Args:
            pdf_objects: PDF objects to match against
            template: Template to check

        Returns:
            True if ALL signature objects are found, False otherwise
        """
        if not template.signature_objects:
            return False

        try:
            signature_objects = json.loads(template.signature_objects)
        except (json.JSONDecodeError, TypeError):
            logger.warning(f"Invalid signature objects JSON for template {template.id}")
            return False

        if not signature_objects:
            return False

        # Check that every signature object exists in the PDF
        for sig_obj_data in signature_objects:
            if not self._object_exists_in_pdf(sig_obj_data, pdf_objects):
                return False

        # All signature objects were found
        return True

    def _object_exists_in_pdf(self, signature_object: dict, pdf_objects: List[PdfObject]) -> bool:
        """
        Check if a signature object exists in the PDF objects using fuzzy matching

        Args:
            signature_object: Template signature object to find
            pdf_objects: PDF objects to search in

        Returns:
            True if object is found with sufficient similarity
        """
        sig_type = signature_object.get('object_type', '')
        sig_content = signature_object.get('content', '')
        sig_x = signature_object.get('x', 0)
        sig_y = signature_object.get('y', 0)
        sig_page = signature_object.get('page_number', 1)

        # Define matching tolerances
        position_tolerance = 10.0  # pixels
        content_similarity_threshold = 0.8  # 80% similarity for text content

        for pdf_obj in pdf_objects:
            # Basic type and page matching - use correct attribute names
            if pdf_obj.type != sig_type or pdf_obj.page != sig_page:
                continue

            # Position matching (within tolerance)
            x_diff = abs(pdf_obj.x - sig_x)
            y_diff = abs(pdf_obj.y - sig_y)

            if x_diff <= position_tolerance and y_diff <= position_tolerance:
                # Content matching for text objects - use 'text' attribute
                if sig_type == 'text' and sig_content and pdf_obj.text:
                    similarity = self._calculate_text_similarity(sig_content, pdf_obj.text)
                    if similarity >= content_similarity_threshold:
                        return True
                elif sig_type != 'text':
                    # For non-text objects, position match is sufficient
                    return True

        return False

    def _calculate_text_similarity(self, text1: str, text2: str) -> float:
        """
        Calculate text similarity using simple character-based comparison

        Args:
            text1: First text string
            text2: Second text string

        Returns:
            Similarity score (0.0 to 1.0)
        """
        if not text1 or not text2:
            return 0.0

        # Normalize text (lowercase, strip whitespace)
        text1 = text1.lower().strip()
        text2 = text2.lower().strip()

        if text1 == text2:
            return 1.0

        # Simple character-based similarity (Jaccard similarity on character bigrams)
        set1 = set(text1[i:i+2] for i in range(len(text1)-1))
        set2 = set(text2[i:i+2] for i in range(len(text2)-1))

        if not set1 and not set2:
            return 1.0
        if not set1 or not set2:
            return 0.0

        intersection = len(set1 & set2)
        union = len(set1 | set2)

        return intersection / union


    # === Template Management ===

    def create_template(self, template_request: TemplateCreateRequest) -> PdfTemplate:
        """
        Create a new PDF template

        Args:
            template_request: Template creation request

        Returns:
            Created template
        """
        # Convert objects and fields to JSON
        signature_objects_json = json.dumps([
            {
                'object_type': obj.type,
                'content': obj.text,
                'x': obj.x,
                'y': obj.y,
                'width': obj.width,
                'height': obj.height,
                'page_number': obj.page,
                'properties': {
                    'font_name': obj.font_name,
                    'font_size': obj.font_size,
                    'char_count': obj.char_count,
                    'bbox': obj.bbox
                }
            }
            for obj in template_request.signature_objects
        ])

        extraction_fields_json = json.dumps([
            {
                'label': field.label,
                'bounding_box': field.bounding_box,
                'page': field.page,
                'required': field.required,
                'validation_regex': field.validation_regex,
                'description': field.description
            }
            for field in template_request.extraction_fields
        ])

        template_data = {
            'name': template_request.name,
            'customer_name': template_request.customer_name,
            'description': template_request.description,
            'signature_objects': signature_objects_json,
            'signature_object_count': len(template_request.signature_objects),
            'extraction_fields': extraction_fields_json,
            'coverage_threshold': template_request.coverage_threshold,
            'is_complete': True,
            'version': 1,
            'is_current_version': True,
            'status': 'active',
            'usage_count': 0
        }

        template = self.pdf_template_repo.create(template_data)
        logger.info(f"Created new template: {template.id} - {template.name}")

        return template


    def get_template_by_id(self, template_id: int) -> Optional[PdfTemplate]:
        """Get a specific template by ID"""
        return self.pdf_template_repo.get_by_id(template_id)

    def get_active_templates(self) -> List[PdfTemplate]:
        """Get all active templates for matching"""
        return self.pdf_template_repo.get_active_templates()

    def get_templates_by_customer(self, customer_name: str) -> List[PdfTemplate]:
        """Get all templates for a specific customer"""
        return self.pdf_template_repo.get_by_customer_name(customer_name)

    def get_template_versions(self, base_template_id: int) -> List[PdfTemplate]:
        """Get all versions of a template"""
        return self.pdf_template_repo.get_template_versions(base_template_id)