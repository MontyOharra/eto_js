"""
Pipeline Service
Service layer for transformation pipeline operations including validation, retrieval, and management
"""
import logging
from typing import Optional, List, Dict, Any
from datetime import datetime

from src.shared.database.repositories import PipelineRepository, ObjectNotFoundError
from src.shared.models.pipeline import (
    Pipeline, PipelineCreate, PipelineUpdate,
    PipelineSummary, PipelineState, VisualState
)

logger = logging.getLogger(__name__)


class PipelineServiceError(Exception):
    """Base exception for pipeline service operations"""
    pass


class PipelineValidationError(PipelineServiceError):
    """Raised when pipeline validation fails"""
    def __init__(self, message: str, validation_errors: Optional[List[Dict[str, Any]]] = None):
        super().__init__(message)
        self.validation_errors = validation_errors or []


class PipelineService:
    """
    Service layer for pipeline operations
    Handles business logic, validation, and orchestration of pipeline management
    """

    def __init__(self, connection_manager, module_catalog_repository=None):
        """
        Initialize pipeline service

        Args:
            connection_manager: Database connection manager
            module_catalog_repository: Optional module catalog repo for validation
        """
        if not connection_manager:
            raise RuntimeError("Database connection manager is required")

        self.connection_manager = connection_manager
        self.pipeline_repo = PipelineRepository(connection_manager)
        self.module_catalog_repo = module_catalog_repository

        logger.info("Pipeline Service initialized")

    # ========== Retrieval Methods ==========

    def get_all_pipelines(
        self,
        include_archived: bool = False,
        filter_by_status: Optional[str] = None,
        filter_by_user: Optional[str] = None,
        search_term: Optional[str] = None,
        limit: Optional[int] = None,
        offset: Optional[int] = None,
        summary_only: bool = False
    ) -> List[Pipeline] | List[PipelineSummary]:
        """
        Get all pipelines with optional filtering

        Args:
            include_archived: Include archived pipelines in results
            filter_by_status: Filter by status (draft, active, archived)
            filter_by_user: Filter by creator user ID
            search_term: Search in name and description
            limit: Maximum number of results
            offset: Number of results to skip (for pagination)
            summary_only: Return lightweight summaries instead of full pipelines

        Returns:
            List of Pipeline or PipelineSummary objects based on summary_only flag

        Raises:
            PipelineServiceError: If retrieval fails
        """
        try:
            # If search term provided, use search functionality
            if search_term:
                results = self.pipeline_repo.search(search_term)
                # Search returns summaries, convert to full if needed
                if not summary_only and results:
                    pipeline_ids = [r.id for r in results]
                    results = [self.pipeline_repo.get_by_id(pid) for pid in pipeline_ids]
                    results = [r for r in results if r]  # Filter None values
            else:
                # Get all with basic filtering
                if summary_only:
                    results = self.pipeline_repo.get_summaries(include_archived=include_archived)
                else:
                    results = self.pipeline_repo.get_all(include_archived=include_archived)

            # Apply additional filters
            if filter_by_status and results:
                results = [p for p in results if p.status == filter_by_status]

            if filter_by_user and results:
                results = [p for p in results if p.created_by_user == filter_by_user]

            # Apply pagination
            if offset:
                results = results[offset:]
            if limit:
                results = results[:limit]

            logger.info(f"Retrieved {len(results)} pipelines with filters: "
                       f"status={filter_by_status}, user={filter_by_user}, "
                       f"search={search_term}, archived={include_archived}")

            return results

        except Exception as e:
            logger.error(f"Error retrieving pipelines: {e}")
            raise PipelineServiceError(f"Failed to retrieve pipelines: {e}") from e

    def get_pipeline_by_id(self, pipeline_id: str) -> Pipeline:
        """
        Get a specific pipeline by ID

        Args:
            pipeline_id: Pipeline ID to retrieve

        Returns:
            Pipeline object

        Raises:
            ObjectNotFoundError: If pipeline not found
            PipelineServiceError: If retrieval fails
        """
        try:
            pipeline = self.pipeline_repo.get_by_id(pipeline_id)

            if not pipeline:
                raise ObjectNotFoundError("Pipeline", pipeline_id)

            logger.info(f"Retrieved pipeline: {pipeline_id}")
            return pipeline

        except ObjectNotFoundError:
            raise
        except Exception as e:
            logger.error(f"Error retrieving pipeline {pipeline_id}: {e}")
            raise PipelineServiceError(f"Failed to retrieve pipeline: {e}") from e

    def get_pipelines_by_name(self, name: str) -> List[Pipeline]:
        """
        Get pipelines by name (can be multiple with same name)

        Args:
            name: Pipeline name to search for

        Returns:
            List of Pipeline objects

        Raises:
            PipelineServiceError: If retrieval fails
        """
        try:
            pipelines = self.pipeline_repo.get_by_name(name)
            logger.info(f"Found {len(pipelines)} pipelines with name: {name}")
            return pipelines

        except Exception as e:
            logger.error(f"Error retrieving pipelines by name '{name}': {e}")
            raise PipelineServiceError(f"Failed to retrieve pipelines by name: {e}") from e

    # ========== Validation Methods ==========

    def validate_pipeline(self, pipeline_state: PipelineState) -> List[Dict[str, Any]]:
        """
        Validate a pipeline structure for correctness

        TODO: Implement comprehensive validation including:
        - Structural graph checks (DAG, connections, types)
        - Module instance validation
        - Entry point validation
        - Type compatibility checks
        - Cycle detection
        - Reachability analysis

        Args:
            pipeline_state: Pipeline structure to validate

        Returns:
            List of validation errors (empty if valid)
        """
        validation_errors = []

        # TODO: Implement validation logic
        # This is a placeholder for the complex validation that needs to be implemented

        logger.warning("Pipeline validation not yet implemented - using placeholder")

        # Basic placeholder validations
        if not pipeline_state.entry_points:
            validation_errors.append({
                "type": "warning",
                "message": "Pipeline has no entry points",
                "severity": "low"
            })

        if not pipeline_state.modules:
            validation_errors.append({
                "type": "error",
                "message": "Pipeline has no modules",
                "severity": "high"
            })

        if not pipeline_state.connections and len(pipeline_state.modules) > 1:
            validation_errors.append({
                "type": "warning",
                "message": "Pipeline has multiple modules but no connections",
                "severity": "medium"
            })

        return validation_errors

    # ========== Creation and Update Methods ==========

    def create_pipeline(self, pipeline_create: PipelineCreate, skip_validation: bool = False) -> Pipeline:
        """
        Create a new pipeline with validation

        TODO: Implement full creation logic including:
        - Complete validation
        - Module reference verification
        - Plan checksum calculation
        - Compiled steps generation

        Args:
            pipeline_create: Pipeline creation data
            skip_validation: Skip validation if True (dangerous!)

        Returns:
            Created Pipeline object

        Raises:
            PipelineValidationError: If validation fails
            PipelineServiceError: If creation fails
        """
        try:
            # Validate pipeline unless explicitly skipped
            if not skip_validation:
                validation_errors = self.validate_pipeline(pipeline_create.pipeline_json)
                if validation_errors:
                    # Check if any errors are blocking (high severity)
                    blocking_errors = [e for e in validation_errors if e.get("severity") == "high"]
                    if blocking_errors:
                        raise PipelineValidationError(
                            "Pipeline validation failed with errors",
                            validation_errors
                        )
                    else:
                        # Log warnings but allow creation
                        logger.warning(f"Pipeline created with warnings: {validation_errors}")

            # TODO: Additional creation logic
            # - Verify all module_refs exist in module catalog
            # - Calculate plan checksum
            # - Generate compiled pipeline steps
            # - Validate type compatibility across connections

            # Create pipeline in repository
            pipeline = self.pipeline_repo.create(pipeline_create)

            logger.info(f"Created pipeline: {pipeline.id} with name '{pipeline.name}'")
            return pipeline

        except PipelineValidationError:
            raise
        except Exception as e:
            logger.error(f"Error creating pipeline: {e}")
            raise PipelineServiceError(f"Failed to create pipeline: {e}") from e

    def update_pipeline(
        self,
        pipeline_id: str,
        pipeline_update: PipelineUpdate,
        skip_validation: bool = False
    ) -> Pipeline:
        """
        Update an existing pipeline

        Args:
            pipeline_id: Pipeline ID to update
            pipeline_update: Update data
            skip_validation: Skip validation if True

        Returns:
            Updated Pipeline object

        Raises:
            ObjectNotFoundError: If pipeline not found
            PipelineValidationError: If validation fails
            PipelineServiceError: If update fails
        """
        try:
            # Check pipeline exists
            existing = self.pipeline_repo.get_by_id(pipeline_id)
            if not existing:
                raise ObjectNotFoundError("Pipeline", pipeline_id)

            # Validate if pipeline structure is being updated
            if pipeline_update.pipeline_json and not skip_validation:
                validation_errors = self.validate_pipeline(pipeline_update.pipeline_json)
                if validation_errors:
                    blocking_errors = [e for e in validation_errors if e.get("severity") == "high"]
                    if blocking_errors:
                        raise PipelineValidationError(
                            "Pipeline validation failed with errors",
                            validation_errors
                        )

            # Update pipeline
            updated = self.pipeline_repo.update(pipeline_id, pipeline_update)

            logger.info(f"Updated pipeline: {pipeline_id}")
            return updated

        except (ObjectNotFoundError, PipelineValidationError):
            raise
        except Exception as e:
            logger.error(f"Error updating pipeline {pipeline_id}: {e}")
            raise PipelineServiceError(f"Failed to update pipeline: {e}") from e

    # ========== Additional Operations ==========

    def duplicate_pipeline(self, pipeline_id: str, new_name: Optional[str] = None) -> Pipeline:
        """
        Duplicate an existing pipeline

        Args:
            pipeline_id: ID of pipeline to duplicate
            new_name: Optional new name for duplicate

        Returns:
            New Pipeline object

        Raises:
            ObjectNotFoundError: If source pipeline not found
            PipelineServiceError: If duplication fails
        """
        try:
            duplicated = self.pipeline_repo.duplicate(pipeline_id, new_name)
            logger.info(f"Duplicated pipeline {pipeline_id} to new pipeline {duplicated.id}")
            return duplicated

        except ObjectNotFoundError:
            raise
        except Exception as e:
            logger.error(f"Error duplicating pipeline {pipeline_id}: {e}")
            raise PipelineServiceError(f"Failed to duplicate pipeline: {e}") from e

    def delete_pipeline(self, pipeline_id: str, hard_delete: bool = False) -> bool:
        """
        Delete a pipeline

        Args:
            pipeline_id: Pipeline ID to delete
            hard_delete: Permanently delete if True, otherwise soft delete

        Returns:
            True if deleted successfully

        Raises:
            ObjectNotFoundError: If pipeline not found
            PipelineServiceError: If deletion fails
        """
        try:
            result = self.pipeline_repo.delete(pipeline_id, hard_delete=hard_delete)
            if not result:
                raise ObjectNotFoundError("Pipeline", pipeline_id)

            action = "hard deleted" if hard_delete else "soft deleted"
            logger.info(f"Pipeline {pipeline_id} {action}")
            return result

        except ObjectNotFoundError:
            raise
        except Exception as e:
            logger.error(f"Error deleting pipeline {pipeline_id}: {e}")
            raise PipelineServiceError(f"Failed to delete pipeline: {e}") from e

    def get_pipeline_statistics(self) -> Dict[str, Any]:
        """
        Get system-wide pipeline statistics

        Returns:
            Dictionary with pipeline statistics
        """
        try:
            stats = self.pipeline_repo.get_pipeline_stats()
            logger.info(f"Retrieved pipeline statistics: {stats}")
            return stats

        except Exception as e:
            logger.error(f"Error getting pipeline statistics: {e}")
            raise PipelineServiceError(f"Failed to get pipeline statistics: {e}") from e

    # ========== Validation Helper Methods (To Be Implemented) ==========

    def _validate_module_references(self, pipeline_state: PipelineState) -> List[Dict[str, Any]]:
        """
        TODO: Validate that all module references exist in module catalog

        Args:
            pipeline_state: Pipeline to validate

        Returns:
            List of validation errors
        """
        # TODO: Implement module reference validation
        pass

    def _validate_connections(self, pipeline_state: PipelineState) -> List[Dict[str, Any]]:
        """
        TODO: Validate connection integrity and type compatibility

        Args:
            pipeline_state: Pipeline to validate

        Returns:
            List of validation errors
        """
        # TODO: Implement connection validation
        pass

    def _validate_dag(self, pipeline_state: PipelineState) -> List[Dict[str, Any]]:
        """
        TODO: Validate that pipeline forms a valid DAG (no cycles)

        Args:
            pipeline_state: Pipeline to validate

        Returns:
            List of validation errors
        """
        # TODO: Implement DAG validation and cycle detection
        pass

    def _calculate_plan_checksum(self, pipeline_state: PipelineState) -> str:
        """
        TODO: Calculate deterministic checksum for pipeline plan

        Args:
            pipeline_state: Pipeline state to checksum

        Returns:
            SHA-256 checksum string
        """
        # TODO: Implement checksum calculation
        pass