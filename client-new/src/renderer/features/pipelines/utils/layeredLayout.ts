/**
 * Layered Graph Layout Algorithm (Sugiyama-style)
 *
 * Arranges pipeline nodes in horizontal layers from left to right:
 * - Entry points are leftmost (layer 0)
 * - Each module is placed based on the maximum layer of its predecessors + 1
 * - Earlier execution = further left, later execution = further right
 *
 * This provides clear visual flow of data through the pipeline.
 */

export interface LayoutNode {
  id: string;
  width?: number;
  height?: number;
}

export interface LayoutConnection {
  from_node_id: string;
  to_node_id: string;
}

export interface Position {
  x: number;
  y: number;
}

/**
 * Calculate layer assignments for all nodes in the pipeline
 * Uses topological ordering to ensure proper left-to-right flow
 */
function calculateLayers(
  entryPoints: any[],
  modules: any[],
  connections: LayoutConnection[]
): Map<string, number> {
  const layers = new Map<string, number>();

  // Entry points start at layer 0
  entryPoints.forEach((ep) => {
    layers.set(ep.node_id, 0);
  });

  // Build adjacency list for quick lookups
  // Maps from node_id -> list of target node_ids
  const adjacency = new Map<string, string[]>();
  connections.forEach((conn) => {
    if (!adjacency.has(conn.from_node_id)) {
      adjacency.set(conn.from_node_id, []);
    }
    adjacency.get(conn.from_node_id)!.push(conn.to_node_id);
  });

  // Map node_id -> module that contains it
  const nodeToModule = new Map<string, any>();
  modules.forEach((module) => {
    [...module.inputs, ...module.outputs].forEach((node: any) => {
      nodeToModule.set(node.node_id, module);
    });
  });

  // Process nodes in topological order using queue
  const queue: string[] = [...entryPoints.map((ep) => ep.node_id)];
  const visited = new Set<string>();

  while (queue.length > 0) {
    const nodeId = queue.shift()!;
    if (visited.has(nodeId)) continue;
    visited.add(nodeId);

    const sourceLayer = layers.get(nodeId) || 0;

    // Find all nodes connected from this one
    const targets = adjacency.get(nodeId) || [];

    targets.forEach((targetNodeId) => {
      // Find module containing target node
      const targetModule = nodeToModule.get(targetNodeId);
      if (!targetModule) return;

      const targetModuleId = targetModule.module_instance_id;

      // Module's layer = max of all its input pins' layers + 1
      // Check all input pins to find the maximum source layer
      let maxInputLayer = sourceLayer;
      targetModule.inputs.forEach((inputNode: any) => {
        const inputLayer = layers.get(inputNode.node_id) || 0;
        maxInputLayer = Math.max(maxInputLayer, inputLayer);
      });

      // Set module layer (use all output nodes as proxy for module)
      const newLayer = maxInputLayer + 1;
      const currentLayer = layers.get(targetModuleId) || 0;

      if (newLayer > currentLayer) {
        // Update all output nodes to this layer
        targetModule.outputs.forEach((outputNode: any) => {
          layers.set(outputNode.node_id, newLayer);
        });
        // Also set the module itself
        layers.set(targetModuleId, newLayer);

        // Queue all output nodes for further processing
        targetModule.outputs.forEach((outputNode: any) => {
          queue.push(outputNode.node_id);
        });
      }
    });
  }

  return layers;
}

/**
 * Group nodes by their assigned layer
 */
function groupByLayer(layers: Map<string, number>): Map<number, string[]> {
  const layerGroups = new Map<number, string[]>();

  layers.forEach((layer, nodeId) => {
    if (!layerGroups.has(layer)) {
      layerGroups.set(layer, []);
    }
    layerGroups.get(layer)!.push(nodeId);
  });

  return layerGroups;
}

/**
 * Calculate positions for all nodes based on layer assignments
 */
function calculatePositions(
  layers: Map<string, number>,
  modules: any[],
  entryPoints: any[]
): Record<string, Position> {
  const positions: Record<string, Position> = {};

  // Group nodes by layer
  const layerGroups = groupByLayer(layers);

  // Layout constants
  const LAYER_SPACING = 500;  // Horizontal spacing between layers
  const NODE_SPACING = 180;   // Vertical spacing between nodes in same layer
  const START_X = 50;         // Left margin

  // Process each layer
  layerGroups.forEach((nodeIds, layerIndex) => {
    // Deduplicate - we may have both entry points and module IDs in the list
    const uniqueIds = new Set<string>();
    const nodesToPosition: Array<{ id: string; isEntryPoint: boolean }> = [];

    nodeIds.forEach((nodeId) => {
      // Check if this is an entry point
      const isEntryPoint = entryPoints.some((ep) => ep.node_id === nodeId);

      if (isEntryPoint) {
        if (!uniqueIds.has(nodeId)) {
          uniqueIds.add(nodeId);
          nodesToPosition.push({ id: nodeId, isEntryPoint: true });
        }
      } else {
        // Check if this is a module ID
        const module = modules.find((m) => m.module_instance_id === nodeId);
        if (module && !uniqueIds.has(nodeId)) {
          uniqueIds.add(nodeId);
          nodesToPosition.push({ id: nodeId, isEntryPoint: false });
        }
      }
    });

    // Calculate vertical positioning
    const layerHeight = nodesToPosition.length * NODE_SPACING;
    const startY = -layerHeight / 2;

    // Position each node in this layer
    nodesToPosition.forEach((node, index) => {
      const x = START_X + (layerIndex * LAYER_SPACING);
      const y = startY + (index * NODE_SPACING);

      positions[node.id] = { x, y };
    });
  });

  return positions;
}

/**
 * Main entry point: Calculate layered layout for pipeline
 * Returns positions for both entry points and modules
 */
export function applyLayeredLayout(
  entryPoints: any[],
  modules: any[],
  connections: LayoutConnection[]
): Record<string, Position> {
  console.log('[LayeredLayout] Calculating layout for', {
    entryPoints: entryPoints.length,
    modules: modules.length,
    connections: connections.length,
  });

  // Step 1: Calculate layer assignments
  const layers = calculateLayers(entryPoints, modules, connections);

  console.log('[LayeredLayout] Layer assignments:', Array.from(layers.entries()));

  // Step 2: Calculate positions based on layers
  const positions = calculatePositions(layers, modules, entryPoints);

  console.log('[LayeredLayout] Calculated positions for', Object.keys(positions).length, 'nodes');

  return positions;
}
