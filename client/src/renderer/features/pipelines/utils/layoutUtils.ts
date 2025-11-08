/**
 * Layout utility functions for pipeline graph positioning
 */

import { Node } from '@xyflow/react';

/**
 * Calculate position for a new entry point
 * Places it at the bottom-left of existing nodes
 */
export function calculateNewEntryPointPosition(
  existingNodes: Node[]
): { x: number; y: number } {
  if (existingNodes.length === 0) {
    return { x: 50, y: 50 }; // Default position if no nodes
  }

  // Find the leftmost and bottommost positions
  let minX = Infinity;
  let maxY = -Infinity;

  existingNodes.forEach((node) => {
    const pos = node.position;
    if (pos.x < minX) minX = pos.x;
    if (pos.y > maxY) maxY = pos.y;
  });

  // Place new entry point below the bottom-most node, aligned left
  return {
    x: minX,
    y: maxY + 150, // 150px below the bottom node
  };
}
