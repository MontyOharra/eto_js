import React from 'react';
import { BaseModuleTemplate } from '../../../types/modules';

interface ModuleCardProps {
  module: BaseModuleTemplate;
  onView?: () => void;
  onEdit?: () => void;
  onDelete?: () => void;
  isReadOnly?: boolean;
}

export const ModuleCard: React.FC<ModuleCardProps> = ({
  module,
  onView,
  onEdit,
  onDelete,
  isReadOnly = false
}) => {
  return (
    <div className="bg-gray-800 border border-gray-700 rounded-lg p-4 hover:border-gray-600 transition-colors">
      {/* Module Header */}
      <div className="flex items-start justify-between mb-3">
        <div className="flex items-center">
          <div 
            className="w-4 h-4 rounded-full flex-shrink-0"
            style={{ backgroundColor: module.color }}
          />
          <h4 className="ml-3 font-medium text-white text-sm truncate">{module.name}</h4>
        </div>
        
        {/* Category Badge */}
        <span className="text-xs bg-gray-700 text-gray-300 px-2 py-1 rounded flex-shrink-0 ml-2">
          {module.category}
        </span>
      </div>

      {/* Description */}
      <p className="text-gray-400 text-xs mb-4 line-clamp-3 leading-relaxed">
        {module.description}
      </p>

      {/* Module Stats */}
      <div className="flex items-center justify-between text-xs text-gray-500 mb-4">
        <div className="flex items-center space-x-4">
          <span>{module.inputs.length} input{module.inputs.length !== 1 ? 's' : ''}</span>
          <span>{module.outputs.length} output{module.outputs.length !== 1 ? 's' : ''}</span>
          {module.config?.length > 0 && (
            <span>{module.config.length} config{module.config.length !== 1 ? 's' : ''}</span>
          )}
        </div>
      </div>

      {/* Action Buttons */}
      <div className="flex space-x-2">
        {onView && (
          <button
            onClick={onView}
            className="flex-1 bg-blue-600 hover:bg-blue-700 text-white text-xs font-medium py-2 px-3 rounded transition-colors"
          >
            View
          </button>
        )}
        
        {!isReadOnly && (
          <>
            {onEdit && (
              <button
                onClick={onEdit}
                className="flex-1 bg-gray-600 hover:bg-gray-700 text-white text-xs font-medium py-2 px-3 rounded transition-colors"
              >
                Edit
              </button>
            )}
            
            {onDelete && (
              <button
                onClick={onDelete}
                className="px-3 py-2 bg-red-600 hover:bg-red-700 text-white text-xs font-medium rounded transition-colors"
              >
                Delete
              </button>
            )}
          </>
        )}
      </div>

      {/* Read-only indicator for basic modules */}
      {isReadOnly && (
        <div className="mt-2 flex items-center text-xs text-gray-500">
          <svg className="w-3 h-3 mr-1" fill="currentColor" viewBox="0 0 20 20">
            <path fillRule="evenodd" d="M5 9V7a5 5 0 0110 0v2a2 2 0 012 2v5a2 2 0 01-2 2H5a2 2 0 01-2-2v-5a2 2 0 012-2zm8-2v2H7V7a3 3 0 016 0z" clipRule="evenodd" />
          </svg>
          System Module
        </div>
      )}
    </div>
  );
};