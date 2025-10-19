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
}

export function ModuleHeader({ moduleInstance, template, onDeleteModule }: ModuleHeaderProps) {
  const headerColor = template.color || '#4B5563';
  const textColor = getTextColor(headerColor);

  const handleDelete = () => {
    if (onDeleteModule) {
      onDeleteModule(moduleInstance.module_instance_id);
    }
  };

  return (
    <div
      className="px-3 py-2 rounded-t-lg border-b border-gray-600 flex items-center justify-between"
      style={{ backgroundColor: headerColor }}
    >
      <div>
        <div className="font-medium text-sm" style={{ color: textColor }}>
          {template.title}
        </div>
        <div className="text-xs opacity-70" style={{ color: textColor }}>
          {moduleInstance.module_instance_id}
        </div>
      </div>
      <button
        onClick={handleDelete}
        className="p-1 rounded hover:bg-red-500 transition-colors"
        title="Delete module"
      >
        <svg className="w-4 h-4" style={{ color: textColor }} fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
        </svg>
      </button>
    </div>
  );
}
