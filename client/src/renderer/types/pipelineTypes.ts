/**
 * Type definitions for the Transformation Pipeline system
 * These types match the backend API structure exactly
 */

// Node type definitions
export interface NodeTypeRule {
  allowed_types?: string[];
  type_var?: string;
}

export interface NodeSpec {
  label: string;
  typing: NodeTypeRule;
}

export interface StaticNodes {
  slots: NodeSpec[];
}

export interface DynamicNodeGroup {
  min_count: number;
  max_count?: number | null;
  item: NodeSpec;
}

export interface DynamicNodes {
  groups: Record<string, DynamicNodeGroup>;
}

export interface IOSideShape {
  static?: StaticNodes;
  dynamic?: DynamicNodes;
}

export interface IOShape {
  inputs: IOSideShape;
  outputs: IOSideShape;
  type_params?: Record<string, string[]>;
}

// Module template from API
export interface ModuleTemplate {
  module_ref: string;
  id: string;
  version: string;
  title: string;
  description: string;
  kind: 'transform' | 'action' | 'logic';
  meta: {
    io_shape: IOShape;
  };
  config_schema: any; // JSON Schema object
  category: string;
  color: string;
}

// Node/Pin in a module instance
export interface NodePin {
  node_id: string;
  direction: 'in' | 'out';
  type: string;
  name: string;
  position_index: number;
}

// Module instance (placed on canvas)
export interface ModuleInstance {
  module_instance_id: string;
  module_ref: string; // e.g., "text_cleaner:1.0.0"
  module_kind: string;
  config: Record<string, any>;
  inputs: NodePin[];
  outputs: NodePin[];
}

// Connection between nodes
export interface NodeConnection {
  from_node_id: string;
  to_node_id: string;
}

// Entry point for pipeline
export interface EntryPoint {
  node_id: string;
  name: string;
  type: string;
}

// Pipeline state (execution data)
export interface PipelineState {
  entry_points: EntryPoint[];
  modules: ModuleInstance[];
  connections: NodeConnection[];
}

// Visual state (UI positioning)
export interface VisualState {
  modules: Record<string, { x: number; y: number }>;
  entryPoints?: Record<string, { x: number; y: number }>;
}

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