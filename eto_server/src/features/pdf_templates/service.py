"""
PDF Template Service
Service for template matching and management operations
"""
import json
import logging
from typing import Optional, List, Dict, Any

from shared.database.repositories.pdf_template import PdfTemplateRepository
from shared.database.repositories.pdf_template_version import PdfTemplateVersionRepository
from shared.services import get_pdf_processing_service
from shared.exceptions import ObjectNotFoundError

from shared.models import (
    PdfTemplate, PdfTemplateVersion, PdfTemplateCreate, PdfTemplateUpdate, PdfTemplateVersionCreate,
    PdfObject, ExtractionField, PdfTemplateMatchResult
)

logger = logging.getLogger(__name__)


class PdfTemplateService:
    """Service for PDF template matching and management"""

    def __init__(self, connection_manager):
        if not connection_manager:
            raise RuntimeError("Database connection manager is required")

        self.connection_manager = connection_manager

        # Repository layer - with explicit type annotations for IDE support
        self.pdf_template_repo: PdfTemplateRepository = PdfTemplateRepository(self.connection_manager)
        self.pdf_template_version_repo: PdfTemplateVersionRepository = PdfTemplateVersionRepository(self.connection_manager)

        logger.info("PDF Template Service initialized")

    # === Template Matching ===

    def find_best_template_match(self, pdf_objects: List[PdfObject]) -> PdfTemplateMatchResult:
        """
        Find the best matching template for a PDF document

        A template matches if ALL signature objects are found in the PDF.
        Among matching templates, choose the one with the most signature objects.

        Args:
            pdf_objects: List of PDF objects extracted from the document

        Returns:
            PdfTemplateMatchResult with match details
        """
        try:
            # Get all active templates
            active_templates = self.pdf_template_repo.get_active_templates()

            if not active_templates:
                logger.info("No active templates found for matching")
                return PdfTemplateMatchResult(template_found=False)

            best_match_template = None
            best_match_version = None
            most_signature_objects = 0

            # Check each template's current version for complete match
            for template in active_templates:
                try:
                    # Get the current version for this template
                    current_version = self.get_current_version(template.id)
                    if not current_version:
                        logger.debug(f"Template {template.id} has no current version, skipping")
                        continue

                    # Check if all signature objects from current version are found in PDF
                    all_objects_found = self._check_all_version_objects_found(pdf_objects, current_version)
                    signature_object_count = current_version.signature_object_count

                    logger.debug(f"Template {template.id} (version {current_version.version_num}): all objects found = {all_objects_found}, signature count = {signature_object_count}")

                    # Only consider templates where ALL signature objects are found
                    if all_objects_found and signature_object_count > most_signature_objects:
                        best_match_template = template
                        best_match_version = current_version
                        most_signature_objects = signature_object_count

                except Exception as e:
                    logger.warning(f"Error checking template {template.id}: {e}")
                    continue

            # Build result
            if best_match_template and best_match_version:
                # Update version usage statistics
                self.pdf_template_version_repo.increment_usage_count(best_match_version.id)

                logger.info(f"Template match found: {best_match_template.id} (version {best_match_version.version_num}) with {most_signature_objects} signature objects (all matched)")

                return PdfTemplateMatchResult(
                    template_found=True,
                    template_id=best_match_template.id,
                    template_version=best_match_version.version_num,
                    coverage_percentage=100.0,  # Always 100% since all objects must be found
                    unmatched_object_count=None,  # Not needed
                    match_details=json.dumps({
                        "template_name": best_match_template.name,
                        "template_version": best_match_version.version_num,
                        "total_pdf_objects": len(pdf_objects),
                        "matched_signature_objects": most_signature_objects,
                        "match_type": "complete_match"
                    })
                )
            else:
                logger.info("No template match found - no templates had all signature objects present")
                return PdfTemplateMatchResult(template_found=False)

        except Exception as e:
            logger.error(f"Error in template matching: {e}")
            return PdfTemplateMatchResult(template_found=False)

    def _check_all_version_objects_found(self, pdf_objects: List[PdfObject], version: PdfTemplateVersion) -> bool:
        """
        Check if ALL version signature objects are found in the PDF

        Args:
            pdf_objects: PDF objects to match against
            version: Template version with typed signature objects

        Returns:
            True if ALL signature objects are found, False otherwise
        """
        if not version.signature_objects:
            return False

        # Check that every signature object exists in the PDF
        for signature_obj in version.signature_objects:
            if not self._object_exists_in_pdf(signature_obj, pdf_objects):
                return False

        # All signature objects were found
        return True

    def _object_exists_in_pdf(self, signature_object: PdfObject, pdf_objects: List[PdfObject]) -> bool:
        """
        Check if a typed signature object exists in the PDF objects using fuzzy matching

        Args:
            signature_object: Template signature object (typed PdfObject)
            pdf_objects: PDF objects to search in

        Returns:
            True if object is found with sufficient similarity
        """
        # Define matching tolerances
        position_tolerance = 10.0  # pixels
        content_similarity_threshold = 0.8  # 80% similarity for text content

        for pdf_obj in pdf_objects:
            # Basic type and page matching
            if pdf_obj.type != signature_object.type or pdf_obj.page != signature_object.page:
                continue

            # Position matching (within tolerance) using bounding box centers
            pdf_obj_center_x = (pdf_obj.bbox[0] + pdf_obj.bbox[2]) / 2
            pdf_obj_center_y = (pdf_obj.bbox[1] + pdf_obj.bbox[3]) / 2
            signature_center_x = (signature_object.bbox[0] + signature_object.bbox[2]) / 2
            signature_center_y = (signature_object.bbox[1] + signature_object.bbox[3]) / 2

            x_diff = abs(pdf_obj_center_x - signature_center_x)
            y_diff = abs(pdf_obj_center_y - signature_center_y)

            if x_diff <= position_tolerance and y_diff <= position_tolerance:
                # Content matching for text objects
                if signature_object.type == 'text' and signature_object.text and pdf_obj.text:
                    similarity = self._calculate_text_similarity(signature_object.text, pdf_obj.text)
                    if similarity >= content_similarity_threshold:
                        return True
                elif signature_object.type != 'text':
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

    def create_template(self, 
        pdf_template_data: PdfTemplateCreate
    ) -> PdfTemplate:
        """
        Create a new PDF template with its first version

        Args:
            name: Template name
            description: Template description
            pdf_id: Source PDF file ID
            signature_objects: Objects for template matching
            extraction_fields: Fields to extract from matching PDFs

        Returns:
            Created template (full domain object)
        """

        template = self.pdf_template_repo.create(pdf_template_data)
        new_template_id = template.id
  
        # Create first version using create model
        version_create = PdfTemplateVersionCreate(
            pdf_template_id=new_template_id,
            signature_objects=pdf_template_data.initial_signature_objects,
            extraction_fields=pdf_template_data.initial_extraction_fields,
            signature_object_count=len(pdf_template_data.initial_signature_objects)
        )
        version = self.pdf_template_version_repo.create(version_create)

        # Set as current version
        template = self.pdf_template_repo.set_current_version_id(template.id, version.id)
        
        if not template:
            raise ObjectNotFoundError("PdfTemplate", new_template_id)
          
        return template
    
    def create_template_version(self, version_create: PdfTemplateVersionCreate) -> PdfTemplateVersion:
        """
        Create a new version of a PDF template  
        
        Args:
            version_create: Template version create model with all required data
            
        Returns:
            Created template version (full domain object)
            
        Raises:
            ObjectNotFoundError: If the template doesn't exist
        """
        # First verify the template exists
        template = self.pdf_template_repo.get_by_id(version_create.pdf_template_id)
        if not template:
            raise ObjectNotFoundError("PdfTemplate", version_create.pdf_template_id)
        
        # Create the version (repository will auto-calculate version number)
        version = self.pdf_template_version_repo.create(version_create)
        
        # Set as current version
        updated_template = self.pdf_template_repo.set_current_version_id(version_create.pdf_template_id, version.id)
        if not updated_template:
            # This shouldn't happen since we just verified the template exists
            raise ObjectNotFoundError("PdfTemplate", version_create.pdf_template_id)
        
        return version
    
    def get_current_version(self, template_id: int) -> Optional[PdfTemplateVersion]:
        """Get the current active version for a template"""
        # Get template to find current_version_id
        template = self.pdf_template_repo.get_by_id(template_id)
        if not template or not template.current_version_id:
            return None
        
        # Get the specific version
        return self.pdf_template_version_repo.get_by_id(template.current_version_id)
    
    def get_templates(self, 
        status: Optional[str] = None,
        order_by: str = "created_at",
        desc: bool = False,
        limit: Optional[int] = None,
        offset: Optional[int] = None
    ) -> List[PdfTemplate]:
        """
        Get PDF templates with filtering and pagination
        
        Args:
            status: Filter by template status (active/inactive)
            order_by: Field to order by
            desc: Sort in descending order
            limit: Maximum number of templates to return
            offset: Number of templates to skip
            
        Returns:
            List of PDF template domain objects
        """
        return self.pdf_template_repo.get_all(
            status=status,
            order_by=order_by,
            desc=desc,
            limit=limit,
            offset=offset
        )
    
    def get_template_by_id(self, template_id: int) -> Optional[PdfTemplate]:
        """Get a single PDF template by ID"""
        return self.pdf_template_repo.get_by_id(template_id)
    
    def get_template_version(self, template_id: int, version_id: int) -> Optional[PdfTemplateVersion]:
        """Get a specific template version by template ID and version ID"""
        # First verify the template exists
        template = self.pdf_template_repo.get_by_id(template_id)
        if not template:
            return None
        
        # Get the specific version
        version = self.pdf_template_version_repo.get_by_id(version_id)
        if not version:
            return None
        
        # Verify the version belongs to the requested template
        if version.pdf_template_id != template_id:
            return None
        
        return version
    
    def update_template(self, template_id: int, update_data: PdfTemplateUpdate) -> Optional[PdfTemplate]:
        """Update a PDF template with the provided data"""
        return self.pdf_template_repo.update(template_id, update_data)

    def extract_data_from_template(self, template_id: int, pdf_objects: List[PdfObject]) -> Dict[str, Any]:
        """
        Extract data from PDF objects using a specific template

        Args:
            template_id: ID of the template to use for extraction
            pdf_objects: List of PDF objects to extract data from

        Returns:
            Dictionary with extracted field data {field_label: extracted_value}

        Raises:
            ObjectNotFoundError: If template doesn't exist
            ValueError: If template has no extraction fields
        """
        try:
            # Get current template version
            current_version = self.get_current_version(template_id)
            if not current_version:
                raise ObjectNotFoundError("PdfTemplate", template_id)

            if not current_version.extraction_fields:
                logger.warning(f"Template {template_id} has no extraction fields")
                return {}

            extracted_data = {}

            # Extract data for each field defined in the template
            for field in current_version.extraction_fields:
                try:
                    extracted_value = self._extract_field_value(field, pdf_objects)
                    extracted_data[field.label] = extracted_value

                    logger.debug(f"Extracted field '{field.label}': '{extracted_value}'")

                except Exception as e:
                    logger.warning(f"Failed to extract field '{field.label}': {e}")
                    # Handle required fields
                    if field.required:
                        extracted_data[field.label] = None
                        logger.error(f"Required field '{field.label}' extraction failed")
                    else:
                        extracted_data[field.label] = ""

            logger.info(f"Data extraction completed for template {template_id}: {len(extracted_data)} fields")
            return extracted_data

        except ObjectNotFoundError:
            raise
        except Exception as e:
            logger.error(f"Error extracting data with template {template_id}: {e}")
            raise ValueError(f"Data extraction failed: {str(e)}")

    def _extract_field_value(self, field: ExtractionField, pdf_objects: List[PdfObject]) -> str:
        """
        Extract value for a specific field from PDF objects

        Args:
            field: Extraction field definition with bounding box and validation rules
            pdf_objects: List of PDF objects to search

        Returns:
            Extracted text value for the field
        """
        # Find objects that fall within the extraction field's bounding box
        matching_objects = self._find_objects_in_bounding_box(field, pdf_objects)

        if not matching_objects:
            logger.debug(f"No objects found in bounding box for field '{field.label}'")
            return ""

        # Extract and aggregate text from matching objects
        text_values = []
        for obj in matching_objects:
            if obj.text and obj.text.strip():
                text_values.append(obj.text.strip())

        # Combine text values (sorted by position for reading order)
        if text_values:
            # Sort by position (top to bottom, left to right)
            matching_objects_with_text = [
                obj for obj in matching_objects
                if obj.text and obj.text.strip()
            ]
            matching_objects_with_text.sort(key=lambda obj: (obj.bbox[1], obj.bbox[0]))  # y, then x

            combined_text = " ".join([obj.text.strip() for obj in matching_objects_with_text])

            # Apply validation if specified
            if field.validation_regex:
                import re
                if not re.match(field.validation_regex, combined_text):
                    logger.warning(f"Field '{field.label}' value '{combined_text}' failed regex validation")

            return combined_text

        return ""

    def _find_objects_in_bounding_box(self, field: ExtractionField, pdf_objects: List[PdfObject]) -> List[PdfObject]:
        """
        Find PDF objects that fall within the extraction field's bounding box

        Args:
            field: Extraction field with bounding box coordinates
            pdf_objects: List of PDF objects to check

        Returns:
            List of PDF objects that intersect with the bounding box
        """
        matching_objects = []
        field_bbox = field.bounding_box  # [x0, y0, x1, y1]

        for obj in pdf_objects:
            # Only check objects on the correct page
            if obj.page != field.page:
                continue

            # Check if object's bounding box intersects with field's bounding box
            if self._bounding_boxes_intersect(obj.bbox, field_bbox):
                matching_objects.append(obj)

        return matching_objects

    def _bounding_boxes_intersect(self, bbox1: List[float], bbox2: List[float]) -> bool:
        """
        Check if two bounding boxes intersect

        Args:
            bbox1: First bounding box [x0, y0, x1, y1]
            bbox2: Second bounding box [x0, y0, x1, y1]

        Returns:
            True if bounding boxes intersect, False otherwise
        """
        # Bounding boxes intersect if they overlap in both x and y dimensions
        x_overlap = bbox1[0] < bbox2[2] and bbox2[0] < bbox1[2]  # x0 < x1' and x0' < x1
        y_overlap = bbox1[1] < bbox2[3] and bbox2[1] < bbox1[3]  # y0 < y1' and y0' < y1

        return x_overlap and y_overlap

    def is_healthy(self) -> bool:
        """
        Check if the PDF template service is healthy

        Returns:
            True if service is operational, False otherwise
        """
        try:
            # Check if we can access the repositories
            self.pdf_template_repo.count()
            self.pdf_template_version_repo.count()

            return True
        except Exception as e:
            logger.error(f"PDF template service health check failed: {e}")
            return False