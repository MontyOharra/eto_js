"""
PDF Template Service
Service for template matching and management operations
"""
import json
import logging
from typing import Optional, List, Dict, Any

from ...shared.database import get_connection_manager
from ...shared.database.repositories.pdf_template_repository import PdfTemplateRepository
from ...shared.utils import get_service, ServiceNames
from ...shared.domain.types import (
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
            best_coverage = 0.0

            # Calculate coverage for each template
            for template in active_templates:
                try:
                    coverage = self._calculate_template_coverage(pdf_objects, template)

                    logger.debug(f"Template {template.id} coverage: {coverage:.2f}% (threshold: {template.coverage_threshold:.2f}%)")

                    # Check if this template meets threshold and is better than current best
                    if coverage >= template.coverage_threshold and coverage > best_coverage:
                        best_match = template
                        best_coverage = coverage

                except Exception as e:
                    logger.warning(f"Error calculating coverage for template {template.id}: {e}")
                    continue

            # Build result
            if best_match:
                unmatched_count = self._count_unmatched_objects(pdf_objects, best_match)

                # Update template usage statistics
                self.pdf_template_repo.increment_usage_count(best_match.id)

                logger.info(f"Template match found: {best_match.id} with {best_coverage:.2f}% coverage")

                return TemplateMatchResult(
                    template_found=True,
                    template_id=best_match.id,
                    template_version=best_match.version,
                    coverage_percentage=best_coverage,
                    unmatched_object_count=unmatched_count,
                    match_details=json.dumps({
                        "template_name": best_match.name,
                        "customer_name": best_match.customer_name,
                        "total_pdf_objects": len(pdf_objects),
                        "matched_signature_objects": int(best_coverage * best_match.signature_object_count / 100) if best_match.signature_object_count else 0
                    })
                )
            else:
                logger.info("No template match found")
                return TemplateMatchResult(template_found=False)

        except Exception as e:
            logger.error(f"Error in template matching: {e}")
            return TemplateMatchResult(template_found=False)

    def _calculate_template_coverage(self, pdf_objects: List[PdfObject], template: PdfTemplate) -> float:
        """
        Calculate what percentage of template signature objects are found in PDF

        Args:
            pdf_objects: PDF objects to match against
            template: Template to check coverage for

        Returns:
            Coverage percentage (0.0 to 100.0)
        """
        if not template.signature_objects:
            return 0.0

        try:
            signature_objects = json.loads(template.signature_objects)
        except (json.JSONDecodeError, TypeError):
            logger.warning(f"Invalid signature objects JSON for template {template.id}")
            return 0.0

        if not signature_objects:
            return 0.0

        matched_count = 0

        for sig_obj_data in signature_objects:
            if self._object_exists_in_pdf(sig_obj_data, pdf_objects):
                matched_count += 1

        coverage = (matched_count / len(signature_objects)) * 100.0
        return coverage

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
            # Basic type and page matching
            if pdf_obj.object_type != sig_type or pdf_obj.page_number != sig_page:
                continue

            # Position matching (within tolerance)
            x_diff = abs(pdf_obj.x - sig_x)
            y_diff = abs(pdf_obj.y - sig_y)

            if x_diff <= position_tolerance and y_diff <= position_tolerance:
                # Content matching for text objects
                if sig_type == 'text' and sig_content and pdf_obj.content:
                    similarity = self._calculate_text_similarity(sig_content, pdf_obj.content)
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

    def _count_unmatched_objects(self, pdf_objects: List[PdfObject], template: PdfTemplate) -> int:
        """
        Count PDF objects that don't match any template signature object

        Args:
            pdf_objects: PDF objects to check
            template: Template with signature objects

        Returns:
            Number of unmatched objects
        """
        if not template.signature_objects:
            return len(pdf_objects)

        try:
            signature_objects = json.loads(template.signature_objects)
        except (json.JSONDecodeError, TypeError):
            return len(pdf_objects)

        unmatched_count = 0

        for pdf_obj in pdf_objects:
            # Convert PdfObject to dict for comparison
            pdf_obj_dict = {
                'object_type': pdf_obj.object_type,
                'content': pdf_obj.content,
                'x': pdf_obj.x,
                'y': pdf_obj.y,
                'page_number': pdf_obj.page_number
            }

            if not self._object_exists_in_pdf(pdf_obj_dict, []):  # We're checking if PDF object matches any signature
                # Check if this PDF object matches any signature object
                found_match = False
                for sig_obj in signature_objects:
                    if self._object_exists_in_pdf(sig_obj, [pdf_obj]):
                        found_match = True
                        break

                if not found_match:
                    unmatched_count += 1

        return unmatched_count

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
                'object_type': obj.object_type,
                'content': obj.content,
                'x': obj.x,
                'y': obj.y,
                'width': obj.width,
                'height': obj.height,
                'page_number': obj.page_number,
                'properties': obj.properties
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

    def create_template_version(self, version_request: TemplateVersionRequest) -> PdfTemplate:
        """
        Create a new version of an existing template

        Args:
            version_request: Template version creation request

        Returns:
            Created template version
        """
        # Get base template to determine next version number
        base_template = self.pdf_template_repo.get_by_id(version_request.base_template_id)
        if not base_template:
            raise ValueError(f"Base template {version_request.base_template_id} not found")

        # Mark previous versions as not current
        self.pdf_template_repo.mark_versions_as_not_current(version_request.base_template_id)

        # Get next version number
        next_version = self.pdf_template_repo.get_next_version_number(version_request.base_template_id)

        # Create new version (similar to create_template but with version info)
        signature_objects_json = json.dumps([
            {
                'object_type': obj.object_type,
                'content': obj.content,
                'x': obj.x,
                'y': obj.y,
                'width': obj.width,
                'height': obj.height,
                'page_number': obj.page_number,
                'properties': obj.properties
            }
            for obj in version_request.signature_objects
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
            for field in version_request.extraction_fields
        ])

        template_data = {
            'name': version_request.name,
            'customer_name': version_request.customer_name,
            'description': version_request.description,
            'signature_objects': signature_objects_json,
            'signature_object_count': len(version_request.signature_objects),
            'extraction_fields': extraction_fields_json,
            'coverage_threshold': version_request.coverage_threshold,
            'is_complete': True,
            'version': next_version,
            'is_current_version': True,
            'status': 'active',
            'usage_count': 0,
            'parent_template_id': version_request.base_template_id  # Link to original template
        }

        template = self.pdf_template_repo.create(template_data)
        logger.info(f"Created template version {next_version}: {template.id} - {template.name}")

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