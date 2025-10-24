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
from shared.exceptions.service import ServiceError, ValidationError, ObjectNotFoundError

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
        Validate pipeline structure.

        Checks:
        1. All module references exist in module catalog
        2. All connections reference valid pins
        3. Connection type compatibility (str -> str, etc.)
        4. No duplicate connections
        5. No cycles (DAG requirement)
        6. All module inputs are connected

        Args:
            pipeline_state: Pipeline to validate

        Raises:
            ValidationError: If validation fails
        """
        indices = self._build_indices(pipeline_state)

        # 1. Validate module references exist
        for module in pipeline_state.modules:
            # TODO: Call get_module_metadata() once module catalog exists
            # For now, we'll skip this check
            logger.debug(f"Skipping module catalog check for {module.module_ref}")

        # 2. Validate all connections reference valid pins
        seen_connections: Set[tuple[str, str]] = set()

        for connection in pipeline_state.connections:
            # Check source pin exists
            if connection.from_node_id not in indices.pin_by_id:
                raise ValidationError(
                    f"Connection references non-existent source pin: {connection.from_node_id}"
                )

            # Check target pin exists
            if connection.to_node_id not in indices.pin_by_id:
                raise ValidationError(
                    f"Connection references non-existent target pin: {connection.to_node_id}"
                )

            source_pin = indices.pin_by_id[connection.from_node_id]
            target_pin = indices.pin_by_id[connection.to_node_id]

            # Check direction is valid (entry/out -> in)
            if source_pin.direction not in ["entry", "out"]:
                raise ValidationError(
                    f"Invalid connection source: {connection.from_node_id} is an input pin"
                )

            if target_pin.direction != "in":
                raise ValidationError(
                    f"Invalid connection target: {connection.to_node_id} is not an input pin"
                )

            # 3. Check type compatibility (entry points are "any" and compatible with everything)
            if source_pin.direction != "entry" and source_pin.type != target_pin.type:
                raise ValidationError(
                    f"Type mismatch in connection {connection.from_node_id} -> {connection.to_node_id}: "
                    f"{source_pin.type} != {target_pin.type}"
                )

            # 4. Check for duplicate connections
            conn_tuple = (connection.from_node_id, connection.to_node_id)
            if conn_tuple in seen_connections:
                raise ValidationError(
                    f"Duplicate connection: {connection.from_node_id} -> {connection.to_node_id}"
                )
            seen_connections.add(conn_tuple)

        # 5. Check for cycles using DFS
        self._check_for_cycles(pipeline_state, indices)

        # 6. Check all module inputs are connected
        for module in pipeline_state.modules:
            for input_pin in module.inputs:
                if input_pin.node_id not in indices.input_to_upstream:
                    raise ValidationError(
                        f"Unconnected input pin in module {module.module_instance_id}: "
                        f"{input_pin.name} ({input_pin.node_id})"
                    )

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
        Remove unreachable nodes from the pipeline.

        A node is reachable if:
        - It's an output module (no downstream connections), OR
        - It's an action module (has side effects), OR
        - It has a path to an output/action module

        This ensures we only compile the minimal execution graph.

        Args:
            pipeline_state: Original pipeline

        Returns:
            New PipelineState with dead branches removed
        """
        indices = self._build_indices(pipeline_state)

        # TODO: When module catalog exists, we can identify "action" modules
        # For now, we'll consider all modules that have no downstream connections as "outputs"

        # Build reverse adjacency (module -> upstream modules)
        downstream_modules: Dict[str, Set[str]] = {
            module.module_instance_id: set() for module in pipeline_state.modules
        }

        for connection in pipeline_state.connections:
            source_pin = indices.pin_by_id[connection.from_node_id]
            target_pin = indices.pin_by_id[connection.to_node_id]

            if source_pin.module_instance_id and target_pin.module_instance_id:
                downstream_modules[source_pin.module_instance_id].add(target_pin.module_instance_id)

        # Find output modules (modules with no downstream connections)
        output_modules: Set[str] = {
            module_id for module_id, downstream in downstream_modules.items()
            if len(downstream) == 0
        }

        # BFS backwards from output modules to find all reachable modules
        reachable_modules: Set[str] = set()
        queue = list(output_modules)

        while queue:
            current = queue.pop(0)
            if current in reachable_modules:
                continue

            reachable_modules.add(current)

            # Find all modules that feed into current
            for connection in pipeline_state.connections:
                source_pin = indices.pin_by_id[connection.from_node_id]
                target_pin = indices.pin_by_id[connection.to_node_id]

                if target_pin.module_instance_id == current and source_pin.module_instance_id:
                    queue.append(source_pin.module_instance_id)

        # Filter modules to only include reachable ones
        pruned_modules = [
            module for module in pipeline_state.modules
            if module.module_instance_id in reachable_modules
        ]

        # Filter connections to only include those between reachable modules or from entry points
        reachable_pins: Set[str] = set()

        # Add entry point pins
        for entry_point in pipeline_state.entry_points:
            reachable_pins.add(entry_point.node_id)

        # Add pins from reachable modules
        for module in pruned_modules:
            for input_pin in module.inputs:
                reachable_pins.add(input_pin.node_id)
            for output_pin in module.outputs:
                reachable_pins.add(output_pin.node_id)

        pruned_connections = [
            conn for conn in pipeline_state.connections
            if conn.from_node_id in reachable_pins and conn.to_node_id in reachable_pins
        ]

        # Prune entry points that are no longer connected
        connected_entry_points: Set[str] = set()
        for conn in pruned_connections:
            source_pin = indices.pin_by_id[conn.from_node_id]
            if source_pin.direction == "entry":
                connected_entry_points.add(conn.from_node_id)

        pruned_entry_points = [
            ep for ep in pipeline_state.entry_points
            if ep.node_id in connected_entry_points
        ]

        return PipelineState(
            entry_points=pruned_entry_points,
            modules=pruned_modules,
            connections=pruned_connections
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
        Compile pipeline into ordered execution steps via topological sort.

        Performs Kahn's algorithm to determine execution order, then generates
        step records with all metadata needed for execution.

        Args:
            pruned_pipeline: Validated and pruned pipeline

        Returns:
            List of steps in execution order (topologically sorted)

        Raises:
            ServiceError: If topological sort fails (shouldn't happen after validation)
        """
        indices = self._build_indices(pruned_pipeline)

        # Build adjacency and in-degree count for Kahn's algorithm
        adjacency: Dict[str, Set[str]] = {
            module.module_instance_id: set() for module in pruned_pipeline.modules
        }
        in_degree: Dict[str, int] = {
            module.module_instance_id: 0 for module in pruned_pipeline.modules
        }

        for connection in pruned_pipeline.connections:
            source_pin = indices.pin_by_id[connection.from_node_id]
            target_pin = indices.pin_by_id[connection.to_node_id]

            # Skip connections from entry points (they don't create dependencies)
            if source_pin.module_instance_id is None:
                continue

            if target_pin.module_instance_id is None:
                continue

            # Add edge: source_module -> target_module
            if target_pin.module_instance_id not in adjacency[source_pin.module_instance_id]:
                adjacency[source_pin.module_instance_id].add(target_pin.module_instance_id)
                in_degree[target_pin.module_instance_id] += 1

        # Kahn's algorithm: Start with modules that have no dependencies
        queue = [module_id for module_id, degree in in_degree.items() if degree == 0]
        sorted_order: List[str] = []

        while queue:
            # Process modules with no remaining dependencies
            # Sort to ensure deterministic ordering when multiple modules are ready
            queue.sort()
            current = queue.pop(0)
            sorted_order.append(current)

            # Decrease in-degree for downstream modules
            for neighbor in adjacency[current]:
                in_degree[neighbor] -= 1
                if in_degree[neighbor] == 0:
                    queue.append(neighbor)

        # Sanity check: All modules should be processed
        if len(sorted_order) != len(pruned_pipeline.modules):
            raise ServiceError(
                f"Topological sort failed: expected {len(pruned_pipeline.modules)} modules, "
                f"got {len(sorted_order)}. This indicates a cycle (should have been caught in validation)."
            )

        # Generate step records
        steps: List[PipelineDefinitionStepCreate] = []

        for step_number, module_id in enumerate(sorted_order):
            module = indices.module_by_id[module_id]

            # Build input field mappings (input_pin_id -> upstream_pin_id)
            input_field_mappings: Dict[str, str] = {}
            for input_pin in module.inputs:
                if input_pin.node_id in indices.input_to_upstream:
                    input_field_mappings[input_pin.node_id] = indices.input_to_upstream[input_pin.node_id]

            # Build node metadata (inputs and outputs for this module)
            node_metadata: Dict[str, List[NodeInstance]] = {
                "inputs": list(module.inputs),
                "outputs": list(module.outputs)
            }

            # TODO: Extract module_kind from module catalog once it exists
            # For now, parse from module_ref (e.g., "text_cleaner:1.0.0" -> kind might be in catalog)
            module_kind = "unknown"  # Placeholder

            step = PipelineDefinitionStepCreate(
                pipeline_compiled_plan_id=0,  # Will be set by caller
                module_instance_id=module.module_instance_id,
                module_ref=module.module_ref,
                module_config=module.config,
                input_field_mappings=input_field_mappings,
                node_metadata=node_metadata,
                step_number=step_number
            )
            steps.append(step)

        return steps

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

        except ValidationError:
            # Re-raise validation errors as-is
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
