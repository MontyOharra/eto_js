import React, { useState } from 'react';
import { BaseModuleTemplate } from '../types/modules';

interface ModuleSelectionPaneProps {
  modules: BaseModuleTemplate[];
  isCollapsed: boolean;
  onToggleCollapse: () => void;
  onModuleSelect: (module: BaseModuleTemplate | null) => void;
  selectedModule: BaseModuleTemplate | null;
}

export const ModuleSelectionPane: React.FC<ModuleSelectionPaneProps> = ({
  modules,
  isCollapsed,
  onToggleCollapse,
  onModuleSelect,
  selectedModule
}) => {
  const [searchTerm, setSearchTerm] = useState('');
  
  // Group modules by category
  const modulesByCategory = modules.reduce((acc, module) => {
    if (!acc[module.category]) {
      acc[module.category] = [];
    }
    acc[module.category].push(module);
    return acc;
  }, {} as Record<string, BaseModuleTemplate[]>);

  // Filter modules based on search term
  const filteredModulesByCategory = Object.entries(modulesByCategory).reduce((acc, [category, categoryModules]) => {
    const filteredModules = categoryModules.filter(module =>
      module.name.toLowerCase().includes(searchTerm.toLowerCase()) ||
      module.description.toLowerCase().includes(searchTerm.toLowerCase())
    );
    if (filteredModules.length > 0) {
      acc[category] = filteredModules;
    }
    return acc;
  }, {} as Record<string, BaseModuleTemplate[]>);

  const handleModuleClick = (module: BaseModuleTemplate, event: React.MouseEvent) => {
    event.preventDefault();
    // If the clicked module is already selected, deselect it
    if (selectedModule?.id === module.id) {
      onModuleSelect(null);
    } else {
      onModuleSelect(module);
    }
  };

  const handleModuleDragStart = (module: BaseModuleTemplate, event: React.DragEvent) => {
    // Set the drag data
    event.dataTransfer.setData('application/json', JSON.stringify(module));
    event.dataTransfer.effectAllowed = 'copy';
    
    // Also select the module
    onModuleSelect(module);
    
    // Create a header-only preview element for dragging
    const dragPreview = document.createElement('div');
    dragPreview.style.width = '200px';
    dragPreview.style.height = '40px';
    dragPreview.style.backgroundColor = module.color;
    dragPreview.style.borderRadius = '8px';
    dragPreview.style.boxShadow = '0 4px 6px rgba(0, 0, 0, 0.2)';
    dragPreview.style.position = 'absolute';
    dragPreview.style.top = '-1000px';
    dragPreview.style.left = '-1000px';
    dragPreview.style.display = 'flex';
    dragPreview.style.alignItems = 'center';
    dragPreview.style.padding = '0 16px';
    dragPreview.style.color = 'white';
    dragPreview.style.fontWeight = '500';
    dragPreview.style.fontSize = '14px';
    dragPreview.style.fontFamily = 'system-ui, -apple-system, sans-serif';
    dragPreview.textContent = module.name;
    
    document.body.appendChild(dragPreview);
    event.dataTransfer.setDragImage(dragPreview, 100, 20);
    
    // Clean up the preview element after drag starts
    setTimeout(() => {
      if (document.body.contains(dragPreview)) {
        document.body.removeChild(dragPreview);
      }
    }, 0);
  };

  return (
    <div 
      className={`bg-gray-800 border-r border-gray-700 transition-all duration-300 ease-in-out flex flex-col relative z-50 h-full ${
        isCollapsed ? 'w-12' : 'w-80'
      }`}
    >
      {/* Header */}
      <div className={`${isCollapsed ? 'flex flex-col items-center p-2 h-full' : 'flex items-center justify-between p-3 border-b border-gray-700'}`}>
        {!isCollapsed && (
          <h2 className="text-white font-semibold text-sm">Module Library</h2>
        )}
        
        {isCollapsed && (
          <div className="flex flex-col items-center h-full">
            <button
              onClick={onToggleCollapse}
              className="p-2 text-gray-400 hover:text-white hover:bg-gray-700 rounded transition-colors flex-shrink-0"
              title="Expand Module Library"
            >
              <svg 
                className="w-4 h-4 rotate-180" 
                fill="none" 
                stroke="currentColor" 
                viewBox="0 0 24 24"
              >
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 19l-7-7 7-7" />
              </svg>
            </button>
            
            <div className="flex-1 flex items-center justify-center">
              <div className="text-white font-semibold text-sm transform rotate-90 origin-center whitespace-nowrap">
                Module Library
              </div>
            </div>
          </div>
        )}
        
        {!isCollapsed && (
          <button
            onClick={onToggleCollapse}
            className="p-2 text-gray-400 hover:text-white hover:bg-gray-700 rounded transition-colors"
            title="Collapse Module Library"
          >
            <svg 
              className="w-4 h-4" 
              fill="none" 
              stroke="currentColor" 
              viewBox="0 0 24 24"
            >
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 19l-7-7 7-7" />
            </svg>
          </button>
        )}
      </div>

      {/* Content - only show when not collapsed */}
      {!isCollapsed && (
        <>
          {/* Search Bar */}
          <div className="p-3 border-b border-gray-700">
            <div className="relative">
              <input
                type="text"
                placeholder="Search modules..."
                value={searchTerm}
                onChange={(e) => setSearchTerm(e.target.value)}
                className="w-full bg-gray-700 text-white text-sm rounded px-3 py-2 pl-9 focus:outline-none focus:ring-2 focus:ring-blue-500"
              />
              <svg 
                className="w-4 h-4 text-gray-400 absolute left-3 top-1/2 transform -translate-y-1/2" 
                fill="none" 
                stroke="currentColor" 
                viewBox="0 0 24 24"
              >
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
              </svg>
            </div>
          </div>

          {/* Module Categories */}
          <div className="flex-1 overflow-y-auto">
            {Object.entries(filteredModulesByCategory).map(([category, categoryModules]) => (
              <div key={category} className="border-b border-gray-700 last:border-b-0">
                {/* Category Header */}
                <div className="px-3 py-2 bg-gray-750 text-gray-300 text-xs font-medium uppercase tracking-wide">
                  {category} ({categoryModules.length})
                </div>

                {/* Category Modules */}
                <div className="p-2 space-y-1">
                  {categoryModules.map((module) => (
                    <div
                      key={module.id}
                      draggable
                      onClick={(e) => handleModuleClick(module, e)}
                      onDragStart={(e) => handleModuleDragStart(module, e)}
                      className={`p-3 rounded cursor-pointer transition-all duration-150 border ${
                        selectedModule?.id === module.id
                          ? 'bg-blue-600 border-blue-400 text-white'
                          : 'bg-gray-700 border-gray-600 text-gray-200 hover:bg-gray-650 hover:border-gray-500'
                      }`}
                    >
                      {/* Module Header */}
                      <div className="flex items-center mb-2">
                        <div 
                          className="w-4 h-4 rounded-full flex-shrink-0"
                          style={{ backgroundColor: module.color }}
                        />
                        <div className="ml-3 flex-1 min-w-0">
                          <div className="text-sm font-medium truncate text-white">{module.name}</div>
                        </div>
                      </div>

                      {/* Module Description */}
                      <div className="text-xs text-gray-400 leading-relaxed">
                        {module.description}
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            ))}

            {/* No results message */}
            {Object.keys(filteredModulesByCategory).length === 0 && (
              <div className="p-4 text-center text-gray-500 text-sm">
                No modules found matching "{searchTerm}"
              </div>
            )}
          </div>

          {/* Footer Hint */}
          <div className="p-3 border-t border-gray-700 bg-gray-750">
            <div className="text-xs text-gray-400 text-center">
              {selectedModule ? (
                <span className="text-blue-400">Selected: {selectedModule.name}</span>
              ) : (
                "Browse available modules"
              )}
            </div>
          </div>
        </>
      )}
    </div>
  );
};