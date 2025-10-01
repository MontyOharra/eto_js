import React, { useState, useEffect } from 'react';
import { Connection, NodePin } from '../../../types/pipelineTypes';

interface StartingConnection {
  moduleId: string;
  nodeId: string;
  nodeType: 'input' | 'output';
}

interface ConnectionLayerProps {
  // Connection data
  connections: Connection[];
  selectedConnectionId: string | null;
  startingConnection: StartingConnection | null;
  currentMousePosition: { x: number; y: number };

  // Module positions for calculating node positions
  modulePositions: Record<string, { x: number; y: number }>;
  modules: any[]; // Module instances to find nodes

  // Zoom and pan for coordinate conversion
  zoom: number;
  panOffset: { x: number; y: number };

  // Helper functions
  getNodeType: (nodeId: string) => string;
  getTypeColor: (type: string) => string;

  // Event handlers
  onConnectionClick: (connectionId: string) => void;
  onConnectionDelete: (connectionId: string) => void;
}

export const ConnectionLayer: React.FC<ConnectionLayerProps> = ({
  connections,
  selectedConnectionId,
  startingConnection,
  currentMousePosition,
  modulePositions,
  modules,
  zoom,
  panOffset,
  getNodeType,
  getTypeColor,
  onConnectionClick,
  onConnectionDelete
}) => {
  // Force update when zoom, pan, modules, or connections change
  const [, forceUpdate] = useState(0);
  useEffect(() => {
    forceUpdate(prev => prev + 1);
  }, [zoom, panOffset, modules, connections]);

  // Use MutationObserver to detect when node positions might change due to text changes
  useEffect(() => {
    const observer = new MutationObserver(() => {
      // Use requestAnimationFrame to ensure DOM has updated before recalculating
      requestAnimationFrame(() => {
        forceUpdate(prev => prev + 1);
      });
    });

    // Observe the canvas for changes to module content
    const canvas = document.querySelector('.transformation-graph-canvas');
    if (canvas) {
      observer.observe(canvas, {
        subtree: true,
        characterData: true,
        childList: true,
        attributes: true,
        attributeFilter: ['style', 'class']
      });
    }

    return () => {
      observer.disconnect();
    };
  }, []);

  // Get node position directly from DOM for real-time accuracy
  const getNodePosition = (nodeId: string): { x: number; y: number } | null => {
    const nodeElement = document.querySelector(`[data-node-id="${nodeId}"]`);
    if (!nodeElement) return null;

    const rect = nodeElement.getBoundingClientRect();
    const canvas = document.querySelector('.transformation-graph-canvas');
    if (!canvas) return null;

    const canvasRect = canvas.getBoundingClientRect();

    // Calculate center of node relative to canvas
    const centerX = rect.left + rect.width / 2 - canvasRect.left;
    const centerY = rect.top + rect.height / 2 - canvasRect.top;

    // Convert to canvas coordinates (accounting for zoom and pan)
    return {
      x: (centerX - panOffset.x) / zoom,
      y: (centerY - panOffset.y) / zoom
    };
  };

  // Generate bezier path for connection
  const generateBezierPath = (
    start: { x: number; y: number },
    end: { x: number; y: number },
    startType: 'input' | 'output',
    isPreview: boolean = false
  ): string => {
    const controlPointOffset = Math.min(Math.abs(end.x - start.x) * 0.5, 100);

    let cp1x, cp2x;

    if (startType === 'input') {
      // Starting from input node (left side) - curve should go left then right
      cp1x = start.x - controlPointOffset;
      if (isPreview) {
        // For preview, mouse should be approached from opposite direction (right side)
        cp2x = end.x + controlPointOffset;
      } else {
        // For actual connection, end is an output, so curve should approach from left
        cp2x = end.x + controlPointOffset;
      }
    } else {
      // Starting from output node (right side) - curve should go right then left
      cp1x = start.x + controlPointOffset;
      if (isPreview) {
        // For preview, mouse should be approached from opposite direction (left side)
        cp2x = end.x - controlPointOffset;
      } else {
        // For actual connection, end is an input, so curve should approach from right
        cp2x = end.x - controlPointOffset;
      }
    }

    const cp1y = start.y;
    const cp2y = end.y;

    return `M ${start.x},${start.y} C ${cp1x},${cp1y} ${cp2x},${cp2y} ${end.x},${end.y}`;
  };

  // Determine if a node is an input or output
  const getNodeDirection = (nodeId: string): 'input' | 'output' => {
    // Node IDs are in format "NXXXX" where the type is stored in the DOM element
    const nodeElement = document.querySelector(`[data-node-id="${nodeId}"]`);
    const direction = nodeElement?.getAttribute('data-node-direction');
    return (direction as 'input' | 'output') || 'output';
  };

  // Calculate connection paths directly for better real-time updates
  const connectionPaths = connections.map(connection => {
    const startPos = getNodePosition(connection.from_node_id);
    const endPos = getNodePosition(connection.to_node_id);

    if (!startPos || !endPos) return null;

    return {
      id: `${connection.from_node_id}-${connection.to_node_id}`,
      path: generateBezierPath(startPos, endPos, 'output', false),
      color: getTypeColor(getNodeType(connection.from_node_id))
    };
  }).filter(Boolean);

  return (
    <>
      {/* CSS Animation for dashed lines */}
      <style>
        {`
          @keyframes dashAnimation {
            0% {
              stroke-dashoffset: 0;
            }
            100% {
              stroke-dashoffset: -24;
            }
          }
        `}
      </style>

      {/* Connection SVG Layer */}
      <svg
        className="absolute inset-0"
        style={{
          width: '100%',
          height: '100%',
          overflow: 'visible',
          pointerEvents: 'none'
        }}
      >
        {/* SVG Filters and Definitions */}
        <defs>
          <filter id="connectionGlow" x="-100%" y="-100%" width="300%" height="300%">
            <feGaussianBlur stdDeviation="5" result="coloredBlur"/>
            <feMerge>
              <feMergeNode in="coloredBlur"/>
              <feMergeNode in="SourceGraphic"/>
            </feMerge>
          </filter>
        </defs>

        {/* Existing Connections */}
        {connectionPaths.map((connData) => {
          if (!connData) return null;

          // Check if this connection is selected (handle multiple selections)
          const isSelected = selectedConnectionId?.includes(connData.id) || false;

          return (
            <g key={connData.id}>
              {isSelected ? (
                <>
                  {/* Glow effect for selected connection */}
                  <path
                    d={connData.path}
                    stroke={connData.color}
                    strokeWidth="8"
                    fill="none"
                    strokeLinecap="round"
                    opacity="0.4"
                    filter="url(#connectionGlow)"
                  />
                  {/* Main connection path with animated dashes */}
                  <path
                    d={connData.path}
                    stroke={connData.color}
                    strokeWidth="3"
                    fill="none"
                    strokeLinecap="round"
                    strokeDasharray="8,4"
                    style={{
                      animation: 'dashAnimation 2s linear infinite',
                      pointerEvents: 'all',
                      cursor: 'pointer'
                    }}
                    onClick={(e) => {
                      e.stopPropagation();
                      console.log('Selected connection clicked:', connData.id);
                      onConnectionClick(connData.id);
                    }}
                  />
                </>
              ) : (
                /* Normal connection path */
                <path
                  d={connData.path}
                  stroke={connData.color}
                  strokeWidth="2"
                  fill="none"
                  strokeLinecap="round"
                  style={{ pointerEvents: 'all', cursor: 'pointer' }}
                  onClick={(e) => {
                    e.stopPropagation();
                    console.log('Connection clicked:', connData.id);
                    onConnectionClick(connData.id);
                  }}
                />
              )}
              {/* Invisible thicker path for easier clicking */}
              <path
                d={connData.path}
                stroke="transparent"
                strokeWidth="6"
                fill="none"
                strokeLinecap="round"
                style={{ pointerEvents: 'all', cursor: 'pointer' }}
                onClick={(e) => {
                  e.stopPropagation();
                  console.log('Invisible path clicked:', connData.id);
                  onConnectionClick(connData.id);
                }}
              />
            </g>
          );
        })}

        {/* Preview Connection */}
        {startingConnection && (() => {
          const startPos = getNodePosition(startingConnection.nodeId);
          if (!startPos) return null;

          const startingNodeType = getNodeType(startingConnection.nodeId);
          const previewColor = getTypeColor(startingNodeType);

          return (
            <path
              d={generateBezierPath(
                startPos,
                currentMousePosition,
                startingConnection.nodeType,
                true  // This is a preview
              )}
              stroke={previewColor}
              strokeWidth="2"
              fill="none"
              strokeLinecap="round"
              strokeDasharray="5,5"
            />
          );
        })()}
      </svg>
    </>
  );
};