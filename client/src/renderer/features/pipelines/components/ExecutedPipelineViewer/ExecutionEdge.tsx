/**
 * ExecutionEdge Component
 * Custom edge for execution visualization with orthogonal paths
 * Uses manual path construction with offset to prevent overlapping edges
 */

import { BaseEdge, EdgeProps } from '@xyflow/react';

export interface ExecutionEdgeData {
  value?: any;
  type?: string;
  offset?: number;
}

export function ExecutionEdge({
  sourceX,
  sourceY,
  targetX,
  targetY,
  style = {},
  markerEnd,
  data,
}: EdgeProps<ExecutionEdgeData>) {
  // Apply horizontal offset for parallel edges - only to the middle vertical section
  const horizontalOffset = data?.offset || 0;

  // For LR layout, manually construct the path with bends closer to target
  // Position the vertical line close to the target (40px before target)
  const midX = targetX - 40 + horizontalOffset;

  // Construct smooth step path: horizontal from source, vertical (offset), horizontal to target
  const edgePath = `M ${sourceX},${sourceY} L ${midX},${sourceY} L ${midX},${targetY} L ${targetX},${targetY}`;

  return (
    <BaseEdge
      path={edgePath}
      markerEnd={markerEnd}
      style={{
        ...style,
        stroke: '#6B7280',
        strokeWidth: 2,
      }}
    />
  );
}
