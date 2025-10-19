/**
 * Edge Utilities
 * Functions for edge creation, coloring, and management
 */

import { Node, Edge } from '@xyflow/react';
import { ModuleInstance } from '../../../types/moduleTypes';
import { findPin } from './typeSystem';

/**
 * Type to color mapping
 */
export const TYPE_COLORS: Record<string, string> = {
  str: '#3B82F6', // blue-500
  int: '#EF4444', // red-500
  float: '#F59E0B', // amber-500
  bool: '#10B981', // green-500
  datetime: '#8B5CF6', // purple-500
};

/**
 * Get color for a type
 */
export function getTypeColor(type: string): string {
  return TYPE_COLORS[type] || '#6B7280'; // gray-500 fallback
}

/**
 * Get edge color based on connected pins
 */
export function getEdgeColor(
  nodes: Node[],
  edge: Edge
): string {
  const sourceNode = nodes.find((n) => n.id === edge.source);
  const targetNode = nodes.find((n) => n.id === edge.target);

  if (!sourceNode?.data?.moduleInstance || !targetNode?.data?.moduleInstance) {
    return '#6B7280'; // gray fallback
  }

  const sourceModule = sourceNode.data.moduleInstance as ModuleInstance;
  const targetModule = targetNode.data.moduleInstance as ModuleInstance;

  const sourcePin = findPin(sourceModule, edge.sourceHandle!);
  const targetPin = findPin(targetModule, edge.targetHandle!);

  // Use source pin type for color (they should match if connected)
  const type = sourcePin?.type || targetPin?.type || 'str';
  return getTypeColor(type);
}

/**
 * Update edge colors for all edges in graph
 */
export function updateEdgeColors(nodes: Node[], edges: Edge[]): Edge[] {
  return edges.map((edge) => {
    const color = getEdgeColor(nodes, edge);
    return {
      ...edge,
      style: {
        ...edge.style,
        stroke: color,
        strokeWidth: edge.style?.strokeWidth || 2,
      },
    };
  });
}

/**
 * Create a new edge with proper styling
 */
export function createStyledEdge(
  source: string,
  sourceHandle: string,
  target: string,
  targetHandle: string,
  type: string
): Edge {
  const color = getTypeColor(type);

  return {
    id: `${source}-${sourceHandle}-${target}-${targetHandle}`,
    source,
    sourceHandle,
    target,
    targetHandle,
    style: {
      stroke: color,
      strokeWidth: 2,
    },
  };
}

/**
 * Find all edges connected to a specific pin
 */
export function findConnectedEdges(
  edges: Edge[],
  moduleId: string,
  pinId: string
): Edge[] {
  return edges.filter(
    (edge) =>
      (edge.source === moduleId && edge.sourceHandle === pinId) ||
      (edge.target === moduleId && edge.targetHandle === pinId)
  );
}

/**
 * Find edge connecting two specific pins
 */
export function findEdgeBetweenPins(
  edges: Edge[],
  sourceModuleId: string,
  sourcePinId: string,
  targetModuleId: string,
  targetPinId: string
): Edge | undefined {
  return edges.find(
    (edge) =>
      edge.source === sourceModuleId &&
      edge.sourceHandle === sourcePinId &&
      edge.target === targetModuleId &&
      edge.targetHandle === targetPinId
  );
}

/**
 * Remove all edges connected to a specific module
 */
export function removeModuleEdges(edges: Edge[], moduleId: string): Edge[] {
  return edges.filter((edge) => edge.source !== moduleId && edge.target !== moduleId);
}

/**
 * Remove all edges connected to a specific pin
 */
export function removePinEdges(edges: Edge[], moduleId: string, pinId: string): Edge[] {
  return edges.filter(
    (edge) =>
      !(edge.source === moduleId && edge.sourceHandle === pinId) &&
      !(edge.target === moduleId && edge.targetHandle === pinId)
  );
}
