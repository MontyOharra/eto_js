import React, { useState, useRef, useEffect } from 'react';
import { BaseModuleTemplate } from '../data/testModules';

interface ExtractedDataModuleComponentProps {
  moduleId: string;
  template: BaseModuleTemplate;
  position: { x: number; y: number };
  config?: Record<string, any>;
  zoom?: number; // Add zoom level
  panOffset?: { x: number; y: number }; // Add pan offset
  onMouseDown?: (e: React.MouseEvent) => void;
  onDelete?: () => void;
  onConfigChange?: (config: Record<string, any>) => void;
  onNodeClick?: (moduleId: string, nodeType: 'input' | 'output', nodeIndex: number) => (e: React.MouseEvent) => void;
  onNodePositionUpdate?: (moduleId: string, nodeType: 'input' | 'output', nodeIndex: number, position: { x: number; y: number }) => void;
}

export const ExtractedDataModuleComponent: React.FC<ExtractedDataModuleComponentProps> = ({
  moduleId,
  template,
  position,
  config = {},
  zoom,
  panOffset,
  onMouseDown,
  onDelete,
  onConfigChange,
  onNodeClick,
  onNodePositionUpdate
}) => {
  const [showDeleteModal, setShowDeleteModal] = useState(false);
  const outputNodeRef = useRef<HTMLDivElement>(null);

  // Update position whenever the module moves
  useEffect(() => {
    if (outputNodeRef.current && onNodePositionUpdate) {
      const rect = outputNodeRef.current.getBoundingClientRect();
      const centerX = rect.left + rect.width / 2;
      const centerY = rect.top + rect.height / 2;
      
      onNodePositionUpdate(moduleId, 'output', 0, { x: centerX, y: centerY });
    }
  }, [moduleId, onNodePositionUpdate, position, zoom, panOffset]);

  const handleDeleteClick = (e: React.MouseEvent) => {
    e.stopPropagation();
    setShowDeleteModal(true);
  };

  const handleConfirmDelete = () => {
    if (onDelete) {
      onDelete();
    }
    setShowDeleteModal(false);
  };

  const handleCancelDelete = () => {
    setShowDeleteModal(false);
  };

  const handleMouseDown = (e: React.MouseEvent) => {
    e.preventDefault();
    if (onMouseDown) {
      onMouseDown(e);
    }
  };

  const handleConfigChange = (configName: string, value: any) => {
    const newConfig = { ...config, [configName]: value };
    if (onConfigChange) {
      onConfigChange(newConfig);
    }
  };

  const testValue = config.test_value || template.config[0]?.defaultValue || '';

  return (
    <div
      className="absolute bg-emerald-50 rounded-lg shadow-lg border-2 border-emerald-500 cursor-pointer select-none"
      style={{
        left: `${position.x}px`,
        top: `${position.y}px`,
        minWidth: '200px',
        width: 'max-content',
        maxWidth: '280px',
        transform: 'translate(-50%, 0)',
        userSelect: 'none',
        WebkitUserSelect: 'none',
        MozUserSelect: 'none',
        msUserSelect: 'none'
      }}
      onMouseDown={handleMouseDown}
    >
      {/* Header */}
      <div 
        className="px-3 py-2 rounded-t-lg flex items-center justify-between gap-2"
        style={{ backgroundColor: template.color }}
      >
        <div className="text-white font-medium text-xs flex-1">{template.name}</div>
        <div className="text-emerald-100 text-xs bg-emerald-600 px-2 py-1 rounded">
          SOURCE
        </div>
        <button
          onClick={handleDeleteClick}
          className="w-5 h-5 flex items-center justify-center text-white hover:bg-red-600 hover:text-white rounded transition-colors"
          title="Delete module"
        >
          <svg className="w-3 h-3" fill="currentColor" viewBox="0 0 20 20">
            <path fillRule="evenodd" d="M9 2a1 1 0 00-.894.553L7.382 4H4a1 1 0 000 2v10a2 2 0 002 2h8a2 2 0 002-2V6a1 1 0 100-2h-3.382l-.724-1.447A1 1 0 0011 2H9zM7 8a1 1 0 012 0v6a1 1 0 11-2 0V8zm5-1a1 1 0 00-1 1v6a1 1 0 102 0V8a1 1 0 00-1-1z" clipRule="evenodd" />
          </svg>
        </button>
      </div>

      {/* Test Value Input */}
      <div className="px-3 py-2 bg-yellow-50 border-b border-emerald-200">
        <label className="block text-emerald-800 text-xs font-medium mb-1">
          Test Value (Dev Only)
        </label>
        <input
          type="text"
          value={testValue}
          onChange={(e) => handleConfigChange('test_value', e.target.value)}
          onMouseDown={(e) => e.stopPropagation()}
          onFocus={(e) => e.stopPropagation()}
          onClick={(e) => e.stopPropagation()}
          placeholder={template.config[0]?.placeholder || 'Enter test value...'}
          className="w-full bg-white border border-emerald-300 text-emerald-800 text-xs rounded px-2 py-1 focus:outline-none focus:ring-1 focus:ring-emerald-500 focus:border-emerald-500"
        />
      </div>

      {/* Output Node */}
      <div className="py-2 relative">
        <div className="flex relative min-h-6">
          {/* Output Side */}
          <div className="flex-1 flex items-center justify-end relative px-3">
            <div className="flex-1 text-right">
              <div className="text-xs text-emerald-700 break-words leading-tight font-medium">
                {template.outputs[0]?.name}
              </div>
              <div className="text-xs text-emerald-600">
                ({template.outputs[0]?.type})
              </div>
            </div>
            {/* Output Node - Circle centered on right edge */}
            <div 
              className="absolute w-5 h-6 flex items-center justify-center"
              style={{ right: '-10px' }}
            >
              <div
                ref={outputNodeRef}
                className="w-5 h-5 rounded-full border-2 border-emerald-800 cursor-pointer hover:scale-110 transition-transform"
                style={{ 
                  backgroundColor: '#10B981', // Green for string type
                  pointerEvents: 'all',
                  zIndex: 1000
                }}
                title={`${template.outputs[0]?.name} (${template.outputs[0]?.type}): ${template.outputs[0]?.description}`}
                onClick={onNodeClick ? onNodeClick(moduleId, 'output', 0) : undefined}
                onMouseDown={(e) => {
                  e.stopPropagation();
                  e.preventDefault();
                }}
              />
            </div>
          </div>
        </div>
      </div>

      {/* Delete Confirmation Modal */}
      {showDeleteModal && (
        <div className="absolute -top-24 left-1/2 transform -translate-x-1/2 z-50">
          <div className="bg-gray-800 rounded-lg shadow-xl border border-gray-700 p-4 w-64">
            <h3 className="text-white font-semibold text-sm mb-2">Delete Module</h3>
            <p className="text-gray-300 text-xs mb-4">
              Are you sure you want to delete "{template.name}"?
            </p>
            <div className="flex space-x-2">
              <button
                onClick={handleCancelDelete}
                className="flex-1 px-3 py-1.5 bg-gray-600 hover:bg-gray-700 text-white text-xs rounded transition-colors"
              >
                Cancel
              </button>
              <button
                onClick={handleConfirmDelete}
                className="flex-1 px-3 py-1.5 bg-red-600 hover:bg-red-700 text-white text-xs rounded transition-colors"
              >
                Delete
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};