/**
 * Type definitions for the Transformation Pipeline system
 */

import type {
  NodeTypeRule,
  NodeGroup,
  IOSideShape,
  IOShape,
  ModuleTemplate,
} from "../modules/types";

// Re-export module catalog types for convenience
export type { NodeTypeRule, NodeGroup, IOSideShape, IOShape, ModuleTemplate };

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
}

/**
 * Module instance structure
 * Represents a module placed in the pipeline
 */
export interface ModuleInstance {
  module_instance_id: string;
  module_ref: string;
  module_kind: string;
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

// Entry point for pipeline (frontend - includes type for UI)
export interface EntryPoint {
  node_id: string;
  name: string;
  type: string;
}

// Backend-compatible types for serialization
export interface InstanceNodePin {
  node_id: string;
  type: string;
  name: string;
  position_index: number;
  group_index: number;
}

export interface BackendEntryPoint {
  node_id: string;
  name: string;
}

// Pipeline state (execution data)
export interface PipelineState {
  entry_points: EntryPoint[];
  modules: ModuleInstance[];
  connections: NodeConnection[];
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

// API response for modules endpoint
export interface ModulesResponse {
  modules: ModuleTemplate[];
  total_count: number;
  stats: {
    total_modules: number;
    transform_modules: number;
    action_modules: number;
    logic_modules: number;
    module_refs: string[];
  };
}

// Type alias for compatibility
export type Connection = NodeConnection;
