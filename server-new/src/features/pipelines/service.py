"""
Pipeline Service
Handles pipeline definition, compilation, validation, and lifecycle management
"""
import logging
import hashlib
import json
from typing import List, Dict, Set, Optional, Any
from datetime import datetime, timezone
from dataclasses import asdict, replace

from shared.database import DatabaseConnectionManager
from shared.database.repositories import (
    PipelineDefinitionRepository,
    PipelineCompiledPlanRepository,
    PipelineDefinitionStepRepository,
    ModuleCatalogRepository,
)
from shared.types.pipelines import (
    PipelineState,
    NodeInstance,
    ModuleInstance,
    NodeConnection,
    EntryPoint,
    PipelineIndices,
    PinInfo,
)
from shared.types.pipeline_definition import (
    PipelineDefinitionFull,
    PipelineDefinitionSummary,
    PipelineDefinitionCreate,
)
from shared.types.pipeline_compiled_plan import PipelineCompiledPlanCreate
from shared.types.pipeline_definition_step import PipelineDefinitionStepCreate
from shared.exceptions import ServiceError, ValidationError, ObjectNotFoundError, PipelineValidationError
from .utils.validation import PipelineValidator
from .utils.compilation import PipelineCompiler

logger = logging.getLogger(__name__)


class PipelineService:
    """
    Pipeline management service.

    Handles pipeline definition CRUD, compilation, and validation.
    Implements checksum-based deduplication to avoid redundant compilation.

    Compilation Flow:
    1. Validate pipeline structure (module refs, connections, types)
    2. Prune dead branches (unreachable nodes)
    3. Calculate checksum of pruned pipeline
    4. Check for existing compiled plan with same checksum (dedup)
    5. If not exists: Compile (topological sort) and persist
    6. Link pipeline definition to compiled plan
    """

    connection_manager: DatabaseConnectionManager
    definition_repository: PipelineDefinitionRepository
    compiled_plan_repository: PipelineCompiledPlanRepository
    step_repository: PipelineDefinitionStepRepository
    module_catalog_repository: ModuleCatalogRepository

    def __init__(self, connection_manager: DatabaseConnectionManager) -> None:
        """
        Initialize pipeline service

        Args:
            connection_manager: Database connection manager
        """
        self.connection_manager = connection_manager
        self.definition_repository = PipelineDefinitionRepository(connection_manager=connection_manager)
        self.compiled_plan_repository = PipelineCompiledPlanRepository(connection_manager=connection_manager)
        self.step_repository = PipelineDefinitionStepRepository(connection_manager=connection_manager)
        self.module_catalog_repository = ModuleCatalogRepository(connection_manager=connection_manager)

    # ==================== Internal Helper Methods ====================

    def _build_indices(self, pipeline_state: PipelineState) -> PipelineIndices:
        """
        Build lookup indices for fast pipeline traversal.

        Creates:
        - pin_by_id: Maps node_id -> PinInfo (type, direction, name, module)
        - module_by_id: Maps module_instance_id -> ModuleInstance
        - input_to_upstream: Maps input pin node_id -> upstream output pin node_id

        Args:
            pipeline_state: Pipeline structure

        Returns:
            PipelineIndices with lookup structures
        """
        pin_by_id: Dict[str, PinInfo] = {}
        module_by_id: Dict[str, ModuleInstance] = {}
        input_to_upstream: Dict[str, str] = {}

        # Index entry points
        for entry_point in pipeline_state.entry_points:
            pin_by_id[entry_point.node_id] = PinInfo(
                node_id=entry_point.node_id,
                type="any",  # Entry points can connect to any type
                direction="entry",
                name=entry_point.name,
                module_instance_id=None
            )

        # Index modules and their pins
        for module in pipeline_state.modules:
            module_by_id[module.module_instance_id] = module

            # Index input pins
            for input_pin in module.inputs:
                pin_by_id[input_pin.node_id] = PinInfo(
                    node_id=input_pin.node_id,
                    type=input_pin.type,
                    direction="in",
                    name=input_pin.name,
                    module_instance_id=module.module_instance_id
                )

            # Index output pins
            for output_pin in module.outputs:
                pin_by_id[output_pin.node_id] = PinInfo(
                    node_id=output_pin.node_id,
                    type=output_pin.type,
                    direction="out",
                    name=output_pin.name,
                    module_instance_id=module.module_instance_id
                )

        # Build input-to-upstream mapping
        for connection in pipeline_state.connections:
            input_to_upstream[connection.to_node_id] = connection.from_node_id

        return PipelineIndices(
            pin_by_id=pin_by_id,
            module_by_id=module_by_id,
            input_to_upstream=input_to_upstream
        )

    def _validate_pipeline(self, pipeline_state: PipelineState) -> None:
        """
        Validate pipeline structure through multiple stages.

        Uses PipelineValidator to perform comprehensive validation:
        1. Schema validation (node IDs, types, format)
        2. Index building (preprocessing)
        3. Module validation (catalog, groups, type vars, config, actions)
        4. Edge validation (connections, types, cardinality)
        5. Graph validation (cycles, DAG)

        Args:
            pipeline_state: Pipeline to validate

        Raises:
            PipelineValidationError: If validation fails at any stage
        """
        validator = PipelineValidator(module_catalog_repo=self.module_catalog_repository)
        validator.validate(pipeline_state)

    def _check_for_cycles(self, pipeline_state: PipelineState, indices: PipelineIndices) -> None:
        """
        Check for cycles in the pipeline graph using DFS.

        Args:
            pipeline_state: Pipeline to check
            indices: Pre-built indices

        Raises:
            ValidationError: If a cycle is detected
        """
        # Build adjacency list (module -> downstream modules)
        adjacency: Dict[str, Set[str]] = {
            module.module_instance_id: set() for module in pipeline_state.modules
        }

        for connection in pipeline_state.connections:
            source_pin = indices.pin_by_id[connection.from_node_id]
            target_pin = indices.pin_by_id[connection.to_node_id]

            # Skip entry point connections (they're not modules)
            if source_pin.module_instance_id is None:
                continue

            if target_pin.module_instance_id is None:
                continue

            adjacency[source_pin.module_instance_id].add(target_pin.module_instance_id)

        # DFS to detect cycles
        WHITE, GRAY, BLACK = 0, 1, 2
        colors = {module_id: WHITE for module_id in adjacency}

        def dfs(node: str, path: List[str]) -> None:
            colors[node] = GRAY
            path.append(node)

            for neighbor in adjacency[node]:
                if colors[neighbor] == GRAY:
                    # Found a cycle
                    cycle_start = path.index(neighbor)
                    cycle = " -> ".join(path[cycle_start:] + [neighbor])
                    raise ValidationError(f"Cycle detected in pipeline: {cycle}")

                if colors[neighbor] == WHITE:
                    dfs(neighbor, path)

            colors[node] = BLACK
            path.pop()

        for module_id in adjacency:
            if colors[module_id] == WHITE:
                dfs(module_id, [])

    def _prune_dead_branches(self, pipeline_state: PipelineState) -> PipelineState:
        """
        Remove unreachable modules from the pipeline (dead branch pruning).

        A module is reachable if it's an action module OR it has a path to an action module.
        Dead branches are modules that don't contribute to any action execution.

        Algorithm:
        1. Find all action modules (using module catalog)
        2. Work backwards from action inputs to find all upstream modules (BFS)
        3. Filter pipeline to only include reachable modules and their connections

        Args:
            pipeline_state: Original validated pipeline

        Returns:
            New PipelineState with only action-reachable modules

        Note:
            Original pipeline_state is not modified (returns new instance)
        """
        indices = self._build_indices(pipeline_state)

        # Step 1: Find all action modules using module catalog
        action_modules: Set[str] = set()
        for module in pipeline_state.modules:
            # Parse module_ref to get module_id and version
            if ":" not in module.module_ref:
                continue  # Skip malformed refs (should be caught by validation)

            module_id, version = module.module_ref.split(":", 1)

            # Look up module in catalog
            template = self.module_catalog_repository.get_by_module_ref(module_id, version)
            if template and template.module_kind.value == "action":
                action_modules.add(module.module_instance_id)

        logger.debug(f"Found {len(action_modules)} action module(s)")

        # Step 2: BFS backwards from action inputs to find all upstream modules
        reachable_modules: Set[str] = set(action_modules)  # Actions are always reachable
        queue: List[str] = []

        # Start BFS from all action input pins
        for module in pipeline_state.modules:
            if module.module_instance_id in action_modules:
                # Add all input pins to queue
                for input_pin in module.inputs:
                    queue.append(input_pin.node_id)

        visited_pins: Set[str] = set()

        while queue:
            pin_id = queue.pop(0)

            if pin_id in visited_pins:
                continue

            visited_pins.add(pin_id)

            # Get pin info to find its module
            pin_info = indices.pin_by_id.get(pin_id)
            if pin_info and pin_info.module_instance_id:
                reachable_modules.add(pin_info.module_instance_id)

            # Find upstream pin (what feeds into this pin)
            if pin_id in indices.input_to_upstream:
                upstream_pin_id = indices.input_to_upstream[pin_id]
                queue.append(upstream_pin_id)

                # Also add all other output pins from the upstream module
                # (since they're part of the same module execution)
                upstream_pin = indices.pin_by_id.get(upstream_pin_id)
                if upstream_pin and upstream_pin.module_instance_id:
                    upstream_module = indices.module_by_id.get(upstream_pin.module_instance_id)
                    if upstream_module:
                        # Add all inputs of upstream module to continue traversal
                        for input_pin in upstream_module.inputs:
                            queue.append(input_pin.node_id)

        modules_before = len(pipeline_state.modules)
        modules_after = len(reachable_modules)
        modules_pruned = modules_before - modules_after

        if modules_pruned > 0:
            logger.info(f"Pruned {modules_pruned} dead branch module(s) ({modules_after}/{modules_before} remain)")

        # Step 3: Build set of reachable pin node_ids
        reachable_pins: Set[str] = set()

        for module in pipeline_state.modules:
            if module.module_instance_id in reachable_modules:
                # Add all pins from this reachable module
                for pin in module.inputs:
                    reachable_pins.add(pin.node_id)
                for pin in module.outputs:
                    reachable_pins.add(pin.node_id)

        # Also add entry point node_ids (they can connect to reachable modules)
        for entry_point in pipeline_state.entry_points:
            reachable_pins.add(entry_point.node_id)

        # Step 4: Filter modules to reachable only
        pruned_modules = [
            module
            for module in pipeline_state.modules
            if module.module_instance_id in reachable_modules
        ]

        # Step 5: Filter connections to those between reachable pins
        pruned_connections = [
            conn
            for conn in pipeline_state.connections
            if conn.from_node_id in reachable_pins and conn.to_node_id in reachable_pins
        ]

        # Step 6: Keep all entry points (they're pipeline inputs, always needed)
        # Note: Could prune unused entry points, but keeping them preserves interface
        pruned_entry_points = pipeline_state.entry_points

        # Return new PipelineState with pruned data
        return PipelineState(
            entry_points=pruned_entry_points,
            modules=pruned_modules,
            connections=pruned_connections,
        )

    def _calculate_checksum(self, pruned_pipeline: PipelineState) -> str:
        """
        Calculate SHA-256 checksum of pruned pipeline for deduplication.

        The checksum is calculated from a deterministic JSON representation
        of the pipeline structure (excluding visual state and IDs that don't
        affect execution semantics).

        Args:
            pruned_pipeline: Pruned pipeline state

        Returns:
            SHA-256 hex digest
        """
        # Convert to dict (dataclass asdict creates nested dicts)
        pipeline_dict = asdict(pruned_pipeline)

        # Sort all lists to ensure deterministic ordering
        # (order doesn't matter for semantic equivalence)
        pipeline_dict["entry_points"] = sorted(
            pipeline_dict["entry_points"],
            key=lambda ep: ep["node_id"]
        )
        pipeline_dict["modules"] = sorted(
            pipeline_dict["modules"],
            key=lambda mod: mod["module_instance_id"]
        )
        pipeline_dict["connections"] = sorted(
            pipeline_dict["connections"],
            key=lambda conn: (conn["from_node_id"], conn["to_node_id"])
        )

        # Sort module inputs/outputs
        for module in pipeline_dict["modules"]:
            module["inputs"] = sorted(module["inputs"], key=lambda pin: pin["node_id"])
            module["outputs"] = sorted(module["outputs"], key=lambda pin: pin["node_id"])

        # Create deterministic JSON string
        json_str = json.dumps(pipeline_dict, sort_keys=True, separators=(',', ':'))

        # Calculate SHA-256
        return hashlib.sha256(json_str.encode('utf-8')).hexdigest()

    def _compile_pipeline(self, pruned_pipeline: PipelineState) -> List[PipelineDefinitionStepCreate]:
        """
        Compile pipeline into ordered execution steps via layer-based topological sort.

        Uses PipelineCompiler to generate steps with proper layer numbering for
        parallel execution in Dask.

        Args:
            pruned_pipeline: Validated and pruned pipeline

        Returns:
            List of steps ordered by execution layer

        Raises:
            ServiceError: If compilation fails
        """
        try:
            # Build indices for compilation
            indices = self._build_indices(pruned_pipeline)

            # Compile using layer-based topological sort
            steps = PipelineCompiler.compile(pruned_pipeline, indices)

            logger.info(
                f"Compiled {len(steps)} steps across "
                f"{max((s.step_number for s in steps), default=-1) + 1} layers"
            )

            return steps

        except Exception as e:
            logger.error(f"Pipeline compilation failed: {e}", exc_info=True)
            raise ServiceError(f"Failed to compile pipeline: {e}") from e

    def get_module_metadata(self, module_ref: str) -> Any:
        """
        Fetch module metadata from module catalog.

        TODO: Implement once module catalog exists.
        This will be used for validation (checking module refs exist)
        and compilation (getting module_kind).

        Args:
            module_ref: Module reference (e.g., "text_cleaner:1.0.0")

        Returns:
            Module metadata (structure TBD)

        Raises:
            ObjectNotFoundError: If module not found in catalog
        """
        logger.warning(f"get_module_metadata called but not implemented: {module_ref}")
        raise NotImplementedError("Module catalog not yet implemented")

    # ==================== Public API Methods ====================

    def create_pipeline_definition(
        self,
        create_data: PipelineDefinitionCreate
    ) -> PipelineDefinitionFull:
        """
        Create new pipeline definition with compilation.

        Flow (ATOMIC):
        1. Validate pipeline structure (outside transaction)
        2. Prune dead branches (outside transaction)
        3. Calculate checksum (outside transaction)
        4. Compile to steps (outside transaction)
        5. ATOMIC TRANSACTION:
           a. Check for existing compiled plan (dedup)
           b. If not exists: Create compiled plan + steps
           c. Create pipeline definition
           d. Link pipeline definition to compiled plan
        6. All database operations succeed or fail together

        Args:
            create_data: Pipeline definition creation data

        Returns:
            Created pipeline definition with full details

        Raises:
            ValidationError: If pipeline validation fails
            ServiceError: If compilation or persistence fails
        """
        try:
            # Steps 1-3: Validation, pruning, checksum (read-only, outside transaction)
            logger.info("Validating pipeline structure")
            self._validate_pipeline(create_data.pipeline_state)

            logger.info("Pruning dead branches")
            pruned_pipeline = self._prune_dead_branches(create_data.pipeline_state)

            checksum = self._calculate_checksum(pruned_pipeline)
            logger.info(f"Pipeline checksum: {checksum}")

            # Step 4: Compile to steps (computation, outside transaction)
            logger.info("Compiling pipeline to execution steps")
            steps = self._compile_pipeline(pruned_pipeline)

            # Step 5: ATOMIC TRANSACTION - All database operations together
            with self.connection_manager.unit_of_work() as uow:
                # Check for existing compiled plan (deduplication)
                existing_plan = self.compiled_plan_repository.get_by_checksum(checksum)

                compiled_plan_id: int

                if existing_plan:
                    logger.info(f"Found existing compiled plan {existing_plan.id} with matching checksum")
                    compiled_plan_id = existing_plan.id
                else:
                    # Create new compiled plan
                    compiled_plan = uow.pipeline_compiled_plans.create(
                        PipelineCompiledPlanCreate(
                            plan_checksum=checksum,
                            compiled_at=datetime.now(timezone.utc)
                        )
                    )
                    compiled_plan_id = compiled_plan.id
                    logger.info(f"Created compiled plan {compiled_plan_id}")

                    # Update step records with compiled_plan_id
                    steps_with_plan_id = [
                        replace(step, pipeline_compiled_plan_id=compiled_plan_id)
                        for step in steps
                    ]

                    # Bulk create steps
                    uow.pipeline_definition_steps.create_steps(steps_with_plan_id)
                    logger.info(f"Created {len(steps_with_plan_id)} execution steps")

                # Create pipeline definition
                pipeline_def = uow.pipeline_definitions.create(create_data)
                logger.info(f"Created pipeline definition {pipeline_def.id}")

                # Link pipeline definition to compiled plan
                uow.pipeline_definitions.update_compiled_plan_id(
                    pipeline_def.id,
                    compiled_plan_id
                )
                logger.info(f"Linked pipeline {pipeline_def.id} to compiled plan {compiled_plan_id}")

                # Transaction commits here (all or nothing)

            # Fetch and return complete pipeline definition
            result = self.definition_repository.get_by_id(pipeline_def.id)
            if not result:
                raise ServiceError(f"Failed to retrieve created pipeline {pipeline_def.id}")

            logger.info(
                f"Pipeline creation complete: definition {result.id}, "
                f"compiled plan {compiled_plan_id}, "
                f"{len(steps)} steps"
            )
            return result

        except PipelineValidationError:
            # Re-raise pipeline validation errors as-is
            raise
        except Exception as e:
            logger.error(f"Error creating pipeline: {e}", exc_info=True)
            raise ServiceError(f"Failed to create pipeline: {str(e)}")

    def get_pipeline_definition(self, pipeline_id: int) -> PipelineDefinitionFull:
        """
        Get pipeline definition by ID.

        Args:
            pipeline_id: Pipeline definition ID

        Returns:
            Pipeline definition with full details

        Raises:
            ObjectNotFoundError: If pipeline not found
        """
        result = self.definition_repository.get_by_id(pipeline_id)

        if not result:
            raise ObjectNotFoundError(f"Pipeline {pipeline_id} not found")

        return result

    def list_pipeline_definitions(
        self,
        sort_by: str = "created_at",
        sort_order: str = "desc"
    ) -> List[PipelineDefinitionSummary]:
        """
        List all pipeline definitions with lightweight summaries.

        Args:
            sort_by: Field to sort by (created_at, updated_at, id)
            sort_order: Sort order (asc or desc)

        Returns:
            List of pipeline definition summaries
        """
        return self.definition_repository.list_pipelines(
            sort_by=sort_by,
            sort_order=sort_order
        )

    def validate_pipeline(self, pipeline_state: PipelineState) -> Dict[str, Any]:
        """
        Validate pipeline structure without saving.

        Returns structured validation results for API responses.

        Args:
            pipeline_state: Pipeline structure to validate

        Returns:
            Dict with:
                - valid: bool (True if no errors)
                - error: Error dict (code, message, where) if validation failed

        Raises:
            Exception: Any non-validation errors (will result in 500)
        """
        try:
            self._validate_pipeline(pipeline_state)
            return {"valid": True}
        except PipelineValidationError as e:
            # Convert validation exception to API response format (400)
            return {
                "valid": False,
                "error": {
                    "code": e.code,
                    "message": str(e),
                    "where": e.where
                }
            }
        # Note: Other exceptions bubble up and trigger 500 error
