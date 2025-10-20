/**
 * TypeIndicator Component
 * Displays and allows selection of node pin types
 */

import { useState } from 'react';
import { NodePin } from '../../../../../types/moduleTypes';
import { getTypeColor } from '../../../utils/edgeUtils';

export interface TypeIndicatorProps {
  node: NodePin;
  onTypeChange: (nodeId: string, newType: string) => void;
  onFocus: () => void;
  onBlur: () => void;
  isHighlighted: boolean;
  effectiveAllowedTypes?: string[]; // Types available based on connections
}

export function TypeIndicator({
  node,
  onTypeChange,
  onFocus,
  onBlur,
  isHighlighted,
  effectiveAllowedTypes,
}: TypeIndicatorProps) {
  const [isHighlightActive, setIsHighlightActive] = useState(false);

  // Get available types from node's allowed_types, or all types if not specified
  const availableTypes = node.allowed_types || ['str', 'int', 'float', 'bool', 'datetime'];

  // Use effective types if provided (for showing disabled options), otherwise use available types
  const effectiveTypes = effectiveAllowedTypes || availableTypes;

  const highlightStyle = isHighlighted
    ? {
        boxShadow: 'inset 0 0 0 2px #ffffff',
      }
    : {};

  const handleClick = () => {
    if (isHighlightActive) {
      onBlur();
      setIsHighlightActive(false);
    } else {
      onFocus();
      setIsHighlightActive(true);
    }
  };

  const handleBlur = () => {
    onBlur();
    setIsHighlightActive(false);
  };

  // If only one type is available, show static display
  if (availableTypes.length === 1) {
    return (
      <div
        className="w-full text-[9px] px-0.5 py-0.5 rounded border border-gray-600 min-h-[24px] flex items-center justify-center"
        style={{
          backgroundColor: getTypeColor(node.type),
          color: '#FFFFFF',
          ...highlightStyle,
        }}
      >
        {node.type}
      </div>
    );
  }

  // Dropdown with disabled options for types not in effectiveTypes
  return (
    <select
      value={node.type}
      onChange={(e) => onTypeChange(node.node_id, e.target.value)}
      onClick={handleClick}
      onBlur={handleBlur}
      className="w-full text-[9px] text-white px-0.5 py-0.5 rounded border border-gray-600 focus:outline-none focus:ring-1 focus:ring-blue-500 min-h-[24px]"
      style={{
        backgroundColor: getTypeColor(node.type),
        ...highlightStyle,
      }}
    >
      {availableTypes.map((type) => {
        const isDisabled = !effectiveTypes.includes(type);
        return (
          <option
            key={type}
            value={type}
            disabled={isDisabled}
            className={isDisabled ? 'text-gray-500' : ''}
          >
            {type}
          </option>
        );
      })}
    </select>
  );
}
