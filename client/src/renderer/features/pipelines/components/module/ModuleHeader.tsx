/**
 * ModuleHeader Component
 * Displays the module title, ID, and delete button
 */

import { ModuleTemplate, ModuleInstance } from '../../../../types/moduleTypes';
import { getTextColor } from '../../../../utils/pipeline/moduleUtils';

export interface ModuleHeaderProps {
  moduleInstance: ModuleInstance;
  template: ModuleTemplate;
  onDeleteModule?: (moduleId: string) => void;
  executionMode?: boolean;
  onModuleMouseEnter?: (moduleId: string) => void;
  onModuleMouseLeave?: () => void;
  hasFailed?: boolean;
}

export function ModuleHeader({ moduleInstance, template, onDeleteModule, executionMode = false, onModuleMouseEnter, onModuleMouseLeave, hasFailed = false }: ModuleHeaderProps) {
  const headerColor = template.color || '#4B5563';
  const textColor = getTextColor(headerColor);

  // Check if this is an entry point module (not deletable)
  const isEntryPoint = moduleInstance.module_ref === 'entry_point:1.0.0';

  const handleDelete = () => {
    if (onDeleteModule) {
      onDeleteModule(moduleInstance.module_instance_id);
    }
  };

  return (
    <div
      className={`px-3 py-2 ${hasFailed ? 'rounded-t-[4px]' : 'rounded-t-[6px]'} border-b border-gray-600 flex items-center justify-between ${executionMode ? 'nodrag nopan' : ''}`}
      style={{ backgroundColor: headerColor, pointerEvents: 'auto' }}
      onMouseEnter={() => onModuleMouseEnter?.(moduleInstance.module_instance_id)}
      onMouseLeave={() => onModuleMouseLeave?.()}
    >
      <div className="font-medium text-base" style={{ color: textColor }}>
        {template.title}
      </div>
      {!executionMode && !isEntryPoint && (
        <button
          onClick={handleDelete}
          className="p-1 rounded hover:bg-red-500 transition-colors"
          title="Delete module"
        >
          <svg className="w-4 h-4" style={{ color: textColor }} fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
          </svg>
        </button>
      )}
    </div>
  );
}
