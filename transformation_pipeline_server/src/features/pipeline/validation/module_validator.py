"""
Module Validator
Validates module constraints (§2.5 from spec)
"""

from typing import List, Dict, Set
from shared.types import PipelineState

from shared.database.repositories import ModuleCatalogRepository
from shared.exceptions import PipelineValidationError, PipelineValidationErrorCode

from .index_builder import PipelineIndices


class ModuleValidator:
    """
    Validates module-level constraints:
    - Module exists in catalog
    - Pin group cardinalities match template
    - Type variable unification
    - Config matches Pydantic schema
    """

    def __init__(self, module_catalog_repo: ModuleCatalogRepository):
        """
        Initialize validator with module catalog repository

        Args:
            module_catalog_repo: Repository for fetching module templates
        """
        self.module_catalog_repo = module_catalog_repo

    def validate(
        self, pipeline_state: PipelineState, indices: PipelineIndices
    ) -> List[PipelineValidationError]:
        """
        Validate all module constraints

        Args:
            pipeline_state: Pipeline state to validate
            indices: Pre-built indices for efficient lookups

        Returns:
            List of validation errors (empty if all valid)
        """
        errors = []

        for module in pipeline_state.modules:
            # Parse module_ref (format: "module_id:version")
            if ":" not in module.module_ref:
                # Should be caught by schema validator, but check anyway
                errors.append(
                    PipelineValidationError(
                        code=PipelineValidationErrorCode.INVALID_TYPE,
                        message=f"Invalid module_ref format: '{module.module_ref}' (expected 'id:version')",
                        where={"module_instance_id": module.module_instance_id},
                    )
                )
                continue

            module_id, version = module.module_ref.split(":", 1)

            # Fetch template from catalog
            template = self.module_catalog_repo.get_by_module_ref(module_id, version)

            if not template:
                errors.append(
                    PipelineValidationError(
                        code=PipelineValidationErrorCode.MODULE_NOT_FOUND,
                        message=f"Module '{module_id}:{version}' not found in catalog",
                        where={
                            "module_instance_id": module.module_instance_id,
                            "module_ref": module.module_ref,
                        },
                    )
                )
                continue

            # Validate group cardinalities
            errors.extend(self._validate_group_cardinality(module, template))

            # Validate type variable unification
            errors.extend(self._validate_type_variables(module, template))

            # Validate config against schema
            errors.extend(self._validate_config(module, template))

        return errors

    def _validate_group_cardinality(
        self, module, template
    ) -> List[PipelineValidationError]:
        """
        Validate that pin counts match group cardinality constraints

        Args:
            module: ModuleInstance from pipeline
            template: ModuleCatalog from database

        Returns:
            List of cardinality errors
        """
        errors = []
        io_shape = template.meta.io_shape

        # Validate input groups
        for group_idx, group in enumerate(io_shape.inputs.nodes):
            actual_pins = [p for p in module.inputs if p.group_index == group_idx]
            actual_count = len(actual_pins)

            if actual_count < group.min_count:
                errors.append(
                    PipelineValidationError(
                        code=PipelineValidationErrorCode.GROUP_CARDINALITY,
                        message=f"Input group {group_idx} '{group.label}' in module '{module.module_instance_id}' has {actual_count} pins (minimum: {group.min_count})",
                        where={
                            "module_instance_id": module.module_instance_id,
                            "group_index": group_idx,
                            "group_label": group.label,
                            "actual_count": actual_count,
                            "min_count": group.min_count,
                            "direction": "input",
                        },
                    )
                )

            if group.max_count is not None and actual_count > group.max_count:
                errors.append(
                    PipelineValidationError(
                        code=PipelineValidationErrorCode.GROUP_CARDINALITY,
                        message=f"Input group {group_idx} '{group.label}' in module '{module.module_instance_id}' has {actual_count} pins (maximum: {group.max_count})",
                        where={
                            "module_instance_id": module.module_instance_id,
                            "group_index": group_idx,
                            "group_label": group.label,
                            "actual_count": actual_count,
                            "max_count": group.max_count,
                            "direction": "input",
                        },
                    )
                )

        # Validate output groups
        for group_idx, group in enumerate(io_shape.outputs.nodes):
            actual_pins = [p for p in module.outputs if p.group_index == group_idx]
            actual_count = len(actual_pins)

            if actual_count < group.min_count:
                errors.append(
                    PipelineValidationError(
                        code=PipelineValidationErrorCode.GROUP_CARDINALITY,
                        message=f"Output group {group_idx} '{group.label}' in module '{module.module_instance_id}' has {actual_count} pins (minimum: {group.min_count})",
                        where={
                            "module_instance_id": module.module_instance_id,
                            "group_index": group_idx,
                            "group_label": group.label,
                            "actual_count": actual_count,
                            "min_count": group.min_count,
                            "direction": "output",
                        },
                    )
                )

            if group.max_count is not None and actual_count > group.max_count:
                errors.append(
                    PipelineValidationError(
                        code=PipelineValidationErrorCode.GROUP_CARDINALITY,
                        message=f"Output group {group_idx} '{group.label}' in module '{module.module_instance_id}' has {actual_count} pins (maximum: {group.max_count})",
                        where={
                            "module_instance_id": module.module_instance_id,
                            "group_index": group_idx,
                            "group_label": group.label,
                            "actual_count": actual_count,
                            "max_count": group.max_count,
                            "direction": "output",
                        },
                    )
                )

        return errors

    def _validate_type_variables(
        self, module, template
    ) -> List[PipelineValidationError]:
        """
        Validate type variable unification

        If a module uses type variable T, all pins using T must have the same concrete type

        Args:
            module: ModuleInstance from pipeline
            template: ModuleCatalog from database

        Returns:
            List of type variable errors
        """
        errors = []
        io_shape = template.meta.io_shape

        # Map type variables to actual types used
        type_var_bindings: Dict[str, Set[str]] = {}

        # Check input groups
        for group_idx, group in enumerate(io_shape.inputs.nodes):
            if group.typing.type_var:
                type_var = group.typing.type_var
                actual_pins = [p for p in module.inputs if p.group_index == group_idx]

                for pin in actual_pins:
                    if type_var not in type_var_bindings:
                        type_var_bindings[type_var] = set()
                    type_var_bindings[type_var].add(pin.type)

        # Check output groups
        for group_idx, group in enumerate(io_shape.outputs.nodes):
            if group.typing.type_var:
                type_var = group.typing.type_var
                actual_pins = [p for p in module.outputs if p.group_index == group_idx]

                for pin in actual_pins:
                    if type_var not in type_var_bindings:
                        type_var_bindings[type_var] = set()
                    type_var_bindings[type_var].add(pin.type)

        # Check that each type variable has exactly one concrete type
        for type_var, types in type_var_bindings.items():
            if len(types) > 1:
                errors.append(
                    PipelineValidationError(
                        code=PipelineValidationErrorCode.TYPEVAR_MISMATCH,
                        message=f"Type variable '{type_var}' in module '{module.module_instance_id}' is used with conflicting types: {', '.join(sorted(types))}",
                        where={
                            "module_instance_id": module.module_instance_id,
                            "type_var": type_var,
                            "conflicting_types": list(types),
                        },
                    )
                )

        return errors

    def _validate_config(self, module, template) -> List[PipelineValidationError]:
        """
        Validate module config against Pydantic schema

        Args:
            module: ModuleInstance from pipeline
            template: ModuleCatalog from database

        Returns:
            List of config validation errors
        """
        errors = []

        # Template has config_schema which is a JSON Schema dict
        # We can't directly validate against JSON Schema without extra libraries
        # For now, we'll do basic checks - in production you'd use jsonschema or similar

        # Check if required fields are present (from schema)
        config_schema = template.config_schema
        if "required" in config_schema:
            for required_field in config_schema["required"]:
                if required_field not in module.config:
                    errors.append(
                        PipelineValidationError(
                            code=PipelineValidationErrorCode.INVALID_CONFIG,
                            message=f"Required config field '{required_field}' missing in module '{module.module_instance_id}'",
                            where={
                                "module_instance_id": module.module_instance_id,
                                "missing_field": required_field,
                            },
                        )
                    )

        return errors
