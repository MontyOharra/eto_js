import React from 'react';
import { EntryPoint } from '../../../types/pipelineTypes';

interface EntryPointComponentProps {
  entryPoint: EntryPoint;
  position: { x: number; y: number };
  isSelected: boolean;
  onSelect: (nodeId: string) => void;
  onMouseDown: (e: React.MouseEvent) => void;
  onDelete: (nodeId: string) => void;
  onNameChange: (nodeId: string, name: string) => void;
  onNodeClick?: (nodeId: string) => void;
}

export const EntryPointComponent: React.FC<EntryPointComponentProps> = ({
  entryPoint,
  position,
  isSelected,
  onSelect,
  onMouseDown,
  onDelete,
  onNameChange,
  onNodeClick
}) => {
  const borderColor = isSelected ? '#60A5FA' : '#4B5563';

  return (
    <div
      className="absolute bg-gray-800 rounded-lg shadow-lg border-2 select-none"
      style={{
        left: `${position.x}px`,
        top: `${position.y}px`,
        minWidth: '160px',
        width: 'max-content',
        maxWidth: '240px',
        transform: 'translate(-50%, 0)',
        borderColor,
        userSelect: 'none',
        WebkitUserSelect: 'none',
        MozUserSelect: 'none',
        msUserSelect: 'none'
      }}
      onClick={(e) => {
        e.stopPropagation();
        onSelect(entryPoint.node_id);
      }}
      onMouseDown={(e) => {
        e.stopPropagation();
        onMouseDown(e);
      }}
    >
      {/* Header */}
      <div
        className="px-3 py-2 rounded-t-lg flex items-center justify-between"
        style={{ backgroundColor: '#FFFFFF' }} // White color for entry points
      >
        <span className="text-xs font-semibold text-black">Entry Point</span>
        <button
          onClick={(e) => {
            e.stopPropagation();
            onDelete(entryPoint.node_id);
          }}
          className="w-4 h-4 text-gray-600 hover:text-red-500 transition-colors"
        >
          <svg className="w-full h-full" fill="currentColor" viewBox="0 0 20 20">
            <path fillRule="evenodd" d="M4.293 4.293a1 1 0 011.414 0L10 8.586l4.293-4.293a1 1 0 111.414 1.414L11.414 10l4.293 4.293a1 1 0 01-1.414 1.414L10 11.414l-4.293 4.293a1 1 0 01-1.414-1.414L8.586 10 4.293 5.707a1 1 0 010-1.414z" clipRule="evenodd" />
          </svg>
        </button>
      </div>

      {/* Body - Single row for output */}
      <div className="flex border-b border-gray-700 last:border-b-0 min-h-12">
        {/* Empty left half (no inputs) */}
        <div className="flex-1 px-3 py-2" />

        {/* Output Half */}
        <div className="flex-1 flex items-center justify-end relative px-3 py-2">
          {/* Output Content */}
          <div className="mr-3 flex-1 text-right">
            <div className="flex items-center justify-end gap-2">
              <textarea
                value={entryPoint.name}
                onChange={(e) => onNameChange(entryPoint.node_id, e.target.value)}
                onKeyDown={(e) => {
                  // Prevent Enter from creating new line, use Shift+Enter for new line
                  if (e.key === 'Enter' && !e.shiftKey) {
                    e.preventDefault();
                    (e.target as HTMLTextAreaElement).blur();
                  }
                }}
                onClick={(e) => e.stopPropagation()}
                onMouseDown={(e) => e.stopPropagation()}
                className="text-xs bg-gray-700 border border-gray-600 text-gray-300 rounded px-1 py-0.5 focus:outline-none focus:ring-1 focus:ring-blue-500 w-full text-right resize-none overflow-hidden"
                style={{
                  minHeight: '20px',
                  height: 'auto'
                }}
                rows={1}
                onInput={(e) => {
                  const target = e.target as HTMLTextAreaElement;
                  target.style.height = 'auto';
                  target.style.height = target.scrollHeight + 'px';
                }}
              />
            </div>
            {/* Fixed type badge */}
            <div className="text-right mt-1">
              <span className="text-xs bg-gray-700 text-gray-400 px-1.5 py-0.5 rounded inline-block">
                string
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
                backgroundColor: '#3B82F6', // Blue for string type
                pointerEvents: 'all'
              }}
              title={`${entryPoint.name} (string)`}
              onClick={(e) => {
                e.stopPropagation();
                onNodeClick?.(entryPoint.node_id);
              }}
              onMouseDown={(e) => {
                e.stopPropagation();
                e.preventDefault();
              }}
              data-node-id={entryPoint.node_id}
              data-node-direction="output"
              data-module-id={`entry-${entryPoint.node_id}`}
            />
          </div>
        </div>
      </div>
    </div>
  );
};