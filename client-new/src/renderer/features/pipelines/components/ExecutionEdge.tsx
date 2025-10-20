/**
 * ExecutionEdge Component
 * Custom edge for execution visualization with value labels positioned near source
 */

import { useState } from 'react';
import { BaseEdge, EdgeLabelRenderer, EdgeProps, getSmoothStepPath } from '@xyflow/react';

export interface ExecutionEdgeData {
  value?: any;
  type?: string;
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
  const [isHovered, setIsHovered] = useState(false);
  const [edgePath, labelX, labelY] = getSmoothStepPath({
    sourceX,
    sourceY,
    sourcePosition,
    targetX,
    targetY,
    targetPosition,
  });

  const executionData = data as ExecutionEdgeData;
  const typeColor = executionData?.type ? TYPE_COLORS[executionData.type] || '#6B7280' : '#6B7280';

  // Position label near the source output pin
  // For LR layout, place label slightly to the right of the source
  const labelOffsetX = sourceX + 80; // 80px to the right of source
  const labelOffsetY = sourceY;

  return (
    <>
      <BaseEdge
        path={edgePath}
        markerEnd={markerEnd}
        style={{
          ...style,
          stroke: typeColor,
          strokeWidth: 2,
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
              }}
              onMouseEnter={() => setIsHovered(true)}
              onMouseLeave={() => setIsHovered(false)}
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
