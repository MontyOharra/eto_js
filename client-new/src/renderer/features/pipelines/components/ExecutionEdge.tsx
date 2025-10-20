/**
 * ExecutionEdge Component
 * Custom edge for execution visualization with value labels near source
 *
 * Features:
 * - Smooth step edges (orthogonal with 90-degree corners)
 * - Value labels positioned next to source output pins
 * - Interactive hover: hovering edge or label highlights both with glow effect
 * - Type-colored borders and glow effects
 * - Fixed-width labels with hover expansion
 */

import { useState } from 'react';
import { BaseEdge, EdgeLabelRenderer, EdgeProps, getSmoothStepPath } from '@xyflow/react';

export interface ExecutionEdgeData {
  value?: any;
  type?: string;
  offset?: number;
}

const TYPE_COLORS: Record<string, string> = {
  str: '#3B82F6',
  int: '#EF4444',
  float: '#F59E0B',
  bool: '#10B981',
  datetime: '#8B5CF6',
};

const formatValue = (value: any, truncate: boolean = true): string => {
  if (value === null) return 'null';
  if (value === undefined) return 'undefined';
  if (typeof value === 'string') {
    return truncate && value.length > 30 ? value.substring(0, 30) + '...' : value;
  }
  if (typeof value === 'number') return value.toString();
  if (typeof value === 'boolean') return value.toString();
  if (typeof value === 'object') {
    const stringified = JSON.stringify(value, null, 2);
    return truncate && stringified.length > 30 ? stringified.substring(0, 30) + '...' : stringified;
  }
  return String(value);
};

export function ExecutionEdge({
  id,
  sourceX,
  sourceY,
  targetX,
  targetY,
  sourcePosition,
  targetPosition,
  style = {},
  markerEnd,
  data,
}: EdgeProps<ExecutionEdgeData>) {
  const [isLabelHovered, setIsLabelHovered] = useState(false);
  const [isEdgeHovered, setIsEdgeHovered] = useState(false);

  // Combined hover state - true if either label or edge is hovered
  const isHovered = isLabelHovered || isEdgeHovered;

  const executionData = data as ExecutionEdgeData;
  const typeColor = executionData?.type ? TYPE_COLORS[executionData.type] || '#6B7280' : '#6B7280';

  // Apply horizontal offset for parallel edges - only to the middle vertical section
  const horizontalOffset = executionData?.offset || 0;

  // Get the standard path first
  const [standardPath, labelX, labelY] = getSmoothStepPath({
    sourceX,
    sourceY,
    sourcePosition,
    targetX,
    targetY,
    targetPosition,
  });

  // For LR layout with horizontal offset, manually construct the path
  // to keep connection points fixed but offset the vertical section
  let edgePath = standardPath;
  if (horizontalOffset !== 0) {
    // Calculate the midpoint X where the vertical line should be
    const midX = sourceX + (targetX - sourceX) / 2 + horizontalOffset;

    // Construct smooth step path: horizontal from source, vertical (offset), horizontal to target
    edgePath = `M ${sourceX},${sourceY} L ${midX},${sourceY} L ${midX},${targetY} L ${targetX},${targetY}`;
  }

  // Position label next to the source output pin
  // For LR layout, place label slightly to the right of the source
  const labelOffsetX = sourceX + 80; // 80px to the right of source
  const labelOffsetY = sourceY;

  return (
    <>
      {/* Invisible wider path for easier hovering */}
      <path
        d={edgePath}
        fill="none"
        stroke="transparent"
        strokeWidth={20}
        style={{ pointerEvents: 'stroke', cursor: 'pointer' }}
        onMouseEnter={() => setIsEdgeHovered(true)}
        onMouseLeave={() => setIsEdgeHovered(false)}
      />

      {/* Visible edge with glow effect when hovered */}
      <BaseEdge
        path={edgePath}
        markerEnd={markerEnd}
        style={{
          ...style,
          stroke: typeColor,
          strokeWidth: isHovered ? 3 : 2,
          filter: isHovered ? `drop-shadow(0 0 6px ${typeColor})` : 'none',
          transition: 'all 0.2s ease',
        }}
      />

      {executionData?.value !== undefined && (
        <EdgeLabelRenderer>
          <div
            style={{
              position: 'absolute',
              transform: `translate(-50%, -50%) translate(${labelOffsetX}px,${labelOffsetY}px)`,
              fontSize: 11,
              fontWeight: 500,
              pointerEvents: 'all',
            }}
            className="nodrag nopan"
          >
            <div
              style={{
                backgroundColor: '#1F2937',
                border: `2px solid ${typeColor}`,
                borderRadius: 4,
                padding: '4px 8px',
                color: '#E5E7EB',
                width: '120px',
                maxWidth: '120px',
                overflow: 'hidden',
                textOverflow: 'ellipsis',
                whiteSpace: isHovered ? 'normal' : 'nowrap',
                cursor: 'pointer',
                wordBreak: 'break-word',
                boxShadow: isHovered ? `0 0 12px ${typeColor}` : 'none',
                transition: 'all 0.2s ease',
              }}
              onMouseEnter={() => setIsLabelHovered(true)}
              onMouseLeave={() => setIsLabelHovered(false)}
              title={`Value: ${JSON.stringify(executionData.value)}`}
            >
              {formatValue(executionData.value, !isHovered)}
            </div>
          </div>
        </EdgeLabelRenderer>
      )}
    </>
  );
}
