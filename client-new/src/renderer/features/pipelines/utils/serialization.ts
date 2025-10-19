/**
 * Pipeline Serialization Utilities
 * Convert between React Flow state (nodes/edges) and pipeline state format
 */

import { Node, Edge } from '@xyflow/react';
import { PipelineState, VisualState, NodeConnection, EntryPoint } from '../../../types/pipelineTypes';
import { ModuleInstance } from '../../../types/moduleTypes';

/**
 * Serialize React Flow state to PipelineState
 */
export function serializeToPipelineState(nodes: Node[], edges: Edge[]): PipelineState {
  // Extract module instances from nodes (excluding entry points)
  const modules: ModuleInstance[] = nodes
    .filter((node) => node.type === 'module' && !node.data.isEntryPoint)
    .map((node) => node.data.moduleInstance as ModuleInstance)
    .filter(Boolean);

  // Extract entry points from nodes marked as entry points
  const entry_points: EntryPoint[] = nodes
    .filter((node) => node.data.isEntryPoint && node.data.entryPoint)
    .map((node) => node.data.entryPoint as EntryPoint)
    .filter(Boolean);

  // Extract connections from edges
  const connections: NodeConnection[] = edges.map((edge) => ({
    from_node_id: edge.sourceHandle!,
    to_node_id: edge.targetHandle!,
  }));

  return {
    entry_points,
    modules,
    connections,
  };
}

/**
 * Serialize React Flow state to VisualState (positions)
 */
export function serializeToVisualState(nodes: Node[]): VisualState {
  const modules: Record<string, { x: number; y: number }> = {};
  const entryPoints: Record<string, { x: number; y: number }> = {};

  nodes.forEach((node) => {
    if (node.type === 'module' && !node.data.isEntryPoint) {
      // Regular module
      modules[node.id] = {
        x: node.position.x,
        y: node.position.y,
      };
    } else if (node.data.isEntryPoint && node.data.entryPoint) {
      // Entry point node - store using entryPoint's node_id
      const entryPoint = node.data.entryPoint as EntryPoint;
      entryPoints[entryPoint.node_id] = {
        x: node.position.x,
        y: node.position.y,
      };
    }
  });

  return {
    modules,
    entryPoints,
  };
}
