/**
 * Type definitions for the Transformation Pipeline system
 */

import {
  NodeTypeRule as _NodeTypeRule,
  NodeSpec as _NodeSpec,
  StaticNodes as _StaticNodes,
  DynamicNodeGroup as _DynamicNodeGroup,
  DynamicNodes as _DynamicNodes,
  IOSideShape as _IOSideShape,
  IOShape as _IOShape,
  ModuleTemplate as _ModuleTemplate,
  ModuleInstance as _ModuleInstance,
  NodePin as _NodePin
} from './moduleTypes';

// Re-export module type definitions
export type NodeTypeRule = _NodeTypeRule;
export type NodeSpec = _NodeSpec;
export type StaticNodes = _StaticNodes;
export type DynamicNodeGroup = _DynamicNodeGroup;
export type DynamicNodes = _DynamicNodes;
export type IOSideShape = _IOSideShape;
export type IOShape = _IOShape;
export type ModuleTemplate = _ModuleTemplate;
export type ModuleInstance = _ModuleInstance;
export type NodePin = _NodePin;


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

// Type alias for compatibility
export type Connection = NodeConnection;