"""
Edge Validator
Validates connections between pins (§2.3 from spec)
"""
from typing import List
from src.shared.models.pipeline import PipelineState
from .errors import ValidationError, ValidationErrorCode
from .index_builder import PipelineIndices


class EdgeValidator:
    """
    Validates edge constraints:
    - Each input pin has exactly one upstream connection
    - Connected pins have matching types
    - No self-loops
    """

    @staticmethod
    def validate(pipeline_state: PipelineState, indices: PipelineIndices) -> List[ValidationError]:
        """
        Validate all edge constraints

        Args:
            pipeline_state: Pipeline state to validate
            indices: Pre-built indices for efficient lookups

        Returns:
            List of validation errors (empty if all valid)
        """
        errors = []

        # Check input cardinality and type matching
        errors.extend(EdgeValidator._check_input_cardinality(pipeline_state, indices))
        errors.extend(EdgeValidator._check_type_matching(pipeline_state, indices))
        errors.extend(EdgeValidator._check_self_loops(pipeline_state))

        return errors

    @staticmethod
    def _check_input_cardinality(pipeline_state: PipelineState, indices: PipelineIndices) -> List[ValidationError]:
        """
        Check that each input pin has exactly one upstream connection

        Args:
            pipeline_state: Pipeline state
            indices: Pipeline indices

        Returns:
            List of cardinality errors
        """
        errors = []

        # Find all input pins (direction="in")
        input_pins = [
            pin_info for pin_info in indices.pin_by_id.values()
            if pin_info.direction == "in"
        ]

        for pin_info in input_pins:
            upstream_count = 1 if pin_info.node_id in indices.input_to_upstream else 0

            if upstream_count == 0:
                # Missing upstream connection
                errors.append(ValidationError(
                    code=ValidationErrorCode.MISSING_UPSTREAM,
                    message=f"Input pin '{pin_info.name}' in module '{pin_info.module_instance_id}' has no upstream connection",
                    where={
                        "node_id": pin_info.node_id,
                        "module_instance_id": pin_info.module_instance_id,
                        "pin_name": pin_info.name
                    }
                ))

        # Check for multiple upstreams (shouldn't happen with our schema, but validate anyway)
        # Count connections to each input
        input_connection_counts = {}
        for conn in pipeline_state.connections:
            to_pin = indices.pin_by_id.get(conn.to_node_id)
            if to_pin and to_pin.direction == "in":
                input_connection_counts[conn.to_node_id] = input_connection_counts.get(conn.to_node_id, 0) + 1

        for node_id, count in input_connection_counts.items():
            if count > 1:
                pin_info = indices.pin_by_id[node_id]
                errors.append(ValidationError(
                    code=ValidationErrorCode.MULTIPLE_UPSTREAMS,
                    message=f"Input pin '{pin_info.name}' in module '{pin_info.module_instance_id}' has {count} upstream connections (expected 1)",
                    where={
                        "node_id": node_id,
                        "module_instance_id": pin_info.module_instance_id,
                        "pin_name": pin_info.name,
                        "upstream_count": count
                    }
                ))

        return errors

    @staticmethod
    def _check_type_matching(pipeline_state: PipelineState, indices: PipelineIndices) -> List[ValidationError]:
        """
        Check that connected pins have matching types

        Args:
            pipeline_state: Pipeline state
            indices: Pipeline indices

        Returns:
            List of type mismatch errors
        """
        errors = []

        for conn in pipeline_state.connections:
            from_pin = indices.pin_by_id.get(conn.from_node_id)
            to_pin = indices.pin_by_id.get(conn.to_node_id)

            if not from_pin or not to_pin:
                # Pin not found - should be caught by schema validation
                continue

            if from_pin.type != to_pin.type:
                errors.append(ValidationError(
                    code=ValidationErrorCode.EDGE_TYPE_MISMATCH,
                    message=f"Type mismatch: Cannot connect {from_pin.type} output '{from_pin.name}' to {to_pin.type} input '{to_pin.name}'",
                    where={
                        "from_node_id": conn.from_node_id,
                        "to_node_id": conn.to_node_id,
                        "from_type": from_pin.type,
                        "to_type": to_pin.type,
                        "from_pin_name": from_pin.name,
                        "to_pin_name": to_pin.name
                    }
                ))

        return errors

    @staticmethod
    def _check_self_loops(pipeline_state: PipelineState) -> List[ValidationError]:
        """
        Check that no pin connects to itself

        Args:
            pipeline_state: Pipeline state

        Returns:
            List of self-loop errors
        """
        errors = []

        for conn in pipeline_state.connections:
            if conn.from_node_id == conn.to_node_id:
                errors.append(ValidationError(
                    code=ValidationErrorCode.SELF_LOOP,
                    message=f"Self-loop detected: Pin '{conn.from_node_id}' connects to itself",
                    where={
                        "node_id": conn.from_node_id
                    }
                ))

        return errors
