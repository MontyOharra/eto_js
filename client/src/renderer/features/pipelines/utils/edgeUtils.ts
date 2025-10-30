/**
 * Edge Utilities
 * Functions for edge creation, coloring, and management
 */

import { Node, Edge, Position } from "@xyflow/react";
import { ModuleInstance } from "../../../shared/types/moduleTypes";
import { findPin } from "./typeSystem";
import { TYPE_COLORS } from "./moduleUtils";

/**
 * Get color for a type
 */
export function getTypeColor(type: string): string {
  return TYPE_COLORS[type] || "#6B7280"; // gray-500 fallback
}

/**
 * Get edge color based on connected pins
 */
export function getEdgeColor(nodes: Node[], edge: Edge): string {
  const sourceNode = nodes.find((n) => n.id === edge.source);
  const targetNode = nodes.find((n) => n.id === edge.target);

  if (!sourceNode?.data?.moduleInstance || !targetNode?.data?.moduleInstance) {
    return "#6B7280"; // gray fallback
  }

  const sourceModule = sourceNode.data.moduleInstance as ModuleInstance;
  const targetModule = targetNode.data.moduleInstance as ModuleInstance;

  const sourcePin = findPin(sourceModule, edge.sourceHandle!);
  const targetPin = findPin(targetModule, edge.targetHandle!);

  // Use source pin type for color (they should match if connected)
  const type = sourcePin?.type || targetPin?.type || "str";
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
  return edges.filter(
    (edge) => edge.source !== moduleId && edge.target !== moduleId
  );
}

/**
 * Remove all edges connected to a specific pin
 */
export function removePinEdges(
  edges: Edge[],
  moduleId: string,
  pinId: string
): Edge[] {
  return edges.filter(
    (edge) =>
      !(edge.source === moduleId && edge.sourceHandle === pinId) &&
      !(edge.target === moduleId && edge.targetHandle === pinId)
  );
}

/**
 * Create React Flow edges from pipeline connections
 * Handles entry points (prefixed with 'entry-') and module instances
 */
export function createEdgesFromConnections(
  connections: Array<{ from_node_id: string; to_node_id: string }>,
  modules: any[],
  entryPoints: any[]
): Edge[] {
  const edges: Edge[] = [];

  connections.forEach((conn) => {
    // Determine source and target module IDs
    // Entry points in React Flow have 'entry-' prefix
    const sourceIsEntryPoint = entryPoints.some(
      (ep: any) => ep.node_id === conn.from_node_id
    );
    const sourceModuleId = sourceIsEntryPoint
      ? `entry-${conn.from_node_id}`
      : conn.from_node_id;

    const targetIsEntryPoint = entryPoints.some(
      (ep: any) => ep.node_id === conn.to_node_id
    );
    const targetModuleId = targetIsEntryPoint
      ? `entry-${conn.to_node_id}`
      : conn.to_node_id;

    // Find which module contains the source and target nodes
    let sourceNodeModuleId = sourceModuleId;
    let targetNodeModuleId = targetModuleId;

    // For non-entry-point nodes, find the module that contains this node
    if (!sourceIsEntryPoint) {
      const sourceModule = modules.find((m: any) =>
        [...m.inputs, ...m.outputs].some(
          (node: any) => node.node_id === conn.from_node_id
        )
      );
      if (sourceModule) {
        // Use module_instance_id (ModuleInstance property)
        sourceNodeModuleId = sourceModule.module_instance_id;
      }
    }

    if (!targetIsEntryPoint) {
      const targetModule = modules.find((m: any) =>
        [...m.inputs, ...m.outputs].some(
          (node: any) => node.node_id === conn.to_node_id
        )
      );
      if (targetModule) {
        // Use module_instance_id (ModuleInstance property)
        targetNodeModuleId = targetModule.module_instance_id;
      }
    }

    edges.push({
      id: `${conn.from_node_id}-${conn.to_node_id}`,
      source: sourceNodeModuleId,
      sourceHandle: conn.from_node_id,
      target: targetNodeModuleId,
      targetHandle: conn.to_node_id,
      sourcePosition: Position.Right, // Always right for LR layout
      targetPosition: Position.Left, // Always left for LR layout
      style: {
        stroke: "#6B7280",
        strokeWidth: 2,
      },
    });
  });

  return edges;
}
