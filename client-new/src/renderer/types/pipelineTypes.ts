/**
 * Type definitions for the Transformation Pipeline system
 * Adapted from client/src/renderer/types/pipelineTypes.ts
 */

import type {
  NodeTypeRule,
  NodeGroup,
  IOSideShape,
  IOShape,
  ModuleTemplate,
  ModuleInstance,
  NodePin
} from './moduleTypes';

// Re-export module type definitions
export type {
  NodeTypeRule,
  NodeGroup,
  IOSideShape,
  IOShape,
  ModuleTemplate,
  ModuleInstance,
  NodePin
};

// Connection between nodes (for pipeline graph)
export interface PipelineConnection {
  connection_id: string;
  source_node_id: string;    // module instance ID or entry point node ID
  target_node_id: string;    // module instance ID
  source_pin_id: string;     // output pin node_id
  target_pin_id: string;     // input pin node_id
}

// Entry point for pipeline (frontend - includes type for UI)
export interface EntryPoint {
  node_id: string;
  name: string;
  type: string;
}

// Pipeline state (execution data)
export interface PipelineState {
  entry_points: EntryPoint[];
  modules: ModuleInstance[];
  connections: PipelineConnection[];
}

// Visual state (UI positioning)
export interface VisualState {
  positions: Record<string, { x: number; y: number }>;
}

// Complete pipeline data (for saving/loading)
export interface PipelineData {
  schema_version?: string;
  name?: string;
  description?: string;
  pipeline_state: PipelineState;
  visual_state: VisualState;
}

// API response for modules endpoint
export interface ModulesResponse {
  modules: ModuleTemplate[];
  total_count: number;
  stats?: {
    total_modules: number;
    transform_modules: number;
    action_modules: number;
    logic_modules: number;
    module_refs: string[];
  };
}
