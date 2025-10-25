"""
Pipeline Validation
Validates pipeline structure through multiple stages
"""
from typing import Dict, List, Set, Optional
from shared.types.pipelines import PipelineState, PipelineIndices, PinInfo
from shared.exceptions import (
    SchemaValidationError,
    ModuleValidationError,
    EdgeValidationError,
    GraphValidationError,
)


class PipelineValidator:
    """
    Pipeline validation orchestrator.

    Validates pipelines through 5 stages:
    1. Schema validation (node IDs, types, format)
    2. Index building (preprocessing)
    3. Module validation (catalog, groups, type vars, config, actions)
    4. Edge validation (connections, types, cardinality)
    5. Graph validation (cycles, DAG)

    Fails immediately on first error encountered.
    """

    def __init__(self, module_catalog_repo=None):
        """
        Initialize validator

        Args:
            module_catalog_repo: Optional repository for module catalog lookups
        """
        self.module_catalog_repo = module_catalog_repo

    def validate(self, pipeline_state: PipelineState) -> None:
        """
        Validate pipeline through all stages.
        Fails fast - stops at first stage with errors.

        Args:
            pipeline_state: Pipeline to validate

        Raises:
            SchemaValidationError: Schema validation failed
            ModuleValidationError: Module validation failed
            EdgeValidationError: Edge validation failed
            GraphValidationError: Graph validation failed (cycles)
        """
        # Stage 1: Schema validation
        self._validate_schema(pipeline_state)

        # Stage 2: Build indices (preprocessing)
        indices = self._build_indices(pipeline_state)

        # Stage 3: Module validation
        self._validate_modules(pipeline_state, indices)

        # Stage 4: Edge validation
        self._validate_edges(pipeline_state, indices)

        # Stage 5: Graph validation (cycles)
        self._validate_graph(pipeline_state, indices)

        # If we reach here, validation passed

    # ==================== Validation Stages ====================

    def _validate_schema(self, pipeline_state: PipelineState) -> None:
        """
        Stage 1: Validate basic schema (node IDs, types, format)

        Checks:
        - All node IDs are globally unique
        - All pin types are in allowed set
        - All module refs have format "id:version"

        Raises:
            SchemaValidationError: If schema validation fails
        """
        # TODO: Implement schema validation
        # For now, validation always passes
        raise SchemaValidationError("test", "Schema validation not implemented")
        pass

    def _build_indices(self, pipeline_state: PipelineState) -> PipelineIndices:
        """
        Stage 2: Build lookup indices for efficient validation

        Creates:
        - pin_by_id: Map of node_id -> PinInfo
        - module_by_id: Map of module_instance_id -> ModuleInstance
        - input_to_upstream: Map of input pin -> upstream output pin

        Returns:
            PipelineIndices with lookup structures
        """
        # TODO: Implement index building
        # For now, return empty indices
        return PipelineIndices(
            pin_by_id={},
            module_by_id={},
            input_to_upstream={}
        )

    def _validate_modules(self, pipeline_state: PipelineState, indices: PipelineIndices) -> None:
        """
        Stage 3: Validate modules (catalog, groups, type vars, config, actions)

        Checks:
        - Module exists in catalog
        - Group cardinality constraints (min_count, max_count)
        - Type variable unification (all uses of "T" have same type)
        - Config has required fields
        - At least one action module present

        Args:
            pipeline_state: Pipeline to validate
            indices: Pre-built indices

        Raises:
            ModuleValidationError: If module validation fails
        """
        # TODO: Implement module validation
        # For now, validation always passes
        pass

    def _validate_edges(self, pipeline_state: PipelineState, indices: PipelineIndices) -> None:
        """
        Stage 4: Validate edges (connections, types, cardinality)

        Checks:
        - Each input pin has exactly one upstream connection
        - Connected pins have matching types
        - No self-loops (pin connecting to itself)

        Args:
            pipeline_state: Pipeline to validate
            indices: Pre-built indices

        Raises:
            EdgeValidationError: If edge validation fails
        """
        # TODO: Implement edge validation
        # For now, validation always passes
        pass

    def _validate_graph(self, pipeline_state: PipelineState, indices: PipelineIndices) -> None:
        """
        Stage 5: Validate graph structure (cycles, DAG)

        Checks:
        - Pipeline is a Directed Acyclic Graph (no cycles)

        Args:
            pipeline_state: Pipeline to validate
            indices: Pre-built indices

        Raises:
            GraphValidationError: If graph has cycles
        """
        # TODO: Implement graph validation
        # For now, validation always passes
        pass
