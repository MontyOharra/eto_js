"""
Pipeline Validation Orchestrator
Coordinates all validation stages (§2 from spec)
"""

import networkx as nx

from typing import Optional, Set
from shared.types import PipelineState, PipelineValidationResult, PipelineIndices

from shared.exceptions import PipelineValidationError, PipelineValidationErrorCode
from shared.database.repositories import ModuleCatalogRepository

from validation import (SchemaValidator, IndexBuilder, GraphBuilder, EdgeValidator, ModuleValidator, ReachabilityAnalyzer)

class PipelineValidator:
    """
    Main validation orchestrator (§2 from spec)

    Currently implements:
    - Stage 1: Schema validation (§2.1)
    - Stage 2: Index building (§2.2)
    - Stage 3: Graph validation (cycles) (§2.4)
    - Stage 4: Edge validation (cardinality, types) (§2.3)
    - Stage 5: Module validation (templates, type vars, config) (§2.5)
    - Stage 6: Reachability analysis (action-reachable subgraph) (§2.6)
    """

    def __init__(self, module_catalog_repo: Optional[ModuleCatalogRepository] = None):
        """
        Initialize validator

        Args:
            module_catalog_repo: Repository for fetching module templates (optional for basic validation)
        """
        self.module_catalog_repo = module_catalog_repo
        self.indices: Optional[PipelineIndices] = None
        self.pin_graph: Optional[nx.DiGraph] = None

    def validate(self, pipeline_state: PipelineState) -> PipelineValidationResult:
        """
        Validate pipeline through all stages

        Args:
            pipeline_state: Pipeline state to validate

        Returns:
            ValidationResult with valid flag and any errors found
        """
        errors = []

        # Stage 1: Schema validation (§2.1)
        # Check basic structure, uniqueness, types, format
        schema_errors = SchemaValidator.validate(pipeline_state)
        errors.extend(schema_errors)

        # Early exit if schema errors - prevents cascading errors
        if schema_errors:
            return PipelineValidationResult(valid=False, errors=errors)

        # Stage 2: Build indices (§2.2)
        # Create lookup structures for efficient validation
        self.indices = IndexBuilder.build_indices(pipeline_state)

        # Stage 3: Graph validation - check for cycles (§2.4)
        self.pin_graph = GraphBuilder.build_pin_graph(pipeline_state, self.indices)

        # Check if graph is acyclic (DAG)
        if not nx.is_directed_acyclic_graph(self.pin_graph):
            # Find cycles for error reporting
            cycles = GraphBuilder.find_cycles(self.pin_graph)

            if cycles:
                # Report first cycle found
                cycle = cycles[0]
                cycle_str = " -> ".join(cycle) + f" -> {cycle[0]}"

                errors.append(
                    PipelineValidationError(
                        code=PipelineValidationErrorCode.CYCLE,
                        message=f"Cycle detected in pipeline: {cycle_str}",
                        where={"cycle": cycle, "cycle_length": len(cycle)},
                    )
                )

        # Stage 4: Edge validation - check cardinality and type matching (§2.3)
        edge_errors = EdgeValidator.validate(pipeline_state, self.indices)
        errors.extend(edge_errors)

        # Stage 5: Module validation - check templates, type vars, config (§2.5)
        if self.module_catalog_repo:
            module_validator = ModuleValidator(self.module_catalog_repo)
            module_errors = module_validator.validate(pipeline_state)
            errors.extend(module_errors)

        # Stage 6: Reachability analysis - check for actions and find reachable modules (§2.6)
        reachable_modules, reachability_errors = ReachabilityAnalyzer.analyze(
            pipeline_state, self.indices, self.pin_graph
        )
        errors.extend(reachability_errors)

        # Return result
        return PipelineValidationResult(valid=len(errors) == 0, errors=errors, reachable_modules=reachable_modules)
