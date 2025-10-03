/**
 * New module type system supporting static/dynamic nodes and type variables
 * Based on backend contracts.py structure
 */

// Node type system
export interface NodeTypeRule {
  allowed_types?: string[];  // per-pin whitelist; user picks independently
  type_var?: string;         // e.g., "T" (unifies across pins)
}

export interface NodeSpec {
  label: string;             // UI label, e.g., "cond", "value"
  typing: NodeTypeRule;
}

// Static node definitions
export interface StaticNodes {
  slots: NodeSpec[];         // exact count, fixed order
}

// Dynamic node groups
export interface DynamicNodeGroup {
  min_count: number;
  max_count?: number;
  item: NodeSpec;            // typing applies per pin instance
}

export interface DynamicNodes {
  groups: DynamicNodeGroup[];
}

// I/O shape definitions
export interface IOSideShape {
  static?: StaticNodes;
  dynamic?: DynamicNodes;
}

export interface IOShape {
  inputs: IOSideShape;
  outputs: IOSideShape;
  type_params: Record<string, string[]>; // declare domains for type variables
}

export interface ModuleMeta {
  io_shape: IOShape;
}

// Updated NodePin with new fields
export interface NodePin {
  node_id: string;
  direction: 'in' | 'out';
  type: string;
  name: string;              // user-editable name
  label: string;             // from NodeSpec (static)
  position_index: number;
  group_key?: string;        // for dynamic nodes - which group they belong to
  is_static: boolean;        // whether this is a static or dynamic node
  type_var?: string;         // type variable name if applicable
  allowed_types?: string[];  // allowed types for this node (from template)
}

// Module instance structure
export interface ModuleInstance {
  module_instance_id: string;
  module_ref: string;
  module_kind: string;
  config: Record<string, any>;
  inputs: NodePin[];
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
  meta: ModuleMeta;
  config_schema: any;
}

// Type variable management
export interface TypeVariableState {
  assignments: Record<string, string>; // typeVar -> currentType
  affectedNodes: Record<string, string[]>; // typeVar -> nodeIds[]
}

// Dynamic group info for UI
export interface DynamicGroupInfo {
  groupKey: string;
  group: DynamicNodeGroup;
  currentCount: number;
  canAdd: boolean;
  canRemove: boolean;
}