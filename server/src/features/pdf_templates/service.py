"""
PDF Template Service
Outward-facing service for managing PDF template CRUD and lifecycle
"""
import logging
from typing import Literal, Any, Optional

from shared.database import DatabaseConnectionManager
from shared.database.repositories import (
    PdfTemplateRepository,
    PdfTemplateVersionRepository,
    PipelineDefinitionRepository,
)
from shared.types.pdf_templates import (
    PdfTemplateListView,
    PdfTemplate,
    PdfTemplateCreate,
    PdfTemplateUpdate,
    PdfTemplateVersion,
    PdfVersionSummary,
    ExtractionField as ExtractionFieldDomain,
    TemplateSimulateData,
    TemplateSimulateResult,
)
from shared.types.pdf_files import PdfObjects
from shared.types.pipelines import PipelineState as PipelineStateDomain
from shared.types.pipeline_definition_step import PipelineDefinitionStepCreate
from shared.exceptions.service import ObjectNotFoundError, ConflictError, ServiceError
from features.pipelines.service import PipelineService
from features.pipeline_execution.service import PipelineExecutionService
from features.pdf_files.service import PdfFilesService
from shared.types.pipeline_execution import PipelineExecutionResult
from api.mappers.pipelines import (
    convert_pipeline_state_to_domain,
    convert_visual_state_to_domain,
)

logger = logging.getLogger(__name__)


class PdfTemplateService:
    """
    PDF template management service.

    Handles CRUD operations and lifecycle management for PDF templates and versions.
    Manages template activation/deactivation and version history.
    """

    connection_manager: DatabaseConnectionManager
    template_repository: PdfTemplateRepository
    version_repository: PdfTemplateVersionRepository
    pipeline_repository: PipelineDefinitionRepository
    pipeline_execution_service: PipelineExecutionService

    def __init__(
        self,
        connection_manager: DatabaseConnectionManager,
        pipeline_service: 'PipelineService',
        pdf_files_service: 'PdfFilesService',
        pipeline_execution_service: PipelineExecutionService
    ) -> None:
        """
        Initialize PDF template service

        Args:
            connection_manager: Database connection manager
            pipeline_service: Pipeline service for pipeline operations
            pdf_files_service: PDF files service for text extraction
            pipeline_execution_service: Pipeline execution service for running pipelines
        """
        self.connection_manager = connection_manager
        self.template_repository = PdfTemplateRepository(connection_manager=connection_manager)
        self.version_repository = PdfTemplateVersionRepository(connection_manager=connection_manager)
        self.pipeline_repository = PipelineDefinitionRepository(connection_manager=connection_manager)
        self.pipeline_service = pipeline_service
        self.pdf_files_service = pdf_files_service
        self.pipeline_execution_service = pipeline_execution_service

    def list_templates(
        self,
        status: Literal["active", "inactive"] | None = None,
        sort_by: Literal["name", "status", "usage_count"] = "name",
        sort_order: Literal["asc", "desc"] = "asc"
    ) -> list[PdfTemplateListView]:
        """
        List PDF templates with filtering and sorting.

        Args:
            status: Filter by status ("active" or "inactive"), None for all
            sort_by: Field to sort by ("name", "status", "usage_count")
            sort_order: Sort direction ("asc" or "desc")

        Returns:
            List of PdfTemplateListView
        """
        # Parameters are validated by Pydantic at API layer
        # Just delegate to repository
        return self.template_repository.list_templates(
            status=status,
            sort_by=sort_by,
            sort_order=sort_order
        )

    def get_template(self, template_id: int) -> PdfTemplate:
        """
        Get PDF template metadata by ID.

        Args:
            template_id: Template ID

        Returns:
            PdfTemplate dataclass or None if not found
        """
        result = self.template_repository.get_by_id(template_id)

        if not result:
            raise ObjectNotFoundError(f"Template {template_id} not found")
        
        return result

    def get_version_list(self, template_id: int) -> list[tuple[int, int]]:
        """
        Get list of all version IDs and version numbers for a template.

        Used by GET /api/pdf-templates/{template_id}/versions endpoint.

        Args:
            template_id: Template ID

        Returns:
            List of tuples (version_id, version_number) ordered by version_number ASC

        Raises:
            ObjectNotFoundError: If template not found
        """
        # Verify template exists
        template = self.template_repository.get_by_id(template_id)
        if not template:
            raise ObjectNotFoundError(f"Template {template_id} not found")

        # Get version list from repository
        return self.version_repository.get_version_list_for_template(template_id)

    def get_version_by_id(self, version_id: int) -> PdfTemplateVersion:
        """
        Get specific version details by version ID.

        Used by GET /api/pdf-templates/versions/{version_id} endpoint.
        Called when viewing template details (current version) or switching versions.

        Args:
            version_id: Version record ID

        Returns:
            PdfTemplateVersion dataclass with full version details

        Raises:
            ObjectNotFoundError: If version not found
        """
        version = self.version_repository.get_by_id(version_id)
        if not version:
            raise ObjectNotFoundError(f"Version {version_id} not found")

        return version

    def update_template(
        self,
        template_id: int,
        update_data: PdfTemplateUpdate
    ) -> tuple[PdfTemplate, int, int]:
        """
        Update template with smart versioning logic.

        Flow:
        1. Simple Case: Only name/description changed
           → Update template table directly, return

        2. Version Case: signature_objects or extraction_fields changed (no pipeline)
           → Create new version with current pipeline_definition_id, return

        3. Complex Case: Pipeline fields changed
           → Validate/compile pipeline → Create pipeline_definition + compiled_plan + steps
           → Create new version with new pipeline_definition_id, return

        Args:
            template_id: Template ID to update
            update_data: Unified PdfTemplateUpdate with all possible fields

        Returns:
            Tuple of (updated_template, current_version_num, pipeline_definition_id)

        Raises:
            ObjectNotFoundError: Template not found
            ConflictError: Template is active and wizard data is being changed
            ValidationError: Pipeline validation fails
        """
        from shared.types.pdf_templates import PdfVersionCreate
        from shared.types.pipeline_definition import PipelineDefinitionCreate

        # Get current template
        template = self.template_repository.get_by_id(template_id)
        if not template:
            raise ObjectNotFoundError(f"Template {template_id} not found")

        if template.current_version_id:
            current_version = self.version_repository.get_by_id(template.current_version_id)

        assert current_version is not None

        # Detect what changed
        metadata_changed = update_data.name is not None or update_data.description is not None
        signature_changed = update_data.signature_objects is not None
        extraction_changed = update_data.extraction_fields is not None
        pipeline_changed = update_data.pipeline_state is not None or update_data.visual_state is not None

        wizard_data_changed = signature_changed or extraction_changed or pipeline_changed

        # Check: Cannot update wizard data while template is active
        if wizard_data_changed and template.status == "active":
            raise ConflictError(
                f"Template {template_id} is active. Deactivate first before updating wizard data."
            )

        # ==================== Case 1: Only Metadata Changed ====================
        if metadata_changed and not wizard_data_changed:
            updates = {}
            if update_data.name is not None:
                updates["name"] = update_data.name
            if update_data.description is not None:
                updates["description"] = update_data.description

            updated_template = self.template_repository.update(template_id, updates)
            if not updated_template:
                raise ServiceError(f"Failed to update template {template_id}")

            # Return current version info
            current_version_num = current_version.version_number
            pipeline_id = current_version.pipeline_definition_id
            return updated_template, current_version_num, pipeline_id

        # ==================== Case 2 & 3: Wizard Data Changed ====================
        with self.connection_manager.unit_of_work() as uow:
            pipeline_definition_id: int

            # Sub-case: Pipeline changed (Complex Case)
            if pipeline_changed:
                logger.info("Pipeline data changed - creating new pipeline definition")

                # Both pipeline_state and visual_state must be provided together
                if update_data.pipeline_state is None or update_data.visual_state is None:
                    raise ServiceError(
                        "Both pipeline_state and visual_state must be provided when updating pipeline"
                    )

                # Convert API types to domain types (handles both Pydantic models and dicts)
                pipeline_state_obj = convert_pipeline_state_to_domain(update_data.pipeline_state)
                visual_state_obj = convert_visual_state_to_domain(update_data.visual_state)

                # Create pipeline definition (validation, compilation, creation all handled)
                pipeline_create_data = PipelineDefinitionCreate(
                    pipeline_state=pipeline_state_obj,
                    visual_state=visual_state_obj
                )

                pipeline_definition = self.pipeline_service.create_pipeline_definition(pipeline_create_data)
                pipeline_definition_id = pipeline_definition.id
                logger.info(f"Created pipeline definition {pipeline_definition_id}")

            else:
                # Sub-case: No pipeline change - reuse current pipeline_definition_id
                if not current_version:
                    raise ServiceError(
                        f"Template {template_id} has no current version - cannot determine pipeline_definition_id"
                    )

                pipeline_definition_id = current_version.pipeline_definition_id
                logger.info(f"Reusing pipeline definition {pipeline_definition_id}")

            # Calculate next version number
            next_version_num = (current_version.version_number + 1) if current_version else 1

            # Create new version
            version_data = PdfVersionCreate(
                template_id=template_id,
                version_number=next_version_num,
                source_pdf_id=template.source_pdf_id,
                signature_objects=(
                    update_data.signature_objects
                    if update_data.signature_objects is not None
                    else current_version.signature_objects
                ),
                extraction_fields=(
                    update_data.extraction_fields
                    if update_data.extraction_fields is not None
                    else current_version.extraction_fields
                ),
                pipeline_definition_id=pipeline_definition_id
            )

            new_version = uow.pdf_template_versions.create(version_data)
            logger.info(f"Created version {next_version_num} for template {template_id}")

            # Update template metadata and point to new version
            updates : dict[str, Any] = {"current_version_id": new_version.id}
            if update_data.name is not None:
                updates["name"] = update_data.name
            if update_data.description is not None:
                updates["description"] = update_data.description

            updated_template = uow.pdf_templates.update(template_id, updates)
            if not updated_template:
                raise ServiceError(f"Failed to update template {template_id}")

            # Transaction commits automatically
            logger.info(
                f"Template {template_id} updated successfully: "
                f"version {next_version_num}, pipeline {pipeline_definition_id}"
            )
            return updated_template, next_version_num, pipeline_definition_id

    def create_template(self, template_data: PdfTemplateCreate) -> tuple[PdfTemplate, int, int]:
        """
        Create new PDF template with initial version atomically.

        Creates template + version 1 + pipeline definition in a single transaction.
        Template starts with status="inactive".

        Args:
            template_data: PdfTemplateCreate dataclass with all wizard data

        Returns:
            Tuple of (created_template, version_number, pipeline_definition_id)

        Raises:
            ServiceError: If creation fails at any step
        """
        from shared.types.pdf_templates import PdfVersionCreate
        from shared.types.pipeline_definition import PipelineDefinitionCreate

        try:
            with self.connection_manager.unit_of_work() as uow:
                # Step 1: Create pipeline definition (validation, compilation, hash-based dedup)
                logger.info("Creating pipeline definition for template")

                # Convert API types to domain types (handles both Pydantic models and dicts)
                pipeline_state_obj = convert_pipeline_state_to_domain(template_data.pipeline_state)
                visual_state_obj = convert_visual_state_to_domain(template_data.visual_state)

                # Create pipeline definition (handles validation, compilation, and creation)
                pipeline_create_data = PipelineDefinitionCreate(
                    pipeline_state=pipeline_state_obj,
                    visual_state=visual_state_obj
                )

                pipeline_definition = self.pipeline_service.create_pipeline_definition(pipeline_create_data)
                pipeline_definition_id = pipeline_definition.id
                logger.info(f"Created/reused pipeline definition {pipeline_definition_id}")

                # Step 2: Create template record (status=inactive, current_version_id=None initially)
                template = uow.pdf_templates.create(
                    name=template_data.name,
                    description=template_data.description,
                    source_pdf_id=template_data.source_pdf_id,
                    status="inactive"
                )

                # Step 3: Create version 1 with signature objects, extraction fields, and pipeline ID
                version_data = PdfVersionCreate(
                    template_id=template.id,
                    version_number=1,
                    source_pdf_id=template_data.source_pdf_id,
                    signature_objects=template_data.signature_objects,
                    extraction_fields=template_data.extraction_fields,
                    pipeline_definition_id=pipeline_definition_id
                )

                version = uow.pdf_template_versions.create(version_data)

                # Step 4: Update template to point to version 1 as current version
                updated_template = uow.pdf_templates.update(
                    template.id,
                    {"current_version_id": version.id}
                )

                if not updated_template:
                    raise ServiceError(f"Failed to update template {template.id} with current_version_id")

                # Transaction commits automatically when exiting context manager
                return updated_template, 1, pipeline_definition_id

        except Exception as e:
            # UoW automatically rolls back on exception
            logger.error(f"Error creating template: {e}", exc_info=True)
            raise ServiceError(f"Failed to create template: {str(e)}")

    def activate_template(self, template_id: int) -> PdfTemplate:
        """
        Activate a PDF template for ETO matching.

        Args:
            template_id: Template ID to activate

        Returns:
            Updated template metadata with active status

        Raises:
            ObjectNotFoundError: Template not found
            ConflictError: Template has no current version (cannot activate)
        """
        # Verify template exists
        template = self.template_repository.get_by_id(template_id)
        if not template:
            raise ObjectNotFoundError(f"Template {template_id} not found")

        # Verify template has a current version
        if template.current_version_id is None:
            raise ConflictError(
                f"Template {template_id} has no current version. Cannot activate template without a version."
            )

        # Update status to active
        updated_template = self.template_repository.update(template_id, {"status": "active"})
        if not updated_template:
            # This shouldn't happen since we verified it exists above
            raise ServiceError(f"Failed to activate template {template_id}")

        return updated_template

    def deactivate_template(self, template_id: int) -> PdfTemplate:
        """
        Deactivate a PDF template (stop using for ETO matching).

        Args:
            template_id: Template ID to deactivate

        Returns:
            Updated template metadata with inactive status

        Raises:
            ObjectNotFoundError: Template not found
        """
        # Verify template exists
        template = self.template_repository.get_by_id(template_id)
        if not template:
            raise ObjectNotFoundError(f"Template {template_id} not found")

        # Update status to inactive
        updated_template = self.template_repository.update(template_id, {"status": "inactive"})
        if not updated_template:
            # This shouldn't happen since we verified it exists above
            raise ServiceError(f"Failed to deactivate template {template_id}")

        return updated_template

    # ==================== Template Matching ====================

    def match_template(self, pdf_objects: PdfObjects) -> Optional[tuple[int, int]]:
        """
        Find the best matching template for a PDF document.

        A template matches if ALL signature objects are found in the PDF.
        Among matching templates, ranking:
        1. First by total object count (more objects = better match)
        2. For ties, weighted ranking by object type priority

        Args:
            pdf_objects: PDF objects extracted from the document

        Returns:
            Tuple of (template_id, version_id) if match found, None otherwise
        """
        logger.info("Starting template matching")

        try:
            # Get all active templates
            active_templates = self.template_repository.list_templates(status="active")

            if not active_templates:
                logger.info("No active templates found for matching")
                return None

            matching_templates: list[tuple[PdfTemplateListView, PdfTemplateVersion, int]] = []

            # Check each template's current version for complete match
            for template in active_templates:
                try:
                    # Skip if no current version
                    if template.current_version_id is None:
                        logger.debug(f"Template {template.id} has no current version, skipping")
                        continue

                    # Get the current version
                    current_version = self.version_repository.get_by_id(template.current_version_id)
                    if not current_version:
                        logger.debug(f"Template {template.id} current version not found, skipping")
                        continue

                    # Check if all signature objects from current version are found in PDF
                    if self._is_complete_subset_match(pdf_objects, current_version.signature_objects):
                        total_count = self._count_total_objects(current_version.signature_objects)
                        matching_templates.append((template, current_version, total_count))
                        logger.debug(
                            f"Template {template.id} (version {current_version.version_number}): "
                            f"COMPLETE MATCH with {total_count} objects"
                        )
                    else:
                        logger.debug(
                            f"Template {template.id} (version {current_version.version_number}): "
                            f"incomplete match - skipped"
                        )

                except Exception as e:
                    logger.warning(f"Error checking template {template.id}: {e}")
                    continue

            if not matching_templates:
                logger.info("No template match found - no templates had all signature objects present")
                return None

            # Find the best match using ranking algorithm
            try:
                best_match = self._find_best_match(matching_templates)
                template, version, total_count = best_match
            except ValueError as e:
                logger.error(f"Error finding best match: {e}")
                return None

            # Update version usage statistics
            self.version_repository.increment_usage_count(version.id)

            logger.info(
                f"Template match found: {template.id} (version {version.version_number}) "
                f"with {total_count} total objects"
            )

            return (template.id, version.id)

        except Exception as e:
            logger.error(f"Error in template matching: {e}", exc_info=True)
            return None

    def _is_complete_subset_match(self, pdf_objects: PdfObjects, template_objects: PdfObjects) -> bool:
        """
        Check if template signature objects are a complete subset of PDF objects.

        Args:
            pdf_objects: PDF objects from target document
            template_objects: Template signature objects

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

    def _find_best_match(
        self,
        matching_templates: list[tuple[PdfTemplateListView, PdfTemplateVersion, int]]
    ) -> tuple[PdfTemplateListView, PdfTemplateVersion, int]:
        """
        Find best match using ranking algorithm:
        1. First by total object count (more objects = better)
        2. For ties, weighted ranking by object type priority

        Args:
            matching_templates: List of tuples (template, version, total_count), must be non-empty

        Returns:
            Best match tuple (template, version, total_count)

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

        best_match: Optional[tuple[PdfTemplateListView, PdfTemplateVersion, int]] = None
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
        Calculate weighted score for tie-breaking.
        Higher priority object types get more weight.
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

    def _match_text_words(self, pdf_words: list, template_words: list) -> bool:
        """Match text word objects - returns True if all template words found"""
        if not template_words:
            return True  # Empty requirement always passes

        for template_word in template_words:
            if not self._find_text_word_match(pdf_words, template_word):
                return False
        return True

    def _match_text_lines(self, pdf_lines: list, template_lines: list) -> bool:
        """Match text line objects - returns True if all template lines found"""
        if not template_lines:
            return True

        for template_line in template_lines:
            if not self._find_text_line_match(pdf_lines, template_line):
                return False
        return True

    def _match_graphic_rects(self, pdf_rects: list, template_rects: list) -> bool:
        """Match graphic rectangle objects"""
        if not template_rects:
            return True

        for template_rect in template_rects:
            if not self._find_graphic_rect_match(pdf_rects, template_rect):
                return False
        return True

    def _match_graphic_lines(self, pdf_lines: list, template_lines: list) -> bool:
        """Match graphic line objects"""
        if not template_lines:
            return True

        for template_line in template_lines:
            if not self._find_graphic_line_match(pdf_lines, template_line):
                return False
        return True

    def _match_graphic_curves(self, pdf_curves: list, template_curves: list) -> bool:
        """Match graphic curve objects"""
        if not template_curves:
            return True

        for template_curve in template_curves:
            if not self._find_graphic_curve_match(pdf_curves, template_curve):
                return False
        return True

    def _match_images(self, pdf_images: list, template_images: list) -> bool:
        """Match image objects"""
        if not template_images:
            return True

        for template_image in template_images:
            if not self._find_image_match(pdf_images, template_image):
                return False
        return True

    def _match_tables(self, pdf_tables: list, template_tables: list) -> bool:
        """Match table objects"""
        if not template_tables:
            return True

        for template_table in template_tables:
            if not self._find_table_match(pdf_tables, template_table):
                return False
        return True

    # === Individual object matching methods ===

    def _find_text_word_match(self, pdf_words: list, template_word) -> bool:
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

    def _find_text_line_match(self, pdf_lines: list, template_line) -> bool:
        """Find matching text line by position (text lines only have bbox, no text content)"""
        position_tolerance = 15.0  # Slightly more tolerance for lines

        for pdf_line in pdf_lines:
            if pdf_line.page != template_line.page:
                continue

            if self._positions_match(pdf_line.bbox, template_line.bbox, position_tolerance):
                return True
        return False

    def _find_graphic_rect_match(self, pdf_rects: list, template_rect) -> bool:
        """Find matching graphic rectangle by position and size"""
        position_tolerance = 5.0  # Tighter tolerance for graphics

        for pdf_rect in pdf_rects:
            if pdf_rect.page != template_rect.page:
                continue

            if self._positions_match(pdf_rect.bbox, template_rect.bbox, position_tolerance):
                return True
        return False

    def _find_graphic_line_match(self, pdf_lines: list, template_line) -> bool:
        """Find matching graphic line by position"""
        position_tolerance = 5.0

        for pdf_line in pdf_lines:
            if pdf_line.page != template_line.page:
                continue

            if self._positions_match(pdf_line.bbox, template_line.bbox, position_tolerance):
                return True
        return False

    def _find_graphic_curve_match(self, pdf_curves: list, template_curve) -> bool:
        """Find matching graphic curve by position"""
        position_tolerance = 8.0  # Curves might have slight variations

        for pdf_curve in pdf_curves:
            if pdf_curve.page != template_curve.page:
                continue

            if self._positions_match(pdf_curve.bbox, template_curve.bbox, position_tolerance):
                return True
        return False

    def _find_image_match(self, pdf_images: list, template_image) -> bool:
        """Find matching image by position and size"""
        position_tolerance = 3.0  # Very tight tolerance for images

        for pdf_image in pdf_images:
            if pdf_image.page != template_image.page:
                continue

            if self._positions_match(pdf_image.bbox, template_image.bbox, position_tolerance):
                return True
        return False

    def _find_table_match(self, pdf_tables: list, template_table) -> bool:
        """Find matching table by position"""
        position_tolerance = 10.0  # Tables might have slight layout variations

        for pdf_table in pdf_tables:
            if pdf_table.page != template_table.page:
                continue

            if self._positions_match(pdf_table.bbox, template_table.bbox, position_tolerance):
                return True
        return False

    def _positions_match(self, bbox1: tuple[float, float, float, float], bbox2: tuple[float, float, float, float], tolerance: float) -> bool:
        """Check if two bounding boxes match within tolerance"""
        center1_x = (bbox1[0] + bbox1[2]) / 2
        center1_y = (bbox1[1] + bbox1[3]) / 2
        center2_x = (bbox2[0] + bbox2[2]) / 2
        center2_y = (bbox2[1] + bbox2[3]) / 2

        x_diff = abs(center1_x - center2_x)
        y_diff = abs(center1_y - center2_y)

        return x_diff <= tolerance and y_diff <= tolerance

    def _calculate_text_similarity(self, text1: str, text2: str) -> float:
        """Calculate text similarity using character bigrams (Jaccard similarity)"""
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

    # ==================== Template Simulation ====================

    def simulate(
        self,
        simulate_data: TemplateSimulateData
    ) -> TemplateSimulateResult:
        """
        Simulate template processing: extract data and execute pipeline.

        This method performs data extraction and pipeline execution without
        persistence. Used by the template builder to test templates before saving.

        Args:
            simulate_data: Template simulation data with pdf_objects, extraction_fields, and pipeline_state

        Returns:
            TemplateSimulateResult with extraction fields, extracted data, and execution result
        """
        logger.info(
            f"Simulating template: {len(simulate_data.extraction_fields)} fields, "
            f"{len(simulate_data.pipeline_state.modules)} modules"
        )

        # Extract text from PDF objects (no file I/O needed)
        extracted_data = self._extract_text_from_objects(
            pdf_objects=simulate_data.pdf_objects,
            extraction_fields=simulate_data.extraction_fields
        )

        # Compile and execute pipeline
        execution_result = self.pipeline_service.compile_and_execute(
            pipeline_state=simulate_data.pipeline_state,
            entry_values=extracted_data
        )

        # Return structured result
        return TemplateSimulateResult(
            extraction_fields=simulate_data.extraction_fields,
            extracted_data=extracted_data,
            execution_result=execution_result
        )

    def _extract_text_from_objects(
        self,
        pdf_objects: PdfObjects,
        extraction_fields: list[ExtractionFieldDomain]
    ) -> dict[str, str]:
        """
        Extract text from PDF objects based on extraction fields.

        This is a thin wrapper around the shared extraction utility.
        The actual extraction logic is in features.eto_runs.utils.extraction

        Args:
            pdf_objects: PdfObjects dataclass with text_words and other objects
            extraction_fields: List of extraction field domain objects

        Returns:
            Dict mapping field names to extracted text
        """
        from features.eto_runs.utils.extraction import extract_data_from_pdf_objects

        return extract_data_from_pdf_objects(
            pdf_objects=pdf_objects,
            extraction_fields=extraction_fields
        )
