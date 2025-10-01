import React from 'react';
import { NodePin, NodeSpec } from '../../../../types/pipelineTypes';

interface NodeComponentProps {
  node: NodePin;
  nodeSpec: NodeSpec; // Template specification for this node
  side: 'input' | 'output';
  moduleId: string;
  canRemove: boolean;
  onRemove: () => void;
  onNameChange: (newName: string) => void;
  onTypeChange?: (newType: string) => void; // Callback for type changes
  onClick: () => void;
  connectedOutputName?: string;
  getTypeColor: (type: string) => string;
}

export const NodeComponent: React.FC<NodeComponentProps> = ({
  node,
  nodeSpec,
  side,
  moduleId,
  canRemove,
  onRemove,
  onNameChange,
  onTypeChange,
  onClick,
  connectedOutputName,
  getTypeColor
}) => {
  const isInput = side === 'input';

  const handleNameChange = (e: React.ChangeEvent<HTMLTextAreaElement>) => {
    onNameChange(e.target.value);
  };

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    // Prevent Enter from creating new line, use Shift+Enter for new line
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      (e.target as HTMLTextAreaElement).blur();
    }
  };

  const handleTextareaInput = (e: React.FormEvent<HTMLTextAreaElement>) => {
    const target = e.target as HTMLTextAreaElement;
    target.style.height = 'auto';
    target.style.height = target.scrollHeight + 'px';
  };

  // Get available types from NodeSpec and convert to display names
  const rawTypes = nodeSpec.typing.allowed_types || [];
  const availableTypes = rawTypes.map(convertTypeToDisplayName);
  const hasMultipleTypes = availableTypes.length > 1;
  const isTypeVariable = !!nodeSpec.typing.type_var;

  // Convert backend type names to display names
  function convertTypeToDisplayName(type: string): string {
    switch (type) {
      case 'str': return 'string';
      case 'bool': return 'boolean';
      case 'int': return 'integer';
      case 'float': return 'float';
      default: return type; // datetime, etc. stay as-is
    }
  }

  // Convert display name back to backend type for onChange
  function convertDisplayNameToType(displayName: string): string {
    switch (displayName) {
      case 'string': return 'str';
      case 'boolean': return 'bool';
      case 'integer': return 'int';
      case 'float': return 'float';
      default: return displayName;
    }
  }

  // Get current display name for the node's type
  const currentDisplayType = convertTypeToDisplayName(node.type);

  // Render type selector or static indicator
  const renderTypeSelector = () => {
    if (hasMultipleTypes) {
      return (
        <select
          value={currentDisplayType}
          onChange={(e) => {
            if (onTypeChange) {
              // Convert display name back to backend type
              const backendType = convertDisplayNameToType(e.target.value);
              onTypeChange(backendType);
            }
          }}
          onClick={(e) => e.stopPropagation()}
          onMouseDown={(e) => e.stopPropagation()}
          className="text-xs bg-gray-700 border border-gray-600 text-gray-300 rounded px-1 py-0.5 focus:outline-none focus:ring-1 focus:ring-blue-500 w-20 text-center h-6"
        >
          {availableTypes.map(displayType => (
            <option key={displayType} value={displayType}>{displayType}</option>
          ))}
        </select>
      );
    } else {
      return (
        <span className={`text-xs bg-gray-700 text-gray-400 px-1 py-0.5 rounded w-20 text-center inline-block h-6 flex items-center justify-center ${isTypeVariable ? 'border border-blue-400' : 'border border-gray-600'}`}>
          {isTypeVariable ? nodeSpec.typing.type_var : (availableTypes[0] || currentDisplayType)}
        </span>
      );
    }
  };

  if (isInput) {
    return (
      <div className="flex items-center px-3 py-2 relative">
        {/* Input Node Circle - positioned on left border */}
        <div
          className="absolute left-0 top-1/2 transform -translate-y-1/2 -translate-x-1/2"
          style={{ zIndex: 10 }}
        >
          <div
            className="w-5 h-5 rounded-full border-2 border-gray-800 cursor-pointer hover:scale-110 transition-transform"
            style={{
              backgroundColor: getTypeColor(node.type),
              pointerEvents: 'all'
            }}
            title={`${node.name} (${node.type})`}
            onClick={(e) => {
              e.stopPropagation();
              onClick();
            }}
            onMouseDown={(e) => {
              e.stopPropagation();
              e.preventDefault();
            }}
            data-node-id={node.node_id}
            data-node-direction="input"
            data-module-id={moduleId}
          />
        </div>

        {/* Input Content: 50% name, 50% type */}
        <div className="ml-3 flex-1 flex items-stretch">
          {/* Name section (50%) */}
          <div className="flex-1 flex items-center pr-2">
            <div className="text-xs text-gray-300 leading-tight break-words hyphens-auto" style={{ wordBreak: 'break-word' }}>
              {connectedOutputName || 'Not Connected'}
            </div>
          </div>

          {/* Type section (50%) */}
          <div className="flex-1 flex items-center justify-center gap-1">
            {renderTypeSelector()}
            <button
              onClick={canRemove ? onRemove : undefined}
              className={`w-3 h-3 transition-colors flex-shrink-0 ${
                canRemove
                  ? 'text-gray-500 hover:text-red-400 cursor-pointer'
                  : 'text-transparent cursor-default'
              }`}
              title={canRemove ? "Remove input" : ""}
              disabled={!canRemove}
            >
              <svg className="w-full h-full" fill="currentColor" viewBox="0 0 20 20">
                <path fillRule="evenodd" d="M4.293 4.293a1 1 0 011.414 0L10 8.586l4.293-4.293a1 1 0 111.414 1.414L11.414 10l4.293 4.293a1 1 0 01-1.414 1.414L10 11.414l-4.293 4.293a1 1 0 01-1.414-1.414L8.586 10 4.293 5.707a1 1 0 010-1.414z" clipRule="evenodd" />
              </svg>
            </button>
          </div>
        </div>
      </div>
    );
  } else {
    return (
      <div className="flex items-center px-3 py-2 relative">
        {/* Output Content: 50% type, 50% name */}
        <div className="mr-3 flex-1 flex items-stretch">
          {/* Type section (50%) */}
          <div className="flex-1 flex items-center gap-1">
            <button
              onClick={canRemove ? onRemove : undefined}
              className={`w-3 h-3 transition-colors flex-shrink-0 ${
                canRemove
                  ? 'text-gray-500 hover:text-red-400 cursor-pointer'
                  : 'text-transparent cursor-default'
              }`}
              title={canRemove ? "Remove output" : ""}
              disabled={!canRemove}
            >
              <svg className="w-full h-full" fill="currentColor" viewBox="0 0 20 20">
                <path fillRule="evenodd" d="M4.293 4.293a1 1 0 011.414 0L10 8.586l4.293-4.293a1 1 0 111.414 1.414L11.414 10l4.293 4.293a1 1 0 01-1.414 1.414L10 11.414l-4.293 4.293a1 1 0 01-1.414-1.414L8.586 10 4.293 5.707a1 1 0 010-1.414z" clipRule="evenodd" />
              </svg>
            </button>
            {renderTypeSelector()}
          </div>

          {/* Name section (50%) */}
          <div className="flex-1 flex items-stretch pl-2">
            <textarea
              value={node.name}
              onChange={handleNameChange}
              onKeyDown={handleKeyDown}
              onClick={(e) => e.stopPropagation()}
              onMouseDown={(e) => e.stopPropagation()}
              className="text-xs bg-gray-700 border border-gray-600 text-gray-300 rounded px-1 py-0.5 focus:outline-none focus:ring-1 focus:ring-blue-500 text-right resize-none w-full leading-tight overflow-hidden"
              style={{
                minHeight: '20px',
                height: 'auto',
                wordBreak: 'break-word'
              }}
              rows={1}
              onInput={handleTextareaInput}
            />
          </div>
        </div>

        {/* Output Node Circle - positioned on right border */}
        <div
          className="absolute right-0 top-1/2 transform -translate-y-1/2 translate-x-1/2"
          style={{ zIndex: 10 }}
        >
          <div
            className="w-5 h-5 rounded-full border-2 border-gray-800 cursor-pointer hover:scale-110 transition-transform"
            style={{
              backgroundColor: getTypeColor(node.type),
              pointerEvents: 'all'
            }}
            title={`${node.name} (${node.type})`}
            onClick={(e) => {
              e.stopPropagation();
              onClick();
            }}
            onMouseDown={(e) => {
              e.stopPropagation();
              e.preventDefault();
            }}
            data-node-id={node.node_id}
            data-node-direction="output"
            data-module-id={moduleId}
          />
        </div>
      </div>
    );
  }
};