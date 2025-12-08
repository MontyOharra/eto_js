/**
 * Type definitions for the Transformation Pipeline system
 */

import type {
  NodeGroup,
} from "../modules/types";

// ============================================================================
// Runtime Types (Module Instances & Pins)
// ============================================================================

/**
 * Runtime instance of a pin in a module instance
 * Created when a module is added to the pipeline
 */
export interface NodePin {
  node_id: string;
  direction: 'in' | 'out';
  type: string;
  name: string;              // user-editable name
  label: string;             // from NodeGroup.label
  position_index: number;    // position within the group
  group_index: number;       // index in meta.io_shape.inputs.nodes or outputs.nodes
  type_var?: string;         // type variable name if applicable
  allowed_types?: string[];  // allowed types for this node (from template)
  readonly?: boolean;        // if true, name cannot be edited (used for entry points)
}

/**
 * Module instance structure
 * Represents a module placed in the pipeline
 */
export interface ModuleInstance {
  module_instance_id: string;
  module_ref: string;
  config: Record<string, any>;
  inputs: NodePin[];         // Flat array, grouped by group_index
  outputs: NodePin[];
}

/**
 * Type variable management for generic modules
 * Tracks type unification across module pins
 */
export interface TypeVariableState {
  assignments: Record<string, string>; // typeVar -> currentType
  affectedNodes: Record<string, string[]>; // typeVar -> nodeIds[]
}

/**
 * Group info for UI rendering
 * Helper type for managing dynamic node groups
 */
export interface GroupInfo {
  groupIndex: number;
  group: NodeGroup;
  currentCount: number;
  canAdd: boolean;
  canRemove: boolean;
}

// Connection between nodes
export interface NodeConnection {
  from_node_id: string;
  to_node_id: string;
}

// Entry point for pipeline - structured like a module with outputs
export interface EntryPoint {
  entry_point_id: string;  // Like module_instance_id (format: E01, E02, etc.)
  name: string;
  outputs: NodePin[];      // Array with single output pin containing the type
}

// Output channel instance - structured like a module with inputs only
export interface OutputChannelInstance {
  output_channel_instance_id: string;  // Format: OC01, OC02, etc.
  channel_type: string;                // e.g., "hawb", "pickup_address"
  inputs: NodePin[];                   // Single input pin
}

// Pipeline state (execution data)
export interface PipelineState {
  entry_points: EntryPoint[];
  modules: ModuleInstance[];
  connections: NodeConnection[];
  output_channels: OutputChannelInstance[];
}

// Visual state (UI positioning) - flat structure with all node positions
export type VisualState = Record<string, { x: number; y: number }>;

// Complete pipeline data (for saving/loading)
export interface PipelineData {
  schema_version?: string;
  name?: string;
  description?: string;
  pipeline_json: PipelineState;
  visual_json: VisualState;
}

// Type alias for compatibility
export type Connection = NodeConnection;
