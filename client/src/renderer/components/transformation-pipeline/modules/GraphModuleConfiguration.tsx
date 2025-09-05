import React, { useState } from 'react';
import { BaseModuleTemplate } from '../../../types/modules';

interface GraphModuleConfigurationProps {
  template: BaseModuleTemplate;
  config: Record<string, any>;
  onConfigChange: (config: Record<string, any>) => void;
}

export const GraphModuleConfiguration: React.FC<GraphModuleConfigurationProps> = ({
  template,
  config,
  onConfigChange
}) => {
  const [isConfigExpanded, setIsConfigExpanded] = useState(true);

  const handleConfigChange = (configName: string, value: any) => {
    const newConfig = { ...config, [configName]: value };
    onConfigChange(newConfig);
  };

  // Don't render if there are no visible config items
  const visibleConfigItems = template.config?.filter(c => !c.hidden) || [];
  if (visibleConfigItems.length === 0) {
    return null;
  }

  return (
    <div className="border-t border-gray-700">
      <div 
        className="px-4 py-2 flex items-center justify-between cursor-pointer hover:bg-gray-750 transition-colors"
        onClick={() => setIsConfigExpanded(!isConfigExpanded)}
      >
        <span className="text-gray-300 text-sm font-medium">Configuration</span>
        <svg 
          className={`w-4 h-4 text-gray-400 transition-transform ${isConfigExpanded ? 'rotate-180' : ''}`}
          fill="none" 
          stroke="currentColor" 
          viewBox="0 0 24 24"
        >
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
        </svg>
      </div>
      
      {isConfigExpanded && (
        <div className="px-4 pb-2 space-y-2">
          {visibleConfigItems.map((configItem) => (
            <div key={configItem.name}>
              <label className="block text-gray-300 text-xs mb-1">
                {configItem.description}
                {configItem.required && <span className="text-red-400 ml-1">*</span>}
              </label>
              {configItem.type === 'select' ? (
                <select
                  value={config[configItem.name] || configItem.defaultValue || ''}
                  onChange={(e) => handleConfigChange(configItem.name, e.target.value)}
                  onMouseDown={(e) => e.stopPropagation()}
                  className="w-full bg-gray-700 border border-gray-600 text-white text-xs rounded px-2 py-1 focus:outline-none focus:ring-2 focus:ring-blue-500"
                >
                  {configItem.options?.map(option => (
                    <option key={option} value={option}>
                      {option}
                    </option>
                  ))}
                </select>
              ) : (
                <input
                  type={configItem.type === 'number' ? 'number' : 'text'}
                  value={config[configItem.name] || configItem.defaultValue || ''}
                  onChange={(e) => handleConfigChange(configItem.name, e.target.value)}
                  onMouseDown={(e) => e.stopPropagation()}
                  placeholder={configItem.placeholder}
                  className="w-full bg-gray-700 border border-gray-600 text-white text-xs rounded px-2 py-1 focus:outline-none focus:ring-2 focus:ring-blue-500"
                />
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  );
};