/**
 * Auto-layout utility for executed pipeline viewer
 * Arranges nodes in a left-to-right flow based on dependencies
 * Uses layered graph layout (Sugiyama framework)
 */

interface LayoutNode {
  id: string;
  width?: number;
  height?: number;
}

interface LayoutEdge {
  source_module_id: string;
  target_module_id: string;
}

interface Position {
  x: number;
  y: number;
}

const NODE_WIDTH = 450;
const NODE_HEIGHT = 200;
const HORIZONTAL_SPACING = 200;
const VERTICAL_SPACING = 50;

/**
 * Calculate node layers using topological sort (BFS-based)
 * Returns map of node ID -> layer number (0-indexed)
 */
function calculateLayers(
  nodes: LayoutNode[],
  edges: LayoutEdge[],
  entryPointIds: string[]
): Map<string, number> {
  const layers = new Map<string, number>();
  const inDegree = new Map<string, number>();
  const adjacencyList = new Map<string, string[]>();

  // Initialize
  nodes.forEach(node => {
    inDegree.set(node.id, 0);
    adjacencyList.set(node.id, []);
  });

  // Build graph
  edges.forEach(edge => {
    const current = inDegree.get(edge.target_module_id) || 0;
    inDegree.set(edge.target_module_id, current + 1);

    const neighbors = adjacencyList.get(edge.source_module_id) || [];
    neighbors.push(edge.target_module_id);
    adjacencyList.set(edge.source_module_id, neighbors);
  });

  // BFS starting from entry points
  const queue: Array<{ id: string; layer: number }> = [];

  // Start with entry points at layer 0
  entryPointIds.forEach(id => {
    layers.set(id, 0);
    queue.push({ id, layer: 0 });
  });

  // Process nodes with no dependencies (in case not connected to entry points)
  nodes.forEach(node => {
    if (!entryPointIds.includes(node.id) && (inDegree.get(node.id) || 0) === 0) {
      layers.set(node.id, 0);
      queue.push({ id: node.id, layer: 0 });
    }
  });

  const processed = new Set<string>();

  while (queue.length > 0) {
    const { id, layer } = queue.shift()!;
    if (processed.has(id)) continue;
    processed.add(id);

    const neighbors = adjacencyList.get(id) || [];
    neighbors.forEach(neighborId => {
      const currentLayer = layers.get(neighborId);
      const newLayer = layer + 1;

      // Update to deeper layer if needed
      if (currentLayer === undefined || newLayer > currentLayer) {
        layers.set(neighborId, newLayer);
      }

      // Decrease in-degree
      const degree = inDegree.get(neighborId)! - 1;
      inDegree.set(neighborId, degree);

      // Add to queue if all dependencies processed
      if (degree === 0) {
        queue.push({ id: neighborId, layer: newLayer });
      }
    });
  }

  // Handle any remaining nodes (cycles or disconnected)
  nodes.forEach(node => {
    if (!layers.has(node.id)) {
      layers.set(node.id, 0);
    }
  });

  return layers;
}

/**
 * Auto-arrange nodes in left-to-right layers
 */
export function autoLayoutNodes(
  nodes: LayoutNode[],
  edges: LayoutEdge[],
  entryPointIds: string[]
): Record<string, Position> {
  if (nodes.length === 0) return {};

  // Calculate layers
  const nodeLayers = calculateLayers(nodes, edges, entryPointIds);

  // Group nodes by layer
  const layerGroups = new Map<number, string[]>();
  let maxLayer = 0;

  nodeLayers.forEach((layer, nodeId) => {
    maxLayer = Math.max(maxLayer, layer);
    const group = layerGroups.get(layer) || [];
    group.push(nodeId);
    layerGroups.set(layer, group);
  });

  // Calculate positions
  const positions: Record<string, Position> = {};

  for (let layer = 0; layer <= maxLayer; layer++) {
    const nodesInLayer = layerGroups.get(layer) || [];
    const layerHeight = nodesInLayer.length * (NODE_HEIGHT + VERTICAL_SPACING);

    nodesInLayer.forEach((nodeId, index) => {
      const x = layer * (NODE_WIDTH + HORIZONTAL_SPACING);
      const y = index * (NODE_HEIGHT + VERTICAL_SPACING) - layerHeight / 2 + window.innerHeight / 2;

      positions[nodeId] = { x, y };
    });
  }

  return positions;
}

/**
 * Apply auto-layout to visual state
 */
export function applyAutoLayout(
  entryPoints: Array<{ id: string }>,
  modules: Array<{ instance_id: string }>,
  connections: LayoutEdge[]
): Record<string, Position> {
  const allNodes: LayoutNode[] = [
    ...entryPoints.map(ep => ({ id: ep.id })),
    ...modules.map(m => ({ id: m.instance_id })),
  ];

  const entryPointIds = entryPoints.map(ep => ep.id);

  return autoLayoutNodes(allNodes, connections, entryPointIds);
}
