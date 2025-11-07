/**
 * ExecutionEdge Component
 * Custom edge for execution visualization with orthogonal paths
 * Uses manual path construction with offset to prevent overlapping edges
 * Colors edges based on data type from execution output
 */

import { BaseEdge, EdgeProps } from '@xyflow/react';
import { TYPE_COLORS } from '../../utils/moduleUtils';

export interface ExecutionEdgeData {
  output?: {
    name: string;
    value: any;
    type: string;
  } | null;
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

  // Determine edge color based on output data type
  // If no output data (null), use default gray (no data flowed through)
  const output = data?.output;
  const edgeColor = output?.type
    ? TYPE_COLORS[output.type] || '#6B7280' // Use type color or fallback to gray
    : '#6B7280'; // No output data = gray

  return (
    <BaseEdge
      path={edgePath}
      markerEnd={markerEnd}
      style={{
        ...style,
        stroke: edgeColor,
        strokeWidth: 2,
      }}
    />
  );
}
