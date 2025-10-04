"""
Schema Validator
Validates basic schema and presence requirements (§2.1 from spec)
"""
from typing import List, Set, Dict
from collections import Counter
from src.shared.models.pipeline import PipelineState
from .errors import ValidationError, ValidationErrorCode


class SchemaValidator:
    """Validates basic schema and presence requirements (§2.1)"""

    ALLOWED_TYPES = {"str", "int", "float", "bool", "datetime"}

    def validate(self, pipeline_state: PipelineState) -> List[ValidationError]:
        """
        Run all schema validations

        Args:
            pipeline_state: Pipeline state to validate

        Returns:
            List of validation errors (empty if valid)
        """
        errors = []

        errors.extend(self._check_node_id_uniqueness(pipeline_state))
        errors.extend(self._check_pin_types(pipeline_state))
        errors.extend(self._check_module_refs(pipeline_state))

        return errors

    def _check_node_id_uniqueness(self, pipeline_state: PipelineState) -> List[ValidationError]:
        """
        Check all node IDs are globally unique across entry points and all module pins

        Args:
            pipeline_state: Pipeline state to validate

        Returns:
            List of DUPLICATE_NODE_ID errors
        """
        errors = []

        # Collect all node IDs with their sources for error reporting
        node_ids = []

        # Entry points
        for ep in pipeline_state.entry_points:
            node_ids.append((ep.node_id, f"entry point '{ep.name}'"))

        # Module pins
        for module in pipeline_state.modules:
            for pin in module.inputs:
                node_ids.append((pin.node_id, f"input pin in module '{module.module_instance_id}'"))
            for pin in module.outputs:
                node_ids.append((pin.node_id, f"output pin in module '{module.module_instance_id}'"))

        # Find duplicates
        node_id_counts = Counter([node_id for node_id, _ in node_ids])
        duplicates = {node_id: count for node_id, count in node_id_counts.items() if count > 1}

        # Create errors for each duplicate
        for dup_id in duplicates:
            # Find all sources of this duplicate
            sources = [source for node_id, source in node_ids if node_id == dup_id]
            errors.append(ValidationError(
                code=ValidationErrorCode.DUPLICATE_NODE_ID,
                message=f"Node ID '{dup_id}' is used {duplicates[dup_id]} times: {', '.join(sources)}",
                where={"node_id": dup_id}
            ))

        return errors

    def _check_pin_types(self, pipeline_state: PipelineState) -> List[ValidationError]:
        """
        Check all module pin types are in the allowed set

        Args:
            pipeline_state: Pipeline state to validate

        Returns:
            List of INVALID_TYPE errors
        """
        errors = []

        for module in pipeline_state.modules:
            # Check input pins
            for pin in module.inputs:
                if pin.type not in self.ALLOWED_TYPES:
                    errors.append(ValidationError(
                        code=ValidationErrorCode.INVALID_TYPE,
                        message=f"Invalid type '{pin.type}' for input pin '{pin.node_id}' in module '{module.module_instance_id}'. Allowed types: {', '.join(sorted(self.ALLOWED_TYPES))}",
                        where={
                            "module_instance_id": module.module_instance_id,
                            "node_id": pin.node_id
                        }
                    ))

            # Check output pins
            for pin in module.outputs:
                if pin.type not in self.ALLOWED_TYPES:
                    errors.append(ValidationError(
                        code=ValidationErrorCode.INVALID_TYPE,
                        message=f"Invalid type '{pin.type}' for output pin '{pin.node_id}' in module '{module.module_instance_id}'. Allowed types: {', '.join(sorted(self.ALLOWED_TYPES))}",
                        where={
                            "module_instance_id": module.module_instance_id,
                            "node_id": pin.node_id
                        }
                    ))

        return errors

    def _check_module_refs(self, pipeline_state: PipelineState) -> List[ValidationError]:
        """
        Check module_ref format is valid (should contain ':' for "module_id:version")

        Args:
            pipeline_state: Pipeline state to validate

        Returns:
            List of MISSING_FIELD errors for malformed module refs
        """
        errors = []

        for module in pipeline_state.modules:
            if ":" not in module.module_ref:
                errors.append(ValidationError(
                    code=ValidationErrorCode.MISSING_FIELD,
                    message=f"Module ref '{module.module_ref}' in module '{module.module_instance_id}' is malformed. Expected format: 'module_id:version'",
                    where={"module_instance_id": module.module_instance_id}
                ))

        return errors
