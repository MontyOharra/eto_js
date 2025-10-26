/**
 * NodeRow Component
 * Displays an individual input or output pin row
 */

import React, { useRef, useEffect } from 'react';
import { Handle, Position } from '@xyflow/react';
import { NodePin } from '../../../../../types/moduleTypes';
import { TYPE_COLORS } from '../../../../../utils/pipeline/moduleUtils';
import { TypeIndicator } from './TypeIndicator';

export interface NodeRowProps {
  node: NodePin;
  direction: 'input' | 'output';
  moduleId: string;
  canRemove: boolean;
  onTypeChange: (nodeId: string, newType: string) => void;
  onNameChange: (nodeId: string, newName: string) => void;
  onRemove?: () => void;
  getConnectedOutputName?: (inputNodeId: string) => string | undefined;
  highlightedTypeVar: string | null;
  onTypeVarFocus: (typeVar: string | null) => void;
  onTextFocus?: () => void;
  onTextBlur?: () => void;
  onHandleClick?: (nodeId: string, handleId: string, handleType: 'source' | 'target') => void;
  pendingConnection?: {
    sourceHandleId: string;
    sourceNodeId: string;
    handleType: 'source' | 'target';
  } | null;
  getEffectiveAllowedTypes?: (moduleId: string, pinId: string, baseAllowedTypes: string[]) => string[];
  executionMode?: boolean;
  executionValue?: { value: any; type: string; name: string };
}

export function NodeRow({
  node,
  direction,
  moduleId,
  canRemove,
  onTypeChange,
  onNameChange,
  onRemove,
  getConnectedOutputName,
  highlightedTypeVar,
  onTypeVarFocus,
  onTextFocus,
  onTextBlur,
  onHandleClick,
  pendingConnection,
  getEffectiveAllowedTypes,
  executionMode = false,
  executionValue,
}: NodeRowProps) {
  const isHighlighted = node.type_var && node.type_var === highlightedTypeVar;
  const handleColor = TYPE_COLORS[node.type] || '#6B7280';

  // Format execution value for display
  const formatExecutionValue = (value: any): string => {
    if (value === null) return 'null';
    if (value === undefined) return 'undefined';
    if (typeof value === 'string') return `"${value.length > 20 ? value.substring(0, 20) + '...' : value}"`;
    if (typeof value === 'number') return value.toString();
    if (typeof value === 'boolean') return value.toString();
    if (typeof value === 'object') return JSON.stringify(value).substring(0, 20) + '...';
    return String(value);
  };

  // Check if this handle is the source of the pending connection
  const isPendingSource = pendingConnection?.sourceHandleId === node.node_id;

  // Handle click
  const handleClick = (e: React.MouseEvent) => {
    e.stopPropagation();
    if (onHandleClick) {
      const handleType = direction === 'input' ? 'target' : 'source';
      onHandleClick(moduleId, node.node_id, handleType);
    }
  };

  // For input nodes, display connected output name or "Not Connected"
  const connectedOutputName = direction === 'input' ? getConnectedOutputName?.(node.node_id) : undefined;
  const displayName =
    direction === 'input'
      ? connectedOutputName !== undefined
        ? connectedOutputName
        : 'Not Connected'
      : node.name || '';

  // Ref for input textarea to auto-resize
  const inputTextareaRef = useRef<HTMLTextAreaElement>(null);

  // Auto-resize input textarea when displayName changes
  useEffect(() => {
    if (inputTextareaRef.current && direction === 'input') {
      inputTextareaRef.current.style.height = 'auto';
      inputTextareaRef.current.style.height = inputTextareaRef.current.scrollHeight + 'px';
    }
  }, [displayName, direction]);

  return (
    <div className="relative flex items-center gap-2 py-1.5">
      {/* Connection Handle - Centered on outer edge */}
      <Handle
        type={direction === 'input' ? 'target' : 'source'}
        position={direction === 'input' ? Position.Left : Position.Right}
        id={node.node_id}
        className="!w-5 !h-5 !border-3 !border-gray-900 !cursor-pointer"
        style={{
          [direction === 'input' ? 'left' : 'right']: -13,
          backgroundColor: handleColor,
        }}
        data-handleid={node.node_id}
        onClick={handleClick}
      />

      {/* Node Content - Mirrored layout based on direction */}
      {direction === 'input' ? (
        // Input layout: [handle] name - delete - type (type and delete only show in edit mode)
        <div className="flex items-center w-full gap-2">
          <div className={`${executionMode || !canRemove ? 'flex-1' : 'flex-[2]'} min-w-0 nodrag flex items-center ${executionMode ? 'justify-center' : ''}`}>
            <div className={`text-sm text-gray-300 px-1.5 py-0.5 w-full min-h-[24px] flex items-center ${executionMode ? 'justify-center' : ''}`}>
              {displayName}
            </div>
          </div>
          {!executionMode && (
            <div className="flex-shrink-0">
              <button
                onClick={canRemove && onRemove ? onRemove : undefined}
                className={`p-0.5 rounded transition-colors ${
                  canRemove && onRemove
                    ? 'text-gray-500 hover:text-red-400 hover:bg-red-900 cursor-pointer'
                    : 'invisible cursor-default'
                }`}
                title={canRemove ? 'Remove node' : ''}
                disabled={!canRemove || !onRemove}
              >
                <svg className="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                </svg>
              </button>
            </div>
          )}
          {!executionMode && (
            <div className="flex-shrink-0 w-12 flex items-center">
              <TypeIndicator
                node={node}
                onTypeChange={onTypeChange}
                onFocus={() => onTypeVarFocus(node.type_var || null)}
                onBlur={() => onTypeVarFocus(null)}
                isHighlighted={!!isHighlighted}
                effectiveAllowedTypes={getEffectiveAllowedTypes?.(moduleId, node.node_id, node.allowed_types || [])}
              />
            </div>
          )}
        </div>
      ) : (
        // Output layout: type - delete - name [handle] (type and delete only show in edit mode)
        <div className="flex items-center w-full gap-2">
          {!executionMode && (
            <div className="flex-shrink-0 w-12 flex items-center">
              <TypeIndicator
                node={node}
                onTypeChange={onTypeChange}
                onFocus={() => onTypeVarFocus(node.type_var || null)}
                onBlur={() => onTypeVarFocus(null)}
                isHighlighted={!!isHighlighted}
                effectiveAllowedTypes={getEffectiveAllowedTypes?.(moduleId, node.node_id, node.allowed_types || [])}
              />
            </div>
          )}
          {!executionMode && (
            <div className="flex-shrink-0">
              <button
                onClick={canRemove && onRemove ? onRemove : undefined}
                className={`p-0.5 rounded transition-colors ${
                  canRemove && onRemove
                    ? 'text-gray-500 hover:text-red-400 hover:bg-red-900 cursor-pointer'
                    : 'invisible cursor-default'
                }`}
                title={canRemove ? 'Remove node' : ''}
                disabled={!canRemove || !onRemove}
              >
                <svg className="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                </svg>
              </button>
            </div>
          )}
          <div className={`${executionMode || !canRemove ? 'flex-1' : 'flex-[2]'} min-w-0 nodrag flex items-center ${executionMode ? 'justify-center' : ''}`}>
            {executionMode ? (
              <div className="text-sm text-gray-300 px-1.5 py-0.5 w-full min-h-[24px] flex items-center justify-center">
                {node.name}
              </div>
            ) : (
              <textarea
                value={node.name}
                onChange={(e) => onNameChange(node.node_id, e.target.value)}
                onFocus={onTextFocus}
                onBlur={onTextBlur}
                placeholder="Node name"
                className="w-full text-sm bg-gray-700 text-gray-200 px-1.5 py-0.5 rounded border border-gray-600 focus:outline-none focus:ring-1 focus:ring-blue-500 resize-none overflow-hidden min-h-[24px] nodrag"
                rows={1}
                onInput={(e) => {
                  const target = e.target as HTMLTextAreaElement;
                  target.style.height = 'auto';
                  target.style.height = target.scrollHeight + 'px';
                }}
              />
            )}
          </div>
        </div>
      )}
    </div>
  );
}
