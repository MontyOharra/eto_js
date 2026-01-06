"""
Pipeline Validation
Validates pipeline structure through multiple stages
"""
import logging
from typing import Dict, List, Set, Optional
from collections import Counter
from pydantic import ValidationError as PydanticValidationError
from shared.types.pipelines import PipelineState, PipelineIndices, PinInfo, ModuleInstance
from shared.exceptions import (
    SchemaValidationError,
    ModuleValidationError,
    EdgeValidationError,
    GraphValidationError,
)
from features.modules.registry import ModuleRegistry

logger = logging.getLogger(__name__)

# Allowed types for module pins
ALLOWED_PIN_TYPES = {"str", "int", "float", "bool", "datetime", "list[str]", "dim", "list[dim]"}


class PipelineValidator:
    """
    Pipeline validation orchestrator.

    Validates pipelines through 5 stages:
    1. Schema validation (node IDs, types, format)
    2. Index building (preprocessing)
    3. Module validation (catalog, groups, type vars, config, outputs)
    4. Edge validation (connections, types, cardinality)
    5. Graph validation (cycles, DAG)

    Fails immediately on first error encountered.
    """

    def __init__(self, module_catalog_repo=None, module_registry=None, services=None):
        """
        Initialize validator

        Args:
            module_catalog_repo: Optional repository for module catalog lookups
            module_registry: Optional module registry (defaults to singleton)
            services: Optional services container for database access during validation
        """
        self.module_catalog_repo = module_catalog_repo
        # Use provided registry or fall back to singleton
        self.module_registry = module_registry if module_registry is not None else ModuleRegistry()
        self.services = services

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
        # Check 1: Node ID uniqueness
        self._check_node_id_uniqueness(pipeline_state)

        # Check 2: Pin types
        self._check_pin_types(pipeline_state)

        # Check 3: Module ref format
        self._check_module_refs(pipeline_state)

    def _check_node_id_uniqueness(self, pipeline_state: PipelineState) -> None:
        """
        Check all node IDs are globally unique across entry points, modules, and output channels.
        Fails fast on first duplicate found.

        Raises:
            SchemaValidationError: If duplicate node ID found
        """
        # Collect all node IDs with their sources for error reporting
        node_ids: List[tuple[str, str]] = []

        # Entry points (check output pins)
        for ep in pipeline_state.entry_points:
            for output_pin in ep.outputs:
                node_ids.append((output_pin.node_id, f"entry point '{ep.name}' output '{output_pin.name}'"))

        # Module pins
        for module in pipeline_state.modules:
            for pin in module.inputs:
                node_ids.append(
                    (pin.node_id, f"input pin '{pin.name}' in module '{module.module_instance_id}'")
                )
            for pin in module.outputs:
                node_ids.append(
                    (pin.node_id, f"output pin '{pin.name}' in module '{module.module_instance_id}'")
                )

        # Output channel pins
        for oc in pipeline_state.output_channels:
            for pin in oc.inputs:
                node_ids.append(
                    (pin.node_id, f"input pin '{pin.name}' in output channel '{oc.output_channel_instance_id}'")
                )

        # Find duplicates (fail fast on first duplicate)
        node_id_counts = Counter([node_id for node_id, _ in node_ids])
        for node_id, count in node_id_counts.items():
            if count > 1:
                # Find all sources of this duplicate
                sources = [source for nid, source in node_ids if nid == node_id]
                raise SchemaValidationError(
                    message=f"Node ID '{node_id}' is used {count} times: {', '.join(sources)}",
                    code="duplicate_node_id",
                    where={"node_id": node_id}
                )

    def _check_pin_types(self, pipeline_state: PipelineState) -> None:
        """
        Check all module pin types are in the allowed set.
        Fails fast on first invalid type.

        Raises:
            SchemaValidationError: If invalid pin type found
        """
        for module in pipeline_state.modules:
            # Check input pins
            for pin in module.inputs:
                if pin.type not in ALLOWED_PIN_TYPES:
                    raise SchemaValidationError(
                        message=f"Invalid type '{pin.type}' for input pin '{pin.name}' in module '{module.module_instance_id}'. Allowed types: {', '.join(sorted(ALLOWED_PIN_TYPES))}",
                        code="invalid_pin_type",
                        where={
                            "module_instance_id": module.module_instance_id,
                            "node_id": pin.node_id,
                            "pin_name": pin.name,
                        }
                    )

            # Check output pins
            for pin in module.outputs:
                if pin.type not in ALLOWED_PIN_TYPES:
                    raise SchemaValidationError(
                        message=f"Invalid type '{pin.type}' for output pin '{pin.name}' in module '{module.module_instance_id}'. Allowed types: {', '.join(sorted(ALLOWED_PIN_TYPES))}",
                        code="invalid_pin_type",
                        where={
                            "module_instance_id": module.module_instance_id,
                            "node_id": pin.node_id,
                            "pin_name": pin.name,
                        }
                    )

    def _check_module_refs(self, pipeline_state: PipelineState) -> None:
        """
        Check module_ref format is valid (should contain ':' for "module_id:version").
        Fails fast on first malformed ref.

        Raises:
            SchemaValidationError: If malformed module ref found
        """
        for module in pipeline_state.modules:
            if ":" not in module.module_ref:
                raise SchemaValidationError(
                    message=f"Module ref '{module.module_ref}' in module '{module.module_instance_id}' is malformed. Expected format: 'module_id:version'",
                    code="malformed_module_ref",
                    where={"module_instance_id": module.module_instance_id}
                )

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
        pin_by_id: Dict[str, PinInfo] = {}
        module_by_id: Dict[str, ModuleInstance] = {}
        input_to_upstream: Dict[str, str] = {}

        # Index entry points (index their output pins)
        for entry in pipeline_state.entry_points:
            for output_pin in entry.outputs:
                pin_by_id[output_pin.node_id] = PinInfo(
                    node_id=output_pin.node_id,
                    type=output_pin.type,
                    direction="entry",
                    name=output_pin.name,
                    module_instance_id=None  # Entry points don't have module IDs
                )

        # Index modules and their pins
        for module in pipeline_state.modules:
            # Index module
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

        # Index output channels and their input pins
        for output_channel in pipeline_state.output_channels:
            for input_pin in output_channel.inputs:
                pin_by_id[input_pin.node_id] = PinInfo(
                    node_id=input_pin.node_id,
                    type=input_pin.type,
                    direction="output_channel",
                    name=input_pin.name,
                    module_instance_id=None,
                    output_channel_instance_id=output_channel.output_channel_instance_id
                )

        # Index connections (input pin -> upstream output pin)
        for connection in pipeline_state.connections:
            input_to_upstream[connection.to_node_id] = connection.from_node_id

        return PipelineIndices(
            pin_by_id=pin_by_id,
            module_by_id=module_by_id,
            input_to_upstream=input_to_upstream
        )

    def _validate_modules(self, pipeline_state: PipelineState, indices: PipelineIndices) -> None:
        """
        Stage 3: Validate modules (catalog, groups, type vars, config, output channels)

        Checks:
        - Module exists in catalog
        - Group cardinality constraints (min_count, max_count)
        - Type variable unification (all uses of "T" have same type)
        - Config has required fields
        - Exactly one required output channel present

        Args:
            pipeline_state: Pipeline to validate
            indices: Pre-built indices

        Raises:
            ModuleValidationError: If module validation fails
        """
        logger.info(f"[VALIDATION DEBUG] _validate_modules called with {len(pipeline_state.modules)} modules")
        logger.info(f"[VALIDATION DEBUG] module_catalog_repo is None: {self.module_catalog_repo is None}")

        # Check 1: Exactly one required output channel must be present
        self._check_output_channels(pipeline_state)

        # Skip module catalog validation if no repository provided
        if not self.module_catalog_repo:
            logger.warning("[VALIDATION] Skipping module validation - no catalog repository provided!")
            return

        for module in pipeline_state.modules:
            logger.info(f"[VALIDATION DEBUG] Validating module {module.module_instance_id} ({module.module_ref})")

            # Parse module_ref (format: "module_id:version")
            module_id, version = self._parse_module_ref(module.module_ref)
            logger.info(f"[VALIDATION DEBUG] Parsed: module_id={module_id}, version={version}")

            # Lookup module in catalog
            template = self.module_catalog_repo.get_by_identifier_version(module_id, version)
            logger.info(f"[VALIDATION DEBUG] Template found: {template is not None}")

            if not template:
                raise ModuleValidationError(
                    message=f"Module '{module_id}:{version}' not found in catalog",
                    code="module_not_found",
                    where={
                        "module_instance_id": module.module_instance_id,
                        "module_ref": module.module_ref,
                    }
                )

            # Validate group cardinalities
            logger.info(f"[VALIDATION DEBUG] Checking group cardinality...")
            self._check_group_cardinality(module, template)

            # Validate type variable unification
            logger.info(f"[VALIDATION DEBUG] Checking type variables...")
            self._check_type_variables(module, template)

            # Validate config schema
            logger.info(f"[VALIDATION DEBUG] Checking config...")
            self._check_config(module, template)

    def _check_output_channels(self, pipeline_state: PipelineState) -> None:
        """
        Check that pipeline contains at least one HAWB identifier output channel.
        Either 'hawb' (single) or 'hawb_list' (multiple) must be present.
        Fails fast if validation fails.

        Args:
            pipeline_state: Pipeline to validate

        Raises:
            ModuleValidationError: If HAWB output channel validation fails
        """
        # HAWB identifier channels - at least one must be present
        hawb_channels = {"hawb", "hawb_list"}

        # Find placed HAWB channels
        placed_hawb = [
            oc.channel_type for oc in pipeline_state.output_channels
            if oc.channel_type in hawb_channels
        ]

        if len(placed_hawb) == 0:
            raise ModuleValidationError(
                message="Pipeline must contain at least one HAWB output channel (hawb or hawb_list).",
                code="missing_hawb_output_channel",
                where={
                    "placed_hawb": placed_hawb,
                    "hawb_options": list(hawb_channels)
                }
            )

    def _parse_module_ref(self, module_ref: str) -> tuple[str, str]:
        """
        Parse module_ref into (module_id, version).
        Assumes format "module_id:version" (already validated in schema stage).

        Args:
            module_ref: Module reference string

        Returns:
            Tuple of (module_id, version)
        """
        parts = module_ref.split(":", 1)
        return parts[0], parts[1]

    def _check_group_cardinality(self, module, template) -> None:
        """
        Validate that pin counts match group cardinality constraints.
        Fails fast on first violation.

        Args:
            module: ModuleInstance from pipeline
            template: ModuleCatalog from database

        Raises:
            ModuleValidationError: If cardinality constraint violated
        """
        io_shape = template.meta.io_shape

        # Validate input groups
        for group_idx, group in enumerate(io_shape.inputs.nodes):
            actual_pins = [p for p in module.inputs if p.group_index == group_idx]
            actual_count = len(actual_pins)

            if actual_count < group.min_count:
                raise ModuleValidationError(
                    message=f"Input group {group_idx} '{group.label}' in module '{module.module_instance_id}' has {actual_count} pin(s) (minimum: {group.min_count})",
                    code="group_cardinality_violation",
                    where={
                        "module_instance_id": module.module_instance_id,
                        "group_index": group_idx,
                        "group_label": group.label,
                        "actual_count": actual_count,
                        "min_count": group.min_count,
                        "direction": "input",
                    }
                )

            if group.max_count is not None and actual_count > group.max_count:
                raise ModuleValidationError(
                    message=f"Input group {group_idx} '{group.label}' in module '{module.module_instance_id}' has {actual_count} pin(s) (maximum: {group.max_count})",
                    code="group_cardinality_violation",
                    where={
                        "module_instance_id": module.module_instance_id,
                        "group_index": group_idx,
                        "group_label": group.label,
                        "actual_count": actual_count,
                        "max_count": group.max_count,
                        "direction": "input",
                    }
                )

        # Validate output groups
        for group_idx, group in enumerate(io_shape.outputs.nodes):
            actual_pins = [p for p in module.outputs if p.group_index == group_idx]
            actual_count = len(actual_pins)

            if actual_count < group.min_count:
                raise ModuleValidationError(
                    message=f"Output group {group_idx} '{group.label}' in module '{module.module_instance_id}' has {actual_count} pin(s) (minimum: {group.min_count})",
                    code="group_cardinality_violation",
                    where={
                        "module_instance_id": module.module_instance_id,
                        "group_index": group_idx,
                        "group_label": group.label,
                        "actual_count": actual_count,
                        "min_count": group.min_count,
                        "direction": "output",
                    }
                )

            if group.max_count is not None and actual_count > group.max_count:
                raise ModuleValidationError(
                    message=f"Output group {group_idx} '{group.label}' in module '{module.module_instance_id}' has {actual_count} pin(s) (maximum: {group.max_count})",
                    code="group_cardinality_violation",
                    where={
                        "module_instance_id": module.module_instance_id,
                        "group_index": group_idx,
                        "group_label": group.label,
                        "actual_count": actual_count,
                        "max_count": group.max_count,
                        "direction": "output",
                    }
                )

    def _check_type_variables(self, module, template) -> None:
        """
        Validate type variable unification.
        If a module uses type variable T, all pins using T must have the same concrete type.
        Fails fast on first conflict.

        Args:
            module: ModuleInstance from pipeline
            template: ModuleCatalog from database

        Raises:
            ModuleValidationError: If type variable has conflicting types
        """
        io_shape = template.meta.io_shape
        type_var_bindings: Dict[str, Set[str]] = {}

        # Collect type variable bindings from input groups
        for group_idx, group in enumerate(io_shape.inputs.nodes):
            if group.typing.type_var:
                type_var = group.typing.type_var
                actual_pins = [p for p in module.inputs if p.group_index == group_idx]

                for pin in actual_pins:
                    if type_var not in type_var_bindings:
                        type_var_bindings[type_var] = set()
                    type_var_bindings[type_var].add(pin.type)

        # Collect type variable bindings from output groups
        for group_idx, group in enumerate(io_shape.outputs.nodes):
            if group.typing.type_var:
                type_var = group.typing.type_var
                actual_pins = [p for p in module.outputs if p.group_index == group_idx]

                for pin in actual_pins:
                    if type_var not in type_var_bindings:
                        type_var_bindings[type_var] = set()
                    type_var_bindings[type_var].add(pin.type)

        # Check that each type variable has exactly one concrete type (fail fast)
        for type_var, types in type_var_bindings.items():
            if len(types) > 1:
                raise ModuleValidationError(
                    message=f"Type variable '{type_var}' in module '{module.module_instance_id}' is used with conflicting types: {', '.join(sorted(types))}",
                    code="type_variable_conflict",
                    where={
                        "module_instance_id": module.module_instance_id,
                        "type_var": type_var,
                        "conflicting_types": list(sorted(types)),
                    }
                )

    def _check_config(self, module, template) -> None:
        """
        Validate module config against schema using Pydantic.
        Checks required fields AND validates types/formats/constraints.
        Fails fast on first validation error.

        Args:
            module: ModuleInstance from pipeline
            template: ModuleCatalog from database

        Raises:
            ModuleValidationError: If config validation fails
        """
        logger.info(f"[VALIDATION DEBUG] _check_config called for module {module.module_instance_id}")
        config_schema = template.config_schema

        # Parse module_ref to get module_id
        module_id, _ = self._parse_module_ref(module.module_ref)
        logger.info(f"[VALIDATION DEBUG] module_id: {module_id}")

        # Get module handler from registry
        handler = self.module_registry.get(module_id)
        logger.info(f"[VALIDATION DEBUG] Handler found in registry: {handler is not None}")
        logger.info(f"[VALIDATION DEBUG] Registry has {len(self.module_registry.get_all())} modules registered")
        logger.info(f"[VALIDATION DEBUG] Registered module IDs: {list(self.module_registry.get_all().keys())}")

        if handler:
            # Validate config using Pydantic (comprehensive validation)
            try:
                ConfigModel = handler.config_class()
                config_instance = ConfigModel(**module.config)
            except PydanticValidationError as e:
                # Take first error (fail fast)
                first_error = e.errors()[0]
                field_path = " -> ".join(str(loc) for loc in first_error["loc"])
                raise ModuleValidationError(
                    message=f"Config field '{field_path}': {first_error['msg']}",
                    code="invalid_config",
                    where={
                        "module_instance_id": module.module_instance_id,
                        "field": field_path,
                        "type": first_error["type"]
                    }
                )

            # Call custom validation if method exists (beyond Pydantic schema validation)
            if hasattr(handler, 'validate_config') and callable(handler.validate_config):
                logger.info(f"[VALIDATION DEBUG] Calling validate_config for module {module.module_instance_id} ({module_id})")
                logger.info(f"[VALIDATION DEBUG] Inputs: {[(p.node_id, p.name) for p in module.inputs]}")
                logger.info(f"[VALIDATION DEBUG] Outputs: {[(p.node_id, p.name) for p in module.outputs]}")

                validation_errors = handler.validate_config(config_instance, module.inputs, module.outputs, services=self.services)
                assert isinstance(validation_errors, list)

                logger.info(f"[VALIDATION DEBUG] Validation errors returned: {validation_errors}")

                if validation_errors:
                    # Fail fast on first custom validation error
                    raise ModuleValidationError(
                        message=f"Config validation failed: {validation_errors[0]}",
                        code="custom_validation_failed",
                        where={
                            "module_instance_id": module.module_instance_id,
                            "errors": validation_errors
                        }
                    )
        else:
            # Fallback: Check required fields only (if handler not in registry)
            if "required" in config_schema:
                for required_field in config_schema["required"]:
                    if required_field not in module.config:
                        raise ModuleValidationError(
                            message=f"Required config field '{required_field}' missing in module '{module.module_instance_id}'",
                            code="missing_required_config",
                            where={
                                "module_instance_id": module.module_instance_id,
                                "missing_field": required_field,
                            }
                        )

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
        # Check 1: Self-loops (check first, simplest)
        self._check_self_loops(pipeline_state)

        # Check 2: Input cardinality (each input has exactly one upstream)
        self._check_input_cardinality(pipeline_state, indices)

        # Check 3: Type matching (connected pins have same type)
        self._check_type_matching(pipeline_state, indices)

    def _check_self_loops(self, pipeline_state: PipelineState) -> None:
        """
        Check that no pin connects to itself.
        Fails fast on first self-loop.

        Args:
            pipeline_state: Pipeline state

        Raises:
            EdgeValidationError: If self-loop detected
        """
        for conn in pipeline_state.connections:
            if conn.from_node_id == conn.to_node_id:
                raise EdgeValidationError(
                    message=f"Self-loop detected: Pin '{conn.from_node_id}' connects to itself",
                    code="self_loop",
                    where={
                        "node_id": conn.from_node_id
                    }
                )

    def _check_input_cardinality(self, pipeline_state: PipelineState, indices: PipelineIndices) -> None:
        """
        Check that each input pin (module inputs and output channel inputs) has exactly one upstream connection.
        Fails fast on first violation.

        Args:
            pipeline_state: Pipeline state
            indices: Pipeline indices

        Raises:
            EdgeValidationError: If input cardinality violated
        """
        # Find all input pins (direction="in" for modules, direction="output_channel" for output channels)
        input_pins = [
            pin_info for pin_info in indices.pin_by_id.values()
            if pin_info.direction in ("in", "output_channel")
        ]

        # Check for missing upstreams
        for pin_info in input_pins:
            if pin_info.node_id not in indices.input_to_upstream:
                # Determine the container (module or output channel)
                if pin_info.direction == "in":
                    container_type = "module"
                    container_id = pin_info.module_instance_id
                else:
                    container_type = "output channel"
                    container_id = pin_info.output_channel_instance_id

                raise EdgeValidationError(
                    message=f"Input pin '{pin_info.name}' in {container_type} '{container_id}' has no upstream connection",
                    code="missing_upstream",
                    where={
                        "node_id": pin_info.node_id,
                        "container_type": container_type,
                        "container_id": container_id,
                        "pin_name": pin_info.name
                    }
                )

        # Check for multiple upstreams (count connections to each input)
        input_connection_counts: Dict[str, int] = {}
        for conn in pipeline_state.connections:
            to_pin = indices.pin_by_id.get(conn.to_node_id)
            if to_pin and to_pin.direction in ("in", "output_channel"):
                input_connection_counts[conn.to_node_id] = input_connection_counts.get(conn.to_node_id, 0) + 1

        for node_id, count in input_connection_counts.items():
            if count > 1:
                pin_info = indices.pin_by_id[node_id]
                # Determine the container (module or output channel)
                if pin_info.direction == "in":
                    container_type = "module"
                    container_id = pin_info.module_instance_id
                else:
                    container_type = "output channel"
                    container_id = pin_info.output_channel_instance_id

                raise EdgeValidationError(
                    message=f"Input pin '{pin_info.name}' in {container_type} '{container_id}' has {count} upstream connections (expected 1)",
                    code="multiple_upstreams",
                    where={
                        "node_id": node_id,
                        "container_type": container_type,
                        "container_id": container_id,
                        "pin_name": pin_info.name,
                        "upstream_count": count
                    }
                )

    def _check_type_matching(self, pipeline_state: PipelineState, indices: PipelineIndices) -> None:
        """
        Check that connected pins have matching types.
        Fails fast on first type mismatch.

        Args:
            pipeline_state: Pipeline state
            indices: Pipeline indices

        Raises:
            EdgeValidationError: If type mismatch detected
        """
        for conn in pipeline_state.connections:
            from_pin = indices.pin_by_id.get(conn.from_node_id)
            to_pin = indices.pin_by_id.get(conn.to_node_id)

            # Pins should exist (validated in schema stage), but check anyway
            if not from_pin or not to_pin:
                continue

            if from_pin.type != to_pin.type:
                raise EdgeValidationError(
                    message=f"Type mismatch: Cannot connect {from_pin.type} output '{from_pin.name}' to {to_pin.type} input '{to_pin.name}'",
                    code="type_mismatch",
                    where={
                        "from_node_id": conn.from_node_id,
                        "to_node_id": conn.to_node_id,
                        "from_type": from_pin.type,
                        "to_type": to_pin.type,
                        "from_pin_name": from_pin.name,
                        "to_pin_name": to_pin.name
                    }
                )

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
        self._check_for_cycles(pipeline_state, indices)

    def _check_for_cycles(self, pipeline_state: PipelineState, indices: PipelineIndices) -> None:
        """
        Check for cycles in the pipeline graph using DFS.
        Pipelines must be Directed Acyclic Graphs (DAGs).
        Fails fast on first cycle detected.

        Args:
            pipeline_state: Pipeline to check
            indices: Pre-built indices

        Raises:
            GraphValidationError: If a cycle is detected
        """
        # Build adjacency list (module -> downstream modules)
        adjacency: Dict[str, Set[str]] = {
            module.module_instance_id: set() for module in pipeline_state.modules
        }

        for connection in pipeline_state.connections:
            source_pin = indices.pin_by_id.get(connection.from_node_id)
            target_pin = indices.pin_by_id.get(connection.to_node_id)

            # Skip if pins not found
            if not source_pin or not target_pin:
                continue

            # Skip entry point connections (they're not modules)
            if source_pin.module_instance_id is None:
                continue

            if target_pin.module_instance_id is None:
                continue

            adjacency[source_pin.module_instance_id].add(target_pin.module_instance_id)

        # DFS to detect cycles using colors
        # WHITE (0) = unvisited, GRAY (1) = visiting, BLACK (2) = visited
        WHITE, GRAY, BLACK = 0, 1, 2
        colors: Dict[str, int] = {module_id: WHITE for module_id in adjacency}

        def dfs(node: str, path: List[str]) -> None:
            """
            Depth-first search to detect cycles.

            Args:
                node: Current module ID
                path: Current path from root to current node

            Raises:
                GraphValidationError: If cycle detected
            """
            colors[node] = GRAY
            path.append(node)

            for neighbor in adjacency[node]:
                if colors[neighbor] == GRAY:
                    # Found a back edge - this is a cycle!
                    cycle_start = path.index(neighbor)
                    cycle_path = path[cycle_start:] + [neighbor]
                    cycle_str = " → ".join(cycle_path)
                    raise GraphValidationError(
                        message=f"Cycle detected in pipeline: {cycle_str}",
                        code="cycle_detected",
                        where={
                            "cycle": cycle_path,
                            "cycle_length": len(cycle_path) - 1
                        }
                    )

                if colors[neighbor] == WHITE:
                    dfs(neighbor, path)

            colors[node] = BLACK
            path.pop()

        # Run DFS from each unvisited node
        for module_id in adjacency:
            if colors[module_id] == WHITE:
                dfs(module_id, [])
