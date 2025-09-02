import React from 'react';
import { BaseModuleTemplate, ModuleInput, ModuleOutput } from '../data/testModules';

interface ModuleComponentProps {
  module: BaseModuleTemplate;
  position: { x: number; y: number };
  onConfigChange?: (config: any) => void;
  isSelected?: boolean;
  onClick?: (e: React.MouseEvent) => void;
  onMouseDown?: (e: React.MouseEvent) => void;
}

export const ModuleComponent: React.FC<ModuleComponentProps> = ({
  module,
  position,
  onConfigChange,
  isSelected = false,
  onClick,
  onMouseDown
}) => {
  const getTypeColor = (type: string) => {
    switch (type) {
      case 'string': return '#3B82F6'; // Blue
      case 'number': return '#10B981'; // Green  
      case 'boolean': return '#8B5CF6'; // Purple
      case 'array': return '#F59E0B'; // Orange
      case 'object': return '#EF4444'; // Red
      case 'file': return '#6B7280'; // Gray
      default: return '#9CA3AF'; // Default gray
    }
  };

  const renderConnectionPoint = (
    type: 'input' | 'output', 
    item: ModuleInput | ModuleOutput, 
    index: number
  ) => {
    const isInput = type === 'input';
    const color = getTypeColor(item.type);
    
    return (
      <div
        key={`${type}-${index}`}
        className={`absolute ${isInput ? '-left-2' : '-right-2'} w-4 h-4 rounded-full border-2 border-gray-800 transition-all duration-200 hover:scale-125 cursor-pointer group`}
        style={{ 
          backgroundColor: color,
          top: `${60 + index * 28}px`,
          zIndex: 10
        }}
        title={`${item.name} (${item.type})`}
      >
        {/* Connection point tooltip */}
        <div className={`absolute ${isInput ? 'left-6' : 'right-6'} top-1/2 transform -translate-y-1/2 bg-gray-800 text-white text-xs rounded px-2 py-1 opacity-0 group-hover:opacity-100 transition-opacity duration-200 pointer-events-none whitespace-nowrap z-20`}>
          <div className="font-medium">{item.name}</div>
          <div className="text-gray-400">{item.type}</div>
          <div className="text-gray-300 text-xs">{item.description}</div>
        </div>
      </div>
    );
  };

  const moduleHeight = Math.max(
    120, // Minimum height
    60 + Math.max(module.inputs.length, module.outputs.length) * 28 + 20 // Dynamic height based on inputs/outputs
  );

  return (
    <div
      className={`absolute bg-gray-800 rounded-lg shadow-lg border-2 transition-all duration-200 cursor-pointer ${
        isSelected 
          ? 'border-blue-400 shadow-blue-400/20' 
          : 'border-gray-600 hover:border-gray-500'
      }`}
      style={{
        left: `${position.x}px`,
        top: `${position.y}px`,
        width: '220px',
        height: `${moduleHeight}px`,
        zIndex: isSelected ? 20 : 10,
      }}
      onClick={onClick}
      onMouseDown={onMouseDown}
    >
      {/* Module Header */}
      <div 
        className="h-12 rounded-t-lg flex items-center px-3 text-white"
        style={{ backgroundColor: module.color }}
      >
        <div className="flex-1">
          <div className="font-medium text-sm truncate">{module.name}</div>
          <div className="text-xs opacity-80">{module.category}</div>
        </div>
        
        {/* Config indicator */}
        {module.config.length > 0 && (
          <div className="w-5 h-5 bg-white bg-opacity-20 rounded flex items-center justify-center">
            <svg className="w-3 h-3" fill="currentColor" viewBox="0 0 20 20">
              <path fillRule="evenodd" d="M11.49 3.17c-.38-1.56-2.6-1.56-2.98 0a1.532 1.532 0 01-2.286.948c-1.372-.836-2.942.734-2.106 2.106.54.886.061 2.042-.947 2.287-1.561.379-1.561 2.6 0 2.978a1.532 1.532 0 01.947 2.287c-.836 1.372.734 2.942 2.106 2.106a1.532 1.532 0 012.287.947c.379 1.561 2.6 1.561 2.978 0a1.533 1.533 0 012.287-.947c1.372.836 2.942-.734 2.106-2.106a1.533 1.533 0 01.947-2.287c1.561-.379 1.561-2.6 0-2.978a1.532 1.532 0 01-.947-2.287c.836-1.372-.734-2.942-2.106-2.106a1.532 1.532 0 01-2.287-.947zM10 13a3 3 0 100-6 3 3 0 000 6z" clipRule="evenodd" />
            </svg>
          </div>
        )}
      </div>

      {/* Module Body */}
      <div className="px-3 py-2 relative">
        <div className="text-gray-300 text-xs leading-relaxed">
          {module.description}
        </div>
        
        {/* Input/Output Labels */}
        <div className="mt-3 flex justify-between text-xs text-gray-400">
          <div>
            {module.inputs.length > 0 && (
              <span>Inputs ({module.inputs.length})</span>
            )}
          </div>
          <div>
            {module.outputs.length > 0 && (
              <span>Outputs ({module.outputs.length})</span>
            )}
          </div>
        </div>
      </div>

      {/* Input Connection Points */}
      {module.inputs.map((input, index) => 
        renderConnectionPoint('input', input, index)
      )}

      {/* Output Connection Points */}  
      {module.outputs.map((output, index) => 
        renderConnectionPoint('output', output, index)
      )}

      {/* Selection indicator */}
      {isSelected && (
        <div className="absolute -inset-1 border-2 border-blue-400 rounded-lg pointer-events-none animate-pulse" />
      )}
    </div>
  );
};