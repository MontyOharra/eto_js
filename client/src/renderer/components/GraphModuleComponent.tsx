import React, { useState } from 'react';
import { BaseModuleTemplate } from '../data/testModules';

interface GraphModuleComponentProps {
  template: BaseModuleTemplate;
  position: { x: number; y: number };
  onMouseDown?: (e: React.MouseEvent) => void;
  onDelete?: () => void;
}

export const GraphModuleComponent: React.FC<GraphModuleComponentProps> = ({
  template,
  position,
  onMouseDown,
  onDelete
}) => {
  const [showDeleteModal, setShowDeleteModal] = useState(false);

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
  return (
    <div
      className="absolute bg-gray-800 rounded-lg shadow-lg border-2 border-gray-600 cursor-pointer"
      style={{
        left: `${position.x}px`,
        top: `${position.y}px`,
        minWidth: '220px',
        width: 'max-content',
        maxWidth: '320px',
        transform: 'translate(-50%, -50%)',
      }}
      onMouseDown={onMouseDown}
    >
      {/* Header */}
      <div 
        className="px-4 py-3 rounded-t-lg flex items-center justify-between gap-4"
        style={{ backgroundColor: template.color }}
      >
        <div className="text-white font-medium text-sm flex-1">{template.name}</div>
        <button
          onClick={handleDeleteClick}
          className="w-7 h-7 flex items-center justify-center text-white hover:bg-red-600 hover:text-white rounded transition-colors"
          title="Delete module"
        >
          <svg className="w-4 h-4" fill="currentColor" viewBox="0 0 20 20">
            <path fillRule="evenodd" d="M9 2a1 1 0 00-.894.553L7.382 4H4a1 1 0 000 2v10a2 2 0 002 2h8a2 2 0 002-2V6a1 1 0 100-2h-3.382l-.724-1.447A1 1 0 0011 2H9zM7 8a1 1 0 012 0v6a1 1 0 11-2 0V8zm5-1a1 1 0 00-1 1v6a1 1 0 102 0V8a1 1 0 00-1-1z" clipRule="evenodd" />
          </svg>
        </button>
      </div>

      {/* Description */}
      <div className="px-4 py-2">
        <div className="text-gray-400 text-xs leading-relaxed">
          {template.description}
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