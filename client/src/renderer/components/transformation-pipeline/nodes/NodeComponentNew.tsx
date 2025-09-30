import React, { useRef, useEffect } from 'react';

interface NodeState {
  id: string;
  name: string;
  type: 'string' | 'number' | 'boolean' | 'datetime';
  description: string;
  required: boolean;
}

interface NodeConnection {
  from_node_id: string;
  to_node_id: string;
}

interface PlacedModule {
  module_instance_id: string;
  inputs: any[];
  outputs: any[];
  config: any;
  module_ref: string;
  module_kind: string;
}

interface NodeComponentProps {
  node: NodeState;
  nodeType: 'input' | 'output';
  nodeIndex: number;
  moduleId: string;
  modulePosition?: { x: number; y: number };
  zoom?: number;
  panOffset?: { x: number; y: number };
  connections?: NodeConnection[];
  placedModules?: PlacedModule[];
  canRemove: boolean;
  allowTypeConfiguration: boolean;
  allowedTypes?: string[]; // New prop for variable types
  onNodeClick?: (moduleId: string, nodeType: 'input' | 'output', nodeIndex: number) => (e: React.MouseEvent) => void;
  onRemove?: (moduleId: string, nodeIndex: number) => void;
  onTypeChange?: (moduleId: string, nodeType: 'input' | 'output', nodeIndex: number, newType: 'string' | 'number' | 'boolean' | 'datetime') => void;
  onPositionUpdate?: (moduleId: string, nodeType: 'input' | 'output', nodeIndex: number, position: { x: number; y: number }) => void;
  onNameChange?: (moduleId: string, nodeType: 'input' | 'output', nodeIndex: number, newName: string) => void;
  getInputDisplayName?: (moduleId: string, nodeIndex: number) => string;
  canChangeType?: (moduleId: string, nodeType: 'input' | 'output', nodeIndex: number) => boolean;
}

const getTypeColor = (type: string): string => {
  switch (type) {
    case 'string': return '#3B82F6'; // Blue
    case 'number': return '#EF4444'; // Red
    case 'boolean': return '#10B981'; // Green
    case 'datetime': return '#8B5CF6'; // Purple
    default: return '#6B7280'; // Gray
  }
};

export const NodeComponentNew: React.FC<NodeComponentProps> = ({
  node,
  nodeType,
  nodeIndex,
  moduleId,
  modulePosition,
  zoom,
  panOffset,
  connections,
  placedModules,
  canRemove,
  allowTypeConfiguration,
  allowedTypes = ['string', 'number', 'boolean', 'datetime'], // Default to all types
  onNodeClick,
  onRemove,
  onTypeChange,
  onPositionUpdate,
  onNameChange,
  getInputDisplayName,
  canChangeType
}) => {
  const circleRef = useRef<HTMLDivElement>(null);

  // Calculate display name for dependency tracking
  const displayName = nodeType === 'input'
    ? (getInputDisplayName ? getInputDisplayName(moduleId, nodeIndex) : (node.name || "Not connected"))
    : node.name;

  // Update position whenever the component renders or moves
  useEffect(() => {
    if (circleRef.current && onPositionUpdate) {
      const rect = circleRef.current.getBoundingClientRect();
      const centerX = rect.left + rect.width / 2;
      const centerY = rect.top + rect.height / 2;

      // Convert to canvas coordinates (accounting for zoom/pan would be handled by parent)
      onPositionUpdate(moduleId, nodeType, nodeIndex, { x: centerX, y: centerY });
    }
  }, [moduleId, nodeType, nodeIndex, onPositionUpdate, modulePosition, zoom, panOffset, connections, placedModules]);

  const handleRemoveClick = (e: React.MouseEvent) => {
    e.stopPropagation();
    onRemove?.(moduleId, nodeIndex);
  };

  const handleTypeChange = (e: React.ChangeEvent<HTMLSelectElement>) => {
    onTypeChange?.(moduleId, nodeType, nodeIndex, e.target.value as any);
  };

  const handleNameChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    onNameChange?.(moduleId, nodeType, nodeIndex, e.target.value);
  };

  // Check if type changing is actually allowed
  const isTypeChangeable = allowTypeConfiguration &&
                           allowedTypes.length > 1 &&
                           (!canChangeType || canChangeType(moduleId, nodeType, nodeIndex));

  if (nodeType === 'input') {
    return (
      <>
        {/* Input Node Circle */}
        <div
          className="absolute left-0 top-1/2 transform -translate-y-1/2 -translate-x-1/2"
          style={{ zIndex: 10 }}
        >
          <div
            ref={circleRef}
            className="w-5 h-5 rounded-full border-2 border-gray-800 cursor-pointer hover:scale-110 transition-transform"
            style={{
              backgroundColor: getTypeColor(node.type),
              pointerEvents: 'all'
            }}
            title={`${node.name} (${node.type}): ${node.description}`}
            onClick={onNodeClick ? onNodeClick(moduleId, nodeType, nodeIndex) : undefined}
            onMouseDown={(e) => {
              e.stopPropagation();
              e.preventDefault();
            }}
            data-node-id={`${moduleId}-input-${nodeIndex}`}
          />
        </div>
        {/* Input Content */}
        <div className="ml-6 flex-1">
          <div className="flex items-center gap-2">
            <span
              className="text-xs text-gray-300 font-medium"
              style={{
                wordBreak: 'break-word',
                overflowWrap: 'break-word',
                hyphens: 'auto'
              }}
            >
              {displayName}
            </span>
            {canRemove && (
              <button
                onClick={handleRemoveClick}
                className="w-3 h-3 flex-shrink-0 text-red-400 hover:text-red-300 transition-colors"
                title="Remove input"
              >
                <svg className="w-full h-full" fill="currentColor" viewBox="0 0 20 20">
                  <path fillRule="evenodd" d="M4.293 4.293a1 1 0 011.414 0L10 8.586l4.293-4.293a1 1 0 111.414 1.414L11.414 10l4.293 4.293a1 1 0 01-1.414 1.414L10 11.414l-4.293 4.293a1 1 0 01-1.414-1.414L8.586 10 4.293 5.707a1 1 0 010-1.414z" clipRule="evenodd" />
                </svg>
              </button>
            )}
          </div>
          {isTypeChangeable && (
            <select
              value={node.type}
              onChange={handleTypeChange}
              onMouseDown={(e) => e.stopPropagation()}
              className="text-xs bg-gray-700 border border-gray-600 text-gray-300 rounded px-1 py-0.5 focus:outline-none focus:ring-1 focus:ring-blue-500 mt-1"
              title={allowedTypes.length === 1 ? 'Type is fixed' : 'Change node type'}
            >
              {allowedTypes.map(type => (
                <option key={type} value={type}>
                  {type}
                </option>
              ))}
            </select>
          )}
          {/* Show type badge if not changeable but types are variable */}
          {!isTypeChangeable && allowTypeConfiguration && allowedTypes.length > 1 && (
            <span className="text-xs bg-gray-700 text-gray-400 px-1.5 py-0.5 rounded mt-1 inline-block">
              {node.type}
            </span>
          )}
        </div>
      </>
    );
  } else {
    return (
      <>
        {/* Output Content */}
        <div className="mr-6 flex-1 text-right">
          <div className="flex items-center justify-end gap-2">
            <input
              type="text"
              value={node.name || ''}
              onChange={handleNameChange}
              onMouseDown={(e) => e.stopPropagation()}
              onFocus={(e) => e.stopPropagation()}
              onClick={(e) => e.stopPropagation()}
              className="text-xs bg-gray-700 border border-gray-600 text-gray-300 rounded px-1 py-0.5 focus:outline-none focus:ring-1 focus:ring-blue-500 min-w-0 text-right max-w-24"
              placeholder="Output name"
            />
            {canRemove && (
              <button
                onClick={handleRemoveClick}
                className="w-3 h-3 flex-shrink-0 text-red-400 hover:text-red-300 transition-colors"
                title="Remove output"
              >
                <svg className="w-full h-full" fill="currentColor" viewBox="0 0 20 20">
                  <path fillRule="evenodd" d="M4.293 4.293a1 1 0 011.414 0L10 8.586l4.293-4.293a1 1 0 111.414 1.414L11.414 10l4.293 4.293a1 1 0 01-1.414 1.414L10 11.414l-4.293 4.293a1 1 0 01-1.414-1.414L8.586 10 4.293 5.707a1 1 0 010-1.414z" clipRule="evenodd" />
                </svg>
              </button>
            )}
          </div>
          {isTypeChangeable && (
            <select
              value={node.type}
              onChange={handleTypeChange}
              onMouseDown={(e) => e.stopPropagation()}
              className="text-xs bg-gray-700 border border-gray-600 text-gray-300 rounded px-1 py-0.5 focus:outline-none focus:ring-1 focus:ring-blue-500 mt-1"
              title={allowedTypes.length === 1 ? 'Type is fixed' : 'Change node type'}
            >
              {allowedTypes.map(type => (
                <option key={type} value={type}>
                  {type}
                </option>
              ))}
            </select>
          )}
          {/* Show type badge if not changeable but types are variable */}
          {!isTypeChangeable && allowTypeConfiguration && allowedTypes.length > 1 && (
            <span className="text-xs bg-gray-700 text-gray-400 px-1.5 py-0.5 rounded mt-1 inline-block">
              {node.type}
            </span>
          )}
        </div>
        {/* Output Node Circle */}
        <div
          className="absolute right-0 top-1/2 transform -translate-y-1/2 translate-x-1/2"
          style={{ zIndex: 10 }}
        >
          <div
            ref={circleRef}
            className="w-5 h-5 rounded-full border-2 border-gray-800 cursor-pointer hover:scale-110 transition-transform"
            style={{
              backgroundColor: getTypeColor(node.type),
              pointerEvents: 'all'
            }}
            title={`${node.name} (${node.type}): ${node.description}`}
            onClick={onNodeClick ? onNodeClick(moduleId, nodeType, nodeIndex) : undefined}
            onMouseDown={(e) => {
              e.stopPropagation();
              e.preventDefault();
            }}
            data-node-id={`${moduleId}-output-${nodeIndex}`}
          />
        </div>
      </>
    );
  }
};