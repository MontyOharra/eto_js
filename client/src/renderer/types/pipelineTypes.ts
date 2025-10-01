/**
 * Type definitions for the Transformation Pipeline system
 * These types match the backend API structure exactly
 */

// Module template from API
export interface ModuleTemplate {
  module_ref: string;
  id: string;
  version: string;
  title: string;
  description: string;
  kind: 'transform' | 'action' | 'logic';
  meta: {
    inputs: {
      allow: boolean;
      min_count: number;
      max_count: number | null;
      type: string[];  // Array of allowed types - empty array means all types allowed
    };
    outputs: {
      allow: boolean;
      min_count: number;
      max_count: number | null;
      type: string[];  // Array of allowed types - empty array means all types allowed
    };
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