"""
PDF Template Service
Service for template matching and management operations
"""
import json
import logging
from typing import Optional, List, Dict, Any, Tuple

from shared.database.repositories.pdf_template import PdfTemplateRepository
from shared.database.repositories.pdf_template_version import PdfTemplateVersionRepository
# PDF processing service will be injected through constructor
from shared.exceptions import ObjectNotFoundError

from shared.models import (
    PdfTemplate, PdfTemplateVersion, PdfTemplateCreate, PdfTemplateUpdate, PdfTemplateVersionCreate,
    PdfObjects, ExtractionField, PdfTemplateMatchResult
)

logger = logging.getLogger(__name__)

# Type alias for template matching tuple
TemplateMatch = Tuple[PdfTemplate, PdfTemplateVersion, int]


class PdfTemplateService:
    """Service for PDF template matching and management"""

    def __init__(self, connection_manager, pdf_service):
        if not connection_manager:
            raise RuntimeError("Database connection manager is required")

        self.connection_manager = connection_manager
        self.pdf_service = pdf_service

        # Repository layer - with explicit type annotations for IDE support
        self.pdf_template_repo: PdfTemplateRepository = PdfTemplateRepository(self.connection_manager)
        self.pdf_template_version_repo: PdfTemplateVersionRepository = PdfTemplateVersionRepository(self.connection_manager)

        logger.info("PDF Template Service initialized")

    # === Template Matching ===

    def find_best_template_match(self, pdf_objects: PdfObjects) -> PdfTemplateMatchResult:
        """
        Find the best matching template for a PDF document

        A template matches if ALL signature objects are found in the PDF.
        Among matching templates, ranking:
        1. First by total object count (more objects = better match)
        2. For ties, weighted ranking by object type priority

        Args:
            pdf_objects: Nested PDF objects extracted from the document

        Returns:
            PdfTemplateMatchResult with match details
        """
        try:
            # Get all active templates
            active_templates = self.pdf_template_repo.get_active_templates()

            if not active_templates:
                logger.info("No active templates found for matching")
                return PdfTemplateMatchResult(template_found=False)

            matching_templates: List[TemplateMatch] = []

            # Check each template's current version for complete match
            for template in active_templates:
                try:
                    # Get the current version for this template
                    current_version = self.get_current_version(template.id)
                    if not current_version:
                        logger.debug(f"Template {template.id} has no current version, skipping")
                        continue

                    # Check if all signature objects from current version are found in PDF
                    if self._is_complete_subset_match(pdf_objects, current_version.signature_objects):
                        total_count = self._count_total_objects(current_version.signature_objects)
                        matching_templates.append((template, current_version, total_count))
                        logger.debug(f"Template {template.id} (version {current_version.version_num}): COMPLETE MATCH with {total_count} objects")
                    else:
                        logger.debug(f"Template {template.id} (version {current_version.version_num}): incomplete match - skipped")

                except Exception as e:
                    logger.warning(f"Error checking template {template.id}: {e}")
                    continue

            if not matching_templates:
                logger.info("No template match found - no templates had all signature objects present")
                return PdfTemplateMatchResult(template_found=False)

            # Find the best match using corrected ranking
            try:
                best_match = self._find_best_match(matching_templates)
                template, version, total_count = best_match
            except ValueError as e:
                logger.error(f"Error finding best match: {e}")
                return PdfTemplateMatchResult(template_found=False)

            # Update version usage statistics
            self.pdf_template_version_repo.increment_usage_count(version.id)

            logger.info(f"Template match found: {template.id} (version {version.version_num}) with {total_count} total objects")

            return PdfTemplateMatchResult(
                template_found=True,
                template_id=template.id,
                template_version=version.version_num
            )

        except Exception as e:
            logger.error(f"Error in template matching: {e}")
            return PdfTemplateMatchResult(template_found=False)

    def _is_complete_subset_match(self, pdf_objects: PdfObjects, template_objects: PdfObjects) -> bool:
        """
        Check if template signature objects are a complete subset of PDF objects

        Args:
            pdf_objects: Nested PDF objects from target document
            template_objects: Nested template signature objects

        Returns:
            True if ALL template objects are found in PDF, False otherwise
        """
        # Check each object type
        return (
            self._match_text_words(pdf_objects.text_words, template_objects.text_words) and
            self._match_text_lines(pdf_objects.text_lines, template_objects.text_lines) and
            self._match_graphic_rects(pdf_objects.graphic_rects, template_objects.graphic_rects) and
            self._match_graphic_lines(pdf_objects.graphic_lines, template_objects.graphic_lines) and
            self._match_graphic_curves(pdf_objects.graphic_curves, template_objects.graphic_curves) and
            self._match_images(pdf_objects.images, template_objects.images) and
            self._match_tables(pdf_objects.tables, template_objects.tables)
        )

    def _find_best_match(self, matching_templates: List[TemplateMatch]) -> TemplateMatch:
        """
        Find best match using corrected ranking algorithm
        1. First by total object count (more objects = better)
        2. For ties, weighted ranking by object type priority

        Args:
            matching_templates: List of TemplateMatch tuples, must be non-empty

        Returns:
            Best TemplateMatch tuple (template, version, total_count)

        Raises:
            ValueError: If matching_templates is empty
        """
        if not matching_templates:
            raise ValueError("Cannot find best match from empty list")

        # Sort by total count descending first
        matching_templates.sort(key=lambda x: x[2], reverse=True)

        # Get the highest count
        max_count = matching_templates[0][2]

        # Find all templates with the max count (ties)
        tied_templates = [match for match in matching_templates if match[2] == max_count]

        if len(tied_templates) == 1:
            # No tie, return the winner
            return tied_templates[0]

        # Break ties using weighted ranking
        logger.debug(f"Breaking tie between {len(tied_templates)} templates with {max_count} objects each")

        best_match: Optional[TemplateMatch] = None
        best_weighted_score = -1.0

        for template, version, total_count in tied_templates:
            weighted_score = self._calculate_weighted_score(version.signature_objects)
            logger.debug(f"Template {template.id}: weighted score = {weighted_score}")

            if weighted_score > best_weighted_score:
                best_weighted_score = weighted_score
                best_match = (template, version, total_count)

        # This should never happen since we have at least one tied template
        if best_match is None:
            raise ValueError("Failed to determine best match from tied templates")

        return best_match

    def _count_total_objects(self, objects: PdfObjects) -> int:
        """Count total objects across all types"""
        return (
            len(objects.text_words) +
            len(objects.text_lines) +
            len(objects.graphic_rects) +
            len(objects.graphic_lines) +
            len(objects.graphic_curves) +
            len(objects.images) +
            len(objects.tables)
        )

    def _calculate_weighted_score(self, objects: PdfObjects) -> float:
        """
        Calculate weighted score for tie-breaking
        Higher priority object types get more weight
        """
        weights = {
            'text_words': 1.0,
            'text_lines': 2.0,
            'graphic_rects': 1.5,
            'graphic_lines': 1.2,
            'graphic_curves': 1.3,
            'images': 3.0,
            'tables': 4.0
        }

        score = (
            len(objects.text_words) * weights['text_words'] +
            len(objects.text_lines) * weights['text_lines'] +
            len(objects.graphic_rects) * weights['graphic_rects'] +
            len(objects.graphic_lines) * weights['graphic_lines'] +
            len(objects.graphic_curves) * weights['graphic_curves'] +
            len(objects.images) * weights['images'] +
            len(objects.tables) * weights['tables']
        )

        return score

    # === Type-specific matching methods ===

    def _match_text_words(self, pdf_words: List[Any], template_words: List[Any]) -> bool:
        """Match text word objects - returns True if all template words found"""
        if not template_words:
            return True  # Empty requirement always passes

        for template_word in template_words:
            if not self._find_text_word_match(pdf_words, template_word):
                return False
        return True

    def _match_text_lines(self, pdf_lines: List[Any], template_lines: List[Any]) -> bool:
        """Match text line objects - returns True if all template lines found"""
        if not template_lines:
            return True

        for template_line in template_lines:
            if not self._find_text_line_match(pdf_lines, template_line):
                return False
        return True

    def _match_graphic_rects(self, pdf_rects: List[Any], template_rects: List[Any]) -> bool:
        """Match graphic rectangle objects"""
        if not template_rects:
            return True

        for template_rect in template_rects:
            if not self._find_graphic_rect_match(pdf_rects, template_rect):
                return False
        return True

    def _match_graphic_lines(self, pdf_lines: List[Any], template_lines: List[Any]) -> bool:
        """Match graphic line objects"""
        if not template_lines:
            return True

        for template_line in template_lines:
            if not self._find_graphic_line_match(pdf_lines, template_line):
                return False
        return True

    def _match_graphic_curves(self, pdf_curves: List[Any], template_curves: List[Any]) -> bool:
        """Match graphic curve objects"""
        if not template_curves:
            return True

        for template_curve in template_curves:
            if not self._find_graphic_curve_match(pdf_curves, template_curve):
                return False
        return True

    def _match_images(self, pdf_images: List[Any], template_images: List[Any]) -> bool:
        """Match image objects"""
        if not template_images:
            return True

        for template_image in template_images:
            if not self._find_image_match(pdf_images, template_image):
                return False
        return True

    def _match_tables(self, pdf_tables: List[Any], template_tables: List[Any]) -> bool:
        """Match table objects"""
        if not template_tables:
            return True

        for template_table in template_tables:
            if not self._find_table_match(pdf_tables, template_table):
                return False
        return True

    # === Individual object matching methods ===

    def _find_text_word_match(self, pdf_words: List[Any], template_word: Any) -> bool:
        """Find matching text word with content and position tolerance"""
        position_tolerance = 10.0
        content_similarity_threshold = 0.8

        for pdf_word in pdf_words:
            if pdf_word.page != template_word.page:
                continue

            # Position matching
            if self._positions_match(pdf_word.bbox, template_word.bbox, position_tolerance):
                # Content matching
                if hasattr(template_word, 'text') and hasattr(pdf_word, 'text'):
                    if template_word.text and pdf_word.text:
                        similarity = self._calculate_text_similarity(template_word.text, pdf_word.text)
                        if similarity >= content_similarity_threshold:
                            return True
        return False

    def _find_text_line_match(self, pdf_lines: List[Any], template_line: Any) -> bool:
        """Find matching text line with content and position tolerance"""
        position_tolerance = 15.0  # Slightly more tolerance for lines
        content_similarity_threshold = 0.7  # Slightly lower for longer text

        for pdf_line in pdf_lines:
            if pdf_line.page != template_line.page:
                continue

            if self._positions_match(pdf_line.bbox, template_line.bbox, position_tolerance):
                if hasattr(template_line, 'text') and hasattr(pdf_line, 'text'):
                    if template_line.text and pdf_line.text:
                        similarity = self._calculate_text_similarity(template_line.text, pdf_line.text)
                        if similarity >= content_similarity_threshold:
                            return True
        return False

    def _find_graphic_rect_match(self, pdf_rects: List[Any], template_rect: Any) -> bool:
        """Find matching graphic rectangle by position and size"""
        position_tolerance = 5.0  # Tighter tolerance for graphics

        for pdf_rect in pdf_rects:
            if pdf_rect.page != template_rect.page:
                continue

            if self._positions_match(pdf_rect.bbox, template_rect.bbox, position_tolerance):
                return True
        return False

    def _find_graphic_line_match(self, pdf_lines: List[Any], template_line: Any) -> bool:
        """Find matching graphic line by position"""
        position_tolerance = 5.0

        for pdf_line in pdf_lines:
            if pdf_line.page != template_line.page:
                continue

            if self._positions_match(pdf_line.bbox, template_line.bbox, position_tolerance):
                return True
        return False

    def _find_graphic_curve_match(self, pdf_curves: List[Any], template_curve: Any) -> bool:
        """Find matching graphic curve by position"""
        position_tolerance = 8.0  # Curves might have slight variations

        for pdf_curve in pdf_curves:
            if pdf_curve.page != template_curve.page:
                continue

            if self._positions_match(pdf_curve.bbox, template_curve.bbox, position_tolerance):
                return True
        return False

    def _find_image_match(self, pdf_images: List[Any], template_image: Any) -> bool:
        """Find matching image by position and size"""
        position_tolerance = 3.0  # Very tight tolerance for images

        for pdf_image in pdf_images:
            if pdf_image.page != template_image.page:
                continue

            if self._positions_match(pdf_image.bbox, template_image.bbox, position_tolerance):
                return True
        return False

    def _find_table_match(self, pdf_tables: List[Any], template_table: Any) -> bool:
        """Find matching table by position"""
        position_tolerance = 10.0  # Tables might have slight layout variations

        for pdf_table in pdf_tables:
            if pdf_table.page != template_table.page:
                continue

            if self._positions_match(pdf_table.bbox, template_table.bbox, position_tolerance):
                return True
        return False

    def _positions_match(self, bbox1: List[float], bbox2: List[float], tolerance: float) -> bool:
        """Check if two bounding boxes match within tolerance"""
        center1_x = (bbox1[0] + bbox1[2]) / 2
        center1_y = (bbox1[1] + bbox1[3]) / 2
        center2_x = (bbox2[0] + bbox2[2]) / 2
        center2_y = (bbox2[1] + bbox2[3]) / 2

        x_diff = abs(center1_x - center2_x)
        y_diff = abs(center1_y - center2_y)

        return x_diff <= tolerance and y_diff <= tolerance

    def _calculate_text_similarity(self, text1: str, text2: str) -> float:
        """Calculate text similarity using character bigrams"""
        if not text1 or not text2:
            return 0.0

        text1 = text1.lower().strip()
        text2 = text2.lower().strip()

        if text1 == text2:
            return 1.0

        # Character bigram similarity
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
