import React from 'react';

// Types
interface NodeConnection {
  id: string;
  fromModuleId: string;
  fromOutputIndex: number;
  toModuleId: string;
  toInputIndex: number;
}

interface StartingConnection {
  moduleId: string;
  type: 'input' | 'output';
  index: number;
}

interface ConnectionLayerProps {
  // Connection data
  connections: NodeConnection[];
  selectedConnectionId: string | null;
  startingConnection: StartingConnection | null;
  currentMousePosition: { x: number; y: number };
  
  // Helper functions
  getNodePosition: (moduleId: string, nodeType: 'input' | 'output', nodeIndex: number) => { x: number; y: number };
  getNodeType: (moduleId: string, nodeType: 'input' | 'output', nodeIndex: number) => string;
  getTypeColor: (type: string) => string;
  generateBezierPath: (start: { x: number; y: number }, end: { x: number; y: number }, startType?: 'input' | 'output') => string;
  
  // Event handlers
  onConnectionClick: (connectionId: string) => (e: React.MouseEvent) => void;
}

export const ConnectionLayer: React.FC<ConnectionLayerProps> = ({
  connections,
  selectedConnectionId,
  startingConnection,
  currentMousePosition,
  getNodePosition,
  getNodeType,
  getTypeColor,
  generateBezierPath,
  onConnectionClick
}) => {
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

      {/* Connection SVG Layer - Behind modules */}
      <svg
        className="absolute inset-0"
        style={{
          width: '100%',
          height: '100%',
          overflow: 'visible',
          pointerEvents: 'auto', // Allow pointer events for connection selection
          zIndex: 1 // Behind modules
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
        {connections.map((connection) => {
          const startPos = getNodePosition(connection.fromModuleId, 'output', connection.fromOutputIndex);
          const endPos = getNodePosition(connection.toModuleId, 'input', connection.toInputIndex);
          const path = generateBezierPath(startPos, endPos);
          
          // Get color from the output node type (source of the connection)
          const outputNodeType = getNodeType(connection.fromModuleId, 'output', connection.fromOutputIndex);
          const connectionColor = getTypeColor(outputNodeType);
          const isSelected = selectedConnectionId === connection.id;
          
          
          return (
            <g key={connection.id}>
              {isSelected ? (
                <>
                  {/* Glow effect for selected connection */}
                  <path
                    d={path}
                    stroke={connectionColor}
                    strokeWidth="8"
                    fill="none"
                    strokeLinecap="round"
                    pointerEvents="none"
                    opacity="0.4"
                    filter="url(#connectionGlow)"
                  />
                  {/* Main connection path with animated dashes */}
                  <path
                    d={path}
                    stroke={connectionColor}
                    strokeWidth="3"
                    fill="none"
                    strokeLinecap="round"
                    strokeDasharray="8,4"
                    style={{ 
                      cursor: 'pointer',
                      animation: 'dashAnimation 2s linear infinite'
                    }}
                    onClick={onConnectionClick(connection.id)}
                    onMouseDown={(e) => e.stopPropagation()}
                  />
                </>
              ) : (
                /* Normal connection path */
                <path
                  d={path}
                  stroke={connectionColor}
                  strokeWidth="2"
                  fill="none"
                  strokeLinecap="round"
                  style={{ cursor: 'pointer' }}
                  onClick={onConnectionClick(connection.id)}
                  onMouseDown={(e) => e.stopPropagation()}
                />
              )}
              {/* Invisible thicker path for easier clicking */}
              <path
                d={path}
                stroke="transparent"
                strokeWidth="10"
                fill="none"
                strokeLinecap="round"
                style={{ cursor: 'pointer' }}
                onClick={onConnectionClick(connection.id)}
                onMouseDown={(e) => e.stopPropagation()}
              />
            </g>
          )
        })}

        {/* Preview Connection */}
        {startingConnection && (() => {
          const startingNodeType = getNodeType(startingConnection.moduleId, startingConnection.type, startingConnection.index);
          const previewColor = getTypeColor(startingNodeType);
          
          return (
            <path
              d={generateBezierPath(
                getNodePosition(startingConnection.moduleId, startingConnection.type, startingConnection.index),
                currentMousePosition,
                startingConnection.type
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