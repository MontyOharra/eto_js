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
    TemplateMatch,
    TemplateMatchingResult,
)
from shared.types.pdf_files import PdfObjects, PdfFile
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

        Templates can be updated even when active. New versions are created automatically.

        Args:
            template_id: Template ID to update
            update_data: Unified PdfTemplateUpdate with all possible fields

        Returns:
            Tuple of (updated_template, current_version_num, pipeline_definition_id)

        Raises:
            ObjectNotFoundError: Template not found
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

    def match_template(self, pdf_objects: PdfObjects, pdf_page_count: int) -> Optional[tuple[int, int]]:
        """
        Find the best matching template for a PDF document.

        A template matches if:
        1. ALL signature objects are found in the PDF
        2. Page count exactly matches template's expected page_count

        Among matching templates, ranking:
        1. First by total object count (more objects = better match)
        2. For ties, weighted ranking by object type priority

        Args:
            pdf_objects: PDF objects extracted from the document
            pdf_page_count: Number of pages in the incoming PDF

        Returns:
            Tuple of (template_id, version_id) if match found, None otherwise
        """
        logger.debug(f"Starting template matching for PDF with {pdf_page_count} pages")

        try:
            # Get all active templates
            active_templates = self.template_repository.list_templates(status="active")

            if not active_templates:
                logger.debug("No active templates found for matching")
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

                    # Get source PDF page count for this template
                    source_pdf = self.pdf_files_service.get_pdf_file(template.source_pdf_id)
                    template_page_count = source_pdf.page_count

                    # Validate page count first (early rejection for performance)
                    if template_page_count is None:
                        logger.warning(
                            f"Template {template.id} source PDF has no page_count, skipping"
                        )
                        continue

                    if pdf_page_count != template_page_count:
                        logger.debug(
                            f"Template {template.id} (version {current_version.version_number}): "
                            f"Page count mismatch - PDF has {pdf_page_count} pages, "
                            f"template expects {template_page_count} pages"
                        )
                        continue  # Skip this template

                    # Check if all signature objects from current version are found in PDF
                    if self._is_complete_subset_match(pdf_objects, current_version.signature_objects):
                        total_count = self._count_total_objects(current_version.signature_objects)
                        matching_templates.append((template, current_version, total_count))
                        logger.debug(
                            f"Template {template.id} (version {current_version.version_number}): "
                            f"COMPLETE MATCH with {total_count} objects and {pdf_page_count} pages"
                        )
                    else:
                        logger.debug(
                            f"Template {template.id} (version {current_version.version_number}): "
                            f"Incomplete object match - skipped"
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

    def match_templates_multi_page(
        self,
        pdf_file: PdfFile,
        page_numbers: Optional[list[int]] = None
    ) -> TemplateMatchingResult:
        """
        Match templates page-by-page with multi-template support.

        NEW ALGORITHM (replacing match_template for multi-template matching):
        - Processes PDF page by page
        - Each page can match a different template
        - Matches are consecutive page ranges
        - Greedy approach: once pages are matched, they're consumed

        Args:
            pdf_file: Complete PDF file with extracted objects and page_count
            page_numbers: Optional list of specific page numbers to process.
                         If None, processes all pages (1 to page_count).
                         Used by worker during reprocessing of specific page subsets.

        Returns:
            TemplateMatchingResult with all matches and unmatched pages
        """
        from shared.types.pdf_templates import TemplateMatch, TemplateMatchingResult

        assert pdf_file.page_count is not None

        # Determine pages to process
        if page_numbers is not None:
            pages_to_process = sorted(page_numbers)
            logger.debug(
                f"Starting multi-page template matching for PDF {pdf_file.id} "
                f"(subset: {len(pages_to_process)} pages of {pdf_file.page_count} total)"
            )
        else:
            pages_to_process = list(range(1, pdf_file.page_count + 1))
            logger.debug(f"Starting multi-page template matching for PDF {pdf_file.id} ({pdf_file.page_count} pages)")

        try:
            # Get all active templates
            active_templates = self.template_repository.list_templates(status="active")
            if not active_templates:
                logger.debug("No active templates found for matching")
                # All pages are unmatched
                return TemplateMatchingResult(
                    matches=[],
                    unmatched_pages=pages_to_process
                )

            matches: list[TemplateMatch] = []
            unmatched_pages: list[int] = []

            # Track which pages we've processed
            pages_set = set(pages_to_process)
            processed_pages: set[int] = set()

            # Process pages in order
            page_index = 0
            while page_index < len(pages_to_process):
                current_page = pages_to_process[page_index]

                # Skip if already processed (consumed by a multi-page match)
                if current_page in processed_pages:
                    page_index += 1
                    continue
                logger.info(f"[MATCH-DEBUG] ========== Processing PDF page {current_page} ==========")

                # Find all templates that could match starting at current_page
                candidate_templates: list[tuple[PdfTemplateListView, PdfTemplateVersion, int]] = []

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

                        # Get template page count from source PDF
                        source_pdf = self.pdf_files_service.get_pdf_file(template.source_pdf_id)
                        template_page_count = source_pdf.page_count

                        if template_page_count is None:
                            logger.warning(f"Template {template.id} source PDF has no page_count, skipping")
                            continue

                        # Check if template can fit - all required pages must be in our subset
                        required_pages = list(range(current_page, current_page + template_page_count))
                        if not all(p in pages_set for p in required_pages):
                            logger.debug(
                                f"Template {template.id}: Required pages {required_pages} "
                                f"not all in subset {pages_to_process}"
                            )
                            continue

                        # Check if ALL template signature objects exist in PDF pages
                        if self._is_complete_multi_page_match(
                            pdf_file=pdf_file,
                            start_page=current_page,
                            template_version=current_version,
                            template_page_count=template_page_count
                        ):
                            candidate_templates.append((template, current_version, template_page_count))
                            logger.debug(
                                f"Template {template.id} (version {current_version.version_number}): "
                                f"MATCH for pages {current_page}-{current_page + template_page_count - 1}"
                            )
                        else:
                            logger.debug(
                                f"Template {template.id} (version {current_version.version_number}): "
                                f"No match starting at page {current_page}"
                            )

                    except Exception as e:
                        logger.warning(f"Error checking template {template.id}: {e}")
                        continue

                if not candidate_templates:
                    # No match for this page
                    logger.info(f"[MATCH-DEBUG] Page {current_page}: No template match found")
                    unmatched_pages.append(current_page)
                    processed_pages.add(current_page)
                    page_index += 1
                    continue

                # Find best match among candidates
                # Convert to format expected by existing _find_best_match
                # Need to calculate total object count for ranking
                candidates_with_count = []
                for template, version, page_count in candidate_templates:
                    total_count = self._count_total_objects(version.signature_objects)
                    candidates_with_count.append((template, version, total_count))

                try:
                    best_template, best_version, total_count = self._find_best_match(candidates_with_count)
                    # Get the page count for the best match
                    best_page_count = None
                    for template, version, page_count in candidate_templates:
                        if template.id == best_template.id and version.id == best_version.id:
                            best_page_count = page_count
                            break

                    if best_page_count is None:
                        raise ValueError("Could not find page count for best match")

                except ValueError as e:
                    logger.error(f"Error finding best match: {e}")
                    unmatched_pages.append(current_page)
                    processed_pages.add(current_page)
                    page_index += 1
                    continue

                # Record match
                matched_page_range = list(range(current_page, current_page + best_page_count))
                matches.append(TemplateMatch(
                    template_id=best_template.id,
                    version_id=best_version.id,
                    matched_pages=matched_page_range
                ))

                # Mark all matched pages as processed
                for p in matched_page_range:
                    processed_pages.add(p)

                # Update version usage statistics
                self.version_repository.increment_usage_count(best_version.id)

                logger.info(
                    f"[MATCH-DEBUG] Match recorded: Template {best_template.id} '{best_template.name}' "
                    f"(version {best_version.version_number}) for pages {matched_page_range}"
                )

                # Move to next unprocessed page
                page_index += 1

            logger.info(
                f"Multi-page matching complete: {len(matches)} matches, "
                f"{len(unmatched_pages)} unmatched pages"
            )

            return TemplateMatchingResult(
                matches=matches,
                unmatched_pages=unmatched_pages
            )

        except Exception as e:
            logger.error(f"Error in multi-page template matching: {e}", exc_info=True)
            raise ServiceError(f"Multi-page template matching failed: {str(e)}") from e

    def _filter_objects_by_page(self, pdf_objects: PdfObjects, page_num: int) -> PdfObjects:
        """
        Extract objects for a specific page from PdfObjects.

        Args:
            pdf_objects: Complete PdfObjects with all pages
            page_num: Page number to filter (1-indexed)

        Returns:
            PdfObjects containing only objects from the specified page
        """
        return PdfObjects(
            text_words=[obj for obj in pdf_objects.text_words if obj.page == page_num],
            graphic_rects=[obj for obj in pdf_objects.graphic_rects if obj.page == page_num],
            graphic_lines=[obj for obj in pdf_objects.graphic_lines if obj.page == page_num],
            graphic_curves=[obj for obj in pdf_objects.graphic_curves if obj.page == page_num],
            images=[obj for obj in pdf_objects.images if obj.page == page_num],
            tables=[obj for obj in pdf_objects.tables if obj.page == page_num]
        )


    def _group_objects_by_page(self, pdf_objects: PdfObjects) -> dict[int, PdfObjects]:
        """
        Group PDF objects by page number.

        Args:
            pdf_objects: Complete PdfObjects with all pages

        Returns:
            Dictionary mapping page_num -> PdfObjects for that page
        """
        # Find all unique page numbers across all object types
        all_pages: set[int] = set()

        for obj in pdf_objects.text_words:
            all_pages.add(obj.page)
        for obj in pdf_objects.graphic_rects:
            all_pages.add(obj.page)
        for obj in pdf_objects.graphic_lines:
            all_pages.add(obj.page)
        for obj in pdf_objects.graphic_curves:
            all_pages.add(obj.page)
        for obj in pdf_objects.images:
            all_pages.add(obj.page)
        for obj in pdf_objects.tables:
            all_pages.add(obj.page)

        # Build dictionary
        result: dict[int, PdfObjects] = {}
        for page_num in sorted(all_pages):
            result[page_num] = self._filter_objects_by_page(pdf_objects, page_num)

        return result

    def _remap_page_numbers(self, pdf_objects: PdfObjects, from_page: int, to_page: int) -> PdfObjects:
        """
        Remap page numbers in PdfObjects from one page to another.

        This is critical for multi-template matching where we need to compare
        template objects (with page numbers from the source PDF) against
        target PDF objects (with different page numbers).

        Example: Template page 1 objects need to match PDF page 5
        - Template objects have .page = 1
        - PDF objects have .page = 5
        - We remap template objects to .page = 5 so comparison works

        Args:
            pdf_objects: PdfObjects to remap
            from_page: Original page number to remap from
            to_page: Target page number to remap to

        Returns:
            New PdfObjects with remapped page numbers
        """
        from dataclasses import replace

        # Remap each object type
        remapped_text_words = [
            replace(obj, page=to_page) if obj.page == from_page else obj
            for obj in pdf_objects.text_words
        ]
        remapped_graphic_rects = [
            replace(obj, page=to_page) if obj.page == from_page else obj
            for obj in pdf_objects.graphic_rects
        ]
        remapped_graphic_lines = [
            replace(obj, page=to_page) if obj.page == from_page else obj
            for obj in pdf_objects.graphic_lines
        ]
        remapped_graphic_curves = [
            replace(obj, page=to_page) if obj.page == from_page else obj
            for obj in pdf_objects.graphic_curves
        ]
        remapped_images = [
            replace(obj, page=to_page) if obj.page == from_page else obj
            for obj in pdf_objects.images
        ]
        remapped_tables = [
            replace(obj, page=to_page) if obj.page == from_page else obj
            for obj in pdf_objects.tables
        ]

        return PdfObjects(
            text_words=remapped_text_words,
            graphic_rects=remapped_graphic_rects,
            graphic_lines=remapped_graphic_lines,
            graphic_curves=remapped_graphic_curves,
            images=remapped_images,
            tables=remapped_tables
        )

    def _is_complete_multi_page_match(
        self,
        pdf_file: PdfFile,
        start_page: int,
        template_version: PdfTemplateVersion,
        template_page_count: int
    ) -> bool:
        """
        Check if ALL template signature objects exist in PDF pages for multi-page template.

        For multi-page templates:
        - Template page 1 objects must exist in PDF page start_page
        - Template page 2 objects must exist in PDF page start_page + 1
        - etc.

        Args:
            pdf_file: Complete PDF file with extracted objects
            start_page: Starting page in PDF to match against (1-indexed)
            template_version: Template version with signature objects
            template_page_count: Number of pages in template

        Returns:
            True if ALL template signature objects match across all pages
        """
        logger.debug(
            f"[MATCH-DEBUG] _is_complete_multi_page_match called: "
            f"start_page={start_page}, template_page_count={template_page_count}, "
            f"pdf_total_pages={pdf_file.page_count}"
        )

        # Group template signature objects by page
        template_objects_by_page = self._group_objects_by_page(template_version.signature_objects)

        logger.debug(
            f"[MATCH-DEBUG] Template objects grouped by page: "
            f"pages={list(template_objects_by_page.keys())}"
        )

        # Group PDF objects by page (cache for efficiency)
        pdf_objects_by_page = self._group_objects_by_page(pdf_file.extracted_objects)

        # Check each template page against corresponding PDF page
        for template_page_num in range(1, template_page_count + 1):
            pdf_page_num = start_page + template_page_num - 1

            # Get objects for this specific page
            template_page_objects = template_objects_by_page.get(template_page_num, PdfObjects(
                text_words=[], graphic_rects=[], graphic_lines=[],
                graphic_curves=[], images=[], tables=[]
            ))
            pdf_page_objects = pdf_objects_by_page.get(pdf_page_num, PdfObjects(
                text_words=[], graphic_rects=[], graphic_lines=[],
                graphic_curves=[], images=[], tables=[]
            ))

            logger.debug(
                f"[MATCH-DEBUG] Comparing template_page={template_page_num} vs pdf_page={pdf_page_num}: "
                f"template_objs={self._count_total_objects(template_page_objects)}, "
                f"pdf_objs={self._count_total_objects(pdf_page_objects)}"
            )

            # CRITICAL FIX: Remap template object page numbers to match PDF page numbers
            # Template objects have page numbers from the source PDF (1, 2, 3...)
            # But we need to compare them against potentially different PDF pages
            # Example: Template page 1 needs to match PDF page 5
            # So we remap all template objects from page=1 to page=5 before comparison
            remapped_template_objects = self._remap_page_numbers(
                template_page_objects,
                from_page=template_page_num,
                to_page=pdf_page_num
            )

            logger.debug(
                f"[MATCH-DEBUG] Remapped template objects from page {template_page_num} to page {pdf_page_num}"
            )

            # Check if ALL template objects on this page exist in PDF page
            # Uses existing _is_complete_subset_match method
            if not self._is_complete_subset_match(pdf_page_objects, remapped_template_objects):
                logger.debug(
                    f"[MATCH-DEBUG] FAILED: Template page {template_page_num} objects not found in PDF page {pdf_page_num}"
                )
                return False

        logger.debug(f"[MATCH-DEBUG] SUCCESS: All {template_page_count} template pages matched starting at PDF page {start_page}")
        return True

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
        text_match = self._match_text_words(pdf_objects.text_words, template_objects.text_words)
        rect_match = self._match_graphic_rects(pdf_objects.graphic_rects, template_objects.graphic_rects)
        line_match = self._match_graphic_lines(pdf_objects.graphic_lines, template_objects.graphic_lines)
        curve_match = self._match_graphic_curves(pdf_objects.graphic_curves, template_objects.graphic_curves)
        image_match = self._match_images(pdf_objects.images, template_objects.images)
        table_match = self._match_tables(pdf_objects.tables, template_objects.tables)

        logger.debug(
            f"[MATCH-DEBUG] Object type matches: text={text_match} ({len(template_objects.text_words)} template), "
            f"rects={rect_match} ({len(template_objects.graphic_rects)} template), "
            f"lines={line_match} ({len(template_objects.graphic_lines)} template), "
            f"curves={curve_match} ({len(template_objects.graphic_curves)} template), "
            f"images={image_match} ({len(template_objects.images)} template), "
            f"tables={table_match} ({len(template_objects.tables)} template)"
        )

        return text_match and rect_match and line_match and curve_match and image_match and table_match

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
            'graphic_rects': 1.5,
            'graphic_lines': 1.2,
            'graphic_curves': 1.3,
            'images': 3.0,
            'tables': 4.0
        }

        score = (
            len(objects.text_words) * weights['text_words'] +
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
            Dict mapping field names to extracted text (for pipeline execution)
        """
        from features.eto_runs.utils.extraction import extract_data_from_pdf_objects

        # Get full extraction results with bbox data
        extraction_results = extract_data_from_pdf_objects(
            pdf_objects=pdf_objects,
            extraction_fields=extraction_fields
        )

        # Convert to dict format for pipeline execution
        return {
            result["name"]: result["extracted_value"]
            for result in extraction_results
        }
