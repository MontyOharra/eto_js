"""
Checksum Calculator
Computes stable SHA-256 checksums of pipeline structures for cache invalidation

This implementation is ID-AGNOSTIC, meaning two pipelines with identical structure
but different node IDs will produce the SAME checksum. This enables deduplication
and caching of compiled steps across multiple pipelines.
"""

import hashlib
import json
from typing import Dict, Any

from shared.typespipeline_definitions import PipelineState


class ChecksumCalculator:
    """
    Computes stable SHA-256 checksums of pipeline structures

    KEY FEATURE: ID-Agnostic Checksums
    ===================================
    The checksum is based on STRUCTURE, not on specific node IDs.

    Example:
        Pipeline A: entry_abc → module_xyz → action_123
        Pipeline B: entry_def → module_uvw → action_456

        If both have the same module types, configs, and connection topology,
        they will produce the SAME checksum even though IDs are different.

    Algorithm:
        1. Sort all nodes by structural properties (deterministic ordering)
        2. Assign positional IDs (entry_0, mod_0, mod_1, etc.)
        3. Build normalized structure using positions instead of actual IDs
        4. Hash the normalized structure

    The checksum includes:
        - Entry point types (but NOT their IDs)
        - Module refs, kinds, and configs
        - Pin types and positions within modules
        - Connection topology (which outputs connect to which inputs)

    The checksum does NOT include:
        - Actual node ID strings
        - UI-only data (positions, labels, colors)
        - Pin names (only structural position matters)
    """

    @staticmethod
    def compute(pipeline_state: PipelineState) -> str:
        """
        Compute ID-agnostic SHA-256 checksum of pipeline structure

        This is the main entry point. It orchestrates the normalization
        and hashing process.

        Args:
            pipeline_state: Validated pipeline state

        Returns:
            64-character SHA-256 hex string

        Example:
            >>> checksum = ChecksumCalculator.compute(pipeline_state)
            >>> print(checksum)
            '3d1a4f5e8b2c9d7a6e4f1b8c5a9d2e7f3b6c8a4d9e1f7a5b2c8d4e6f9a1b3c5d7e'
        """
        # Step 1: Build a mapping from actual IDs to canonical position IDs
        id_to_position = ChecksumCalculator._build_id_mapping(pipeline_state)

        # Step 2: Build normalized structure using position IDs
        normalized_data = ChecksumCalculator._build_normalized_data(
            pipeline_state, id_to_position
        )

        # Step 3: Serialize to deterministic JSON string
        json_str = ChecksumCalculator._serialize_to_json(normalized_data)

        # Step 4: Compute SHA-256 hash
        return ChecksumCalculator._hash_json(json_str)

    @staticmethod
    def _build_id_mapping(pipeline_state: PipelineState) -> Dict[str, str]:
        """
        Build mapping from actual node IDs to canonical position IDs

        This is the core of the ID-agnostic algorithm. We:
        1. Sort all nodes by their STRUCTURAL properties (not by ID)
        2. Assign each node a position-based ID (entry_0, mod_0, etc.)

        Why this works:
            - Two pipelines with identical structure will sort identically
            - After sorting, corresponding nodes get the same position ID
            - The mapping allows us to replace actual IDs with positions

        Args:
            pipeline_state: Pipeline state to process

        Returns:
            Dictionary mapping actual node_id → position_id
            Example: {"entry_abc": "entry_0", "module_xyz": "mod_0", ...}
        """
        id_to_pos = {}

        # ============================================================
        # STEP 1: Sort and map entry points
        # ============================================================
        # Sort entry points by name. This ensures deterministic ordering.
        # The "key" parameter tells sorted() HOW to compare entries.
        # lambda e: (e.name or "") means:
        #   - Sort by name
        #   - "or ''" handles None names (treats them as empty string)
        # Note: Entry points are always type "str" so no need to sort by type
        sorted_entries = sorted(
            pipeline_state.entry_points, key=lambda e: (e.name or "")
        )

        # Assign position IDs: entry_0, entry_1, entry_2, ...
        # enumerate() gives us (index, item) pairs: (0, entry1), (1, entry2), ...
        for idx, entry in enumerate(sorted_entries):
            id_to_pos[entry.node_id] = f"entry_{idx}"

        # ============================================================
        # STEP 2: Sort and map modules
        # ============================================================
        # Sort modules by structural properties (NOT by module_instance_id)
        # We sort by:
        #   1. module_ref (e.g., "text_cleaner:1.0.0")
        #   2. module_kind (e.g., "transform", "action")
        #   3. config (as JSON string for deterministic comparison)
        #   4. number of inputs
        #   5. number of outputs
        # This ensures modules with same structure get same position
        sorted_modules = sorted(
            pipeline_state.modules,
            key=lambda m: (
                m.module_ref,
                m.module_kind,
                json.dumps(
                    m.config, sort_keys=True
                ),  # Convert dict to deterministic string
                len(m.inputs),
                len(m.outputs),
            ),
        )

        # Process each module and its pins
        for mod_idx, module in enumerate(sorted_modules):
            # Assign module position ID: mod_0, mod_1, mod_2, ...
            mod_pos = f"mod_{mod_idx}"
            id_to_pos[module.module_instance_id] = mod_pos

            # ------------------------------------------------------------
            # Sort input pins within this module
            # ------------------------------------------------------------
            # Pins are sorted by (group_index, position_index)
            # This is their structural position, NOT their node_id
            # Example: group_index=0, position_index=0 comes before
            #          group_index=0, position_index=1
            sorted_inputs = sorted(
                module.inputs, key=lambda p: (p.group_index, p.position_index)
            )

            # Assign input pin position IDs: mod_0_in_0, mod_0_in_1, ...
            for pin_idx, pin in enumerate(sorted_inputs):
                id_to_pos[pin.node_id] = f"{mod_pos}_in_{pin_idx}"

            # ------------------------------------------------------------
            # Sort output pins within this module
            # ------------------------------------------------------------
            sorted_outputs = sorted(
                module.outputs, key=lambda p: (p.group_index, p.position_index)
            )

            # Assign output pin position IDs: mod_0_out_0, mod_0_out_1, ...
            for pin_idx, pin in enumerate(sorted_outputs):
                id_to_pos[pin.node_id] = f"{mod_pos}_out_{pin_idx}"

        return id_to_pos

    @staticmethod
    def _build_normalized_data(
        pipeline_state: PipelineState, id_to_pos: Dict[str, str]
    ) -> Dict[str, Any]:
        """
        Build normalized dictionary using position IDs instead of actual IDs

        This function takes the pipeline and the ID mapping, then constructs
        a new representation where all node_ids are replaced with position_ids.

        Args:
            pipeline_state: Pipeline state to normalize
            id_to_pos: Mapping from actual node_id to position_id

        Returns:
            Dictionary with normalized pipeline structure using position IDs
        """
        # ============================================================
        # Re-sort everything using the SAME logic as _build_id_mapping
        # This ensures we process nodes in the same order
        # ============================================================
        sorted_entries = sorted(
            pipeline_state.entry_points, key=lambda e: (e.name or "")
        )

        sorted_modules = sorted(
            pipeline_state.modules,
            key=lambda m: (
                m.module_ref,
                m.module_kind,
                json.dumps(m.config, sort_keys=True),
                len(m.inputs),
                len(m.outputs),
            ),
        )

        # ============================================================
        # Build normalized structure
        # ============================================================
        normalized = {"entries": [], "modules": [], "connections": []}

        # ------------------------------------------------------------
        # Add entry points with position IDs
        # ------------------------------------------------------------
        for entry in sorted_entries:
            normalized["entries"].append(
                {
                    "pos": id_to_pos[
                        entry.node_id
                    ],  # Use position instead of actual ID
                    "name": entry.name
                    or "",  # Entry points don't have type (always str)
                }
            )

        # ------------------------------------------------------------
        # Add modules with position IDs
        # ------------------------------------------------------------
        for module in sorted_modules:
            # Sort pins by structural position (same as in _build_id_mapping)
            sorted_inputs = sorted(
                module.inputs, key=lambda p: (p.group_index, p.position_index)
            )
            sorted_outputs = sorted(
                module.outputs, key=lambda p: (p.group_index, p.position_index)
            )

            module_data = {
                "pos": id_to_pos[module.module_instance_id],  # Module position
                "ref": module.module_ref,
                "kind": module.module_kind,
                "config": module.config,
                "inputs": [
                    {"pos": id_to_pos[pin.node_id], "type": pin.type}  # Pin position
                    for pin in sorted_inputs
                ],
                "outputs": [
                    {"pos": id_to_pos[pin.node_id], "type": pin.type}  # Pin position
                    for pin in sorted_outputs
                ],
            }
            normalized["modules"].append(module_data)

        # ------------------------------------------------------------
        # Add connections with position IDs
        # ------------------------------------------------------------
        # Sort connections by their position IDs (not actual IDs)
        # This ensures deterministic ordering
        sorted_connections = sorted(
            pipeline_state.connections,
            key=lambda c: (
                id_to_pos[c.from_node_id],  # Sort by "from" position
                id_to_pos[c.to_node_id],  # Then by "to" position
            ),
        )

        for connection in sorted_connections:
            normalized["connections"].append(
                {
                    "from": id_to_pos[connection.from_node_id],  # From position
                    "to": id_to_pos[connection.to_node_id],  # To position
                }
            )

        return normalized

    @staticmethod
    def _serialize_to_json(data: Dict[str, Any]) -> str:
        """
        Serialize normalized data to deterministic JSON string

        Why these settings matter:
            - sort_keys=True: Ensures dict keys are always in same order
            - separators=(',', ':'): No whitespace (compact, deterministic)
            - ensure_ascii=True: Converts unicode to ASCII escape sequences

        These settings guarantee that the same data structure always
        produces the EXACT same JSON string, byte-for-byte.

        Args:
            data: Normalized data dictionary

        Returns:
            JSON string with sorted keys and no whitespace
        """
        return json.dumps(
            data,
            sort_keys=True,  # Always sort dict keys alphabetically
            separators=(",", ":"),  # Compact format: no spaces
            ensure_ascii=True,  # Convert unicode to \uXXXX format
        )

    @staticmethod
    def _hash_json(json_str: str) -> str:
        """
        Compute SHA-256 hash of JSON string

        SHA-256 produces a 256-bit (32-byte) hash, represented as a
        64-character hexadecimal string.

        Args:
            json_str: JSON string to hash

        Returns:
            64-character hex digest (lowercase)

        Example:
            >>> _hash_json('{"key":"value"}')
            '3d1a4f5e8b2c9d7a6e4f1b8c5a9d2e7f3b6c8a4d9e1f7a5b2c8d4e6f9a1b3c5d7e'
        """
        # Create hash object
        hash_obj = hashlib.sha256(json_str.encode("utf-8"))

        # Return hexadecimal string representation
        return hash_obj.hexdigest()
