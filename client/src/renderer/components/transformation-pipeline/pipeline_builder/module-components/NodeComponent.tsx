import React from 'react';
import { NodePin } from '../../../../types/pipelineTypes';

interface NodeComponentProps {
  node: NodePin;
  side: 'input' | 'output';
  moduleId: string;
  canRemove: boolean;
  onRemove: () => void;
  onNameChange: (newName: string) => void;
  onClick: () => void;
  connectedOutputName?: string;
  getTypeColor: (type: string) => string;
}

export const NodeComponent: React.FC<NodeComponentProps> = ({
  node,
  side,
  moduleId,
  canRemove,
  onRemove,
  onNameChange,
  onClick,
  connectedOutputName,
  getTypeColor
}) => {
  const isInput = side === 'input';
  const nodeColor = getTypeColor(node.type);

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

  return (
    <div className="flex border-b border-gray-700 last:border-b-0 min-h-12">
      {/* Input Side */}
      <div className="flex-1 flex items-center relative px-3 py-2">
        {isInput && (
          <>
            {/* Input Node Circle - positioned on border, aligned with content center */}
            <div
              className="absolute left-0 top-1/2 transform -translate-y-1/2 -translate-x-1/2"
              style={{ zIndex: 10 }}
            >
              <div
                className="w-5 h-5 rounded-full border-2 border-gray-800 cursor-pointer hover:scale-110 transition-transform"
                style={{
                  backgroundColor: nodeColor,
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

            {/* Input Content */}
            <div className="ml-3 flex-1">
              <div className="flex items-center gap-2">
                <div className="text-xs text-gray-300">
                  {connectedOutputName || 'Not Connected'}
                </div>
                {canRemove && (
                  <button
                    onClick={onRemove}
                    className="w-3 h-3 text-gray-500 hover:text-red-400 transition-colors"
                    title="Remove input"
                  >
                    <svg className="w-full h-full" fill="currentColor" viewBox="0 0 20 20">
                      <path fillRule="evenodd" d="M4.293 4.293a1 1 0 011.414 0L10 8.586l4.293-4.293a1 1 0 111.414 1.414L11.414 10l4.293 4.293a1 1 0 01-1.414 1.414L10 11.414l-4.293 4.293a1 1 0 01-1.414-1.414L8.586 10 4.293 5.707a1 1 0 010-1.414z" clipRule="evenodd" />
                    </svg>
                  </button>
                )}
              </div>
              {/* Type badge */}
              <div className="mt-1">
                <span className="text-xs bg-gray-700 text-gray-400 px-1.5 py-0.5 rounded inline-block">
                  {node.type}
                </span>
              </div>
            </div>
          </>
        )}
      </div>

      {/* Output Side */}
      <div className="flex-1 flex items-center justify-end relative px-3 py-2">
        {!isInput && (
          <>
            {/* Output Content */}
            <div className="mr-3 flex-1 text-right">
              <div className="flex items-center justify-end gap-2">
                <textarea
                  value={node.name}
                  onChange={handleNameChange}
                  onKeyDown={handleKeyDown}
                  onClick={(e) => e.stopPropagation()}
                  onMouseDown={(e) => e.stopPropagation()}
                  className="text-xs bg-gray-700 border border-gray-600 text-gray-300 rounded px-1 py-0.5 focus:outline-none focus:ring-1 focus:ring-blue-500 w-full text-right resize-none overflow-hidden"
                  style={{
                    minHeight: '20px',
                    height: 'auto'
                  }}
                  rows={1}
                  onInput={handleTextareaInput}
                />
                {canRemove && (
                  <button
                    onClick={onRemove}
                    className="w-3 h-3 text-gray-500 hover:text-red-400 transition-colors"
                    title="Remove output"
                  >
                    <svg className="w-full h-full" fill="currentColor" viewBox="0 0 20 20">
                      <path fillRule="evenodd" d="M4.293 4.293a1 1 0 011.414 0L10 8.586l4.293-4.293a1 1 0 111.414 1.414L11.414 10l4.293 4.293a1 1 0 01-1.414 1.414L10 11.414l-4.293 4.293a1 1 0 01-1.414-1.414L8.586 10 4.293 5.707a1 1 0 010-1.414z" clipRule="evenodd" />
                    </svg>
                  </button>
                )}
              </div>
              {/* Type badge */}
              <div className="text-right mt-1">
                <span className="text-xs bg-gray-700 text-gray-400 px-1.5 py-0.5 rounded inline-block">
                  {node.type}
                </span>
              </div>
            </div>

            {/* Output Node Circle - positioned on border, aligned with content center */}
            <div
              className="absolute right-0 top-1/2 transform -translate-y-1/2 translate-x-1/2"
              style={{ zIndex: 10 }}
            >
              <div
                className="w-5 h-5 rounded-full border-2 border-gray-800 cursor-pointer hover:scale-110 transition-transform"
                style={{
                  backgroundColor: nodeColor,
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
          </>
        )}
      </div>
    </div>
  );
};