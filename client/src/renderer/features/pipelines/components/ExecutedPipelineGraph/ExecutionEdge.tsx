/**
 * ExecutionEdge Component
 * Custom edge for execution visualization with orthogonal paths
 * Uses manual path construction with offset to prevent overlapping edges
 * Colors edges based on data type from execution output
 * Displays value labels next to edges with hover expansion
 */

import { useState, CSSProperties } from 'react';
import { BaseEdge, EdgeLabelRenderer, EdgeProps } from '@xyflow/react';
import { TYPE_COLORS } from '../../utils/moduleUtils';

export interface ExecutionEdgeData {
  output?: {
    name: string;
    value: any;
    type: string;
  } | null;
  offset?: number;
}

// Extended EdgeProps to ensure style and data are properly typed
interface ExecutionEdgeProps extends Omit<EdgeProps, 'style' | 'data'> {
  style?: CSSProperties;
  data?: ExecutionEdgeData;
}

// Check if a string is an ISO datetime format
const isISODateTime = (value: string): boolean => {
  // Match ISO 8601 datetime format: YYYY-MM-DDTHH:MM:SS or with milliseconds/timezone
  const isoPattern = /^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}/;
  return isoPattern.test(value);
};

// Format ISO datetime to human readable format
const formatDateTime = (isoString: string): string => {
  try {
    const date = new Date(isoString);
    if (isNaN(date.getTime())) return isoString;

    // Format as "MM/DD/YY HH:MM AM/PM"
    return date.toLocaleString('en-US', {
      month: '2-digit',
      day: '2-digit',
      year: '2-digit',
      hour: 'numeric',
      minute: '2-digit',
      hour12: true,
    });
  } catch {
    return isoString;
  }
};

// Check if value is a dim object (has height, length, width, qty, weight)
const isDimObject = (value: any): boolean => {
  return (
    typeof value === 'object' &&
    value !== null &&
    'height' in value &&
    'length' in value &&
    'width' in value &&
    'qty' in value &&
    'weight' in value
  );
};

// Format a single dim object as "qty - HxLxW @weightlbs"
const formatDim = (dim: any): string => {
  const h = dim.height ?? 0;
  const l = dim.length ?? 0;
  const w = dim.width ?? 0;
  const qty = dim.qty ?? 1;
  const weight = dim.weight ?? 0;
  return `${qty} - ${h}x${l}x${w} @${weight}lbs`;
};

const formatValue = (value: any, truncate: boolean = true): string => {
  if (value === null) return 'null';
  if (value === undefined) return 'undefined';
  if (typeof value === 'string') {
    // Check for ISO datetime format and convert to human readable
    if (isISODateTime(value)) {
      return formatDateTime(value);
    }
    return truncate && value.length > 30 ? value.substring(0, 30) + '...' : value;
  }
  if (typeof value === 'number') return value.toString();
  if (typeof value === 'boolean') return value.toString();
  if (typeof value === 'object') {
    // Check for dim object
    if (isDimObject(value)) {
      return formatDim(value);
    }
    // Check for list[dim] - array of dim objects
    if (Array.isArray(value) && value.length > 0 && isDimObject(value[0])) {
      const formatted = '[' + value.map(formatDim).join(', ') + ']';
      return truncate && formatted.length > 30 ? formatted.substring(0, 30) + '...' : formatted;
    }
    const stringified = JSON.stringify(value, null, 2);
    return truncate && stringified.length > 30 ? stringified.substring(0, 30) + '...' : stringified;
  }
  return String(value);
};

export function ExecutionEdge({
  sourceX,
  sourceY,
  targetX,
  targetY,
  style = {},
  markerEnd,
  data,
}: ExecutionEdgeProps) {
  const [isLabelHovered, setIsLabelHovered] = useState(false);
  const [isEdgeHovered, setIsEdgeHovered] = useState(false);

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

  // Combined hover state
  const isHovered = isLabelHovered || isEdgeHovered;

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
          stroke: edgeColor,
          strokeWidth: isHovered ? 3 : 2,
          filter: isHovered ? `drop-shadow(0 0 6px ${edgeColor})` : 'none',
          transition: 'all 0.2s ease',
        }}
      />

      {/* Value label - only show if output data exists */}
      {output?.value !== undefined && (
        <EdgeLabelRenderer>
          <div
            style={{
              position: 'absolute',
              transform: `translate(-50%, -50%) translate(${labelOffsetX}px,${labelOffsetY}px)`,
              fontSize: 14,
              fontWeight: 500,
              pointerEvents: 'all',
            }}
            className="nodrag nopan"
          >
            <div
              style={{
                backgroundColor: '#1F2937',
                border: `2px solid ${edgeColor}`,
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
                boxShadow: isHovered ? `0 0 12px ${edgeColor}` : 'none',
                transition: 'all 0.2s ease',
              }}
              onMouseEnter={() => setIsLabelHovered(true)}
              onMouseLeave={() => setIsLabelHovered(false)}
              title={`Value: ${JSON.stringify(output.value)}`}
            >
              {formatValue(output.value, !isHovered)}
            </div>
          </div>
        </EdgeLabelRenderer>
      )}
    </>
  );
}
