import React from 'react';

interface ModuleDeletionModalProps {
  isVisible: boolean;
  moduleName: string;
  onConfirm: () => void;
  onCancel: () => void;
}

export const ModuleDeletionModal: React.FC<ModuleDeletionModalProps> = ({
  isVisible,
  moduleName,
  onConfirm,
  onCancel
}) => {
  if (!isVisible) return null;

  return (
    <div className="absolute -top-24 left-1/2 transform -translate-x-1/2 z-50">
      <div className="bg-gray-800 rounded-lg shadow-xl border border-gray-700 p-4 w-64">
        <h3 className="text-white font-semibold text-sm mb-2">Delete Module</h3>
        <p className="text-gray-300 text-xs mb-4">
          Are you sure you want to delete "{moduleName}"?
        </p>
        <div className="flex space-x-2">
          <button
            onClick={onCancel}
            className="flex-1 px-3 py-1.5 bg-gray-600 hover:bg-gray-700 text-white text-xs rounded transition-colors"
          >
            Cancel
          </button>
          <button
            onClick={onConfirm}
            className="flex-1 px-3 py-1.5 bg-red-600 hover:bg-red-700 text-white text-xs rounded transition-colors"
          >
            Delete
          </button>
        </div>
      </div>
    </div>
  );
};