/**
 * Module type system with unified NodeGroup structure
 * Matches backend contracts.py structure
 */

// Node type system
export interface NodeTypeRule {
  allowed_types?: string[];  // per-pin whitelist; user picks independently
  type_var?: string;         // e.g., "T" (unifies across pins)
}

// Unified NodeGroup - replaces StaticNodes/DynamicNodes split
// Static nodes: min_count === max_count === 1
// Dynamic nodes: max_count > 1 or null
export interface NodeGroup {
  label: string;
  min_count: number;
  max_count?: number;        // null/undefined = unlimited
  typing: NodeTypeRule;
}

// I/O shape definitions
export interface IOSideShape {
  nodes: NodeGroup[];        // All nodes in a single array, ordered
}

export interface IOShape {
  inputs: IOSideShape;
  outputs: IOSideShape;
  type_params: Record<string, string[]>; // declare domains for type variables
}

export interface ModuleMeta {
  io_shape: IOShape;
}

// Runtime instance of a pin in a module instance
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

// Module instance structure
export interface ModuleInstance {
  module_instance_id: string;
  module_ref: string;
  module_kind: string;
  config: Record<string, any>;
  inputs: NodePin[];         // Flat array, grouped by group_index
  outputs: NodePin[];
}

// Module template structure
export interface ModuleTemplate {
  id: string;
  version: string;
  title: string;
  description: string;
  kind: string;
  color: string;
  category: string;
  meta: ModuleMeta;
  config_schema: any;
}

// Type variable management
export interface TypeVariableState {
  assignments: Record<string, string>; // typeVar -> currentType
  affectedNodes: Record<string, string[]>; // typeVar -> nodeIds[]
}

// Group info for UI
export interface GroupInfo {
  groupIndex: number;
  group: NodeGroup;
  currentCount: number;
  canAdd: boolean;
  canRemove: boolean;
}
