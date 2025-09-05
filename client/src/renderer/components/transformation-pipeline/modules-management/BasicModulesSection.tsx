import React, { useState } from 'react';
import { useTransformationModules } from '../../../hooks/useTransformationModules';
import { ModuleCard } from './ModuleCard';
import { ModuleDetailsModal } from './ModuleDetailsModal';
import { BaseModuleTemplate } from '../../../types/modules';

export const BasicModulesSection: React.FC = () => {
  const { modules: allModules, isLoading, error } = useTransformationModules();
  const [selectedModule, setSelectedModule] = useState<BaseModuleTemplate | null>(null);
  const [searchTerm, setSearchTerm] = useState('');

  // Filter out custom modules (they don't have the 'Custom' category yet in base modules)
  const basicModules = allModules.filter(module => module.category !== 'Custom');

  // Group modules by category
  const modulesByCategory = basicModules.reduce((acc, module) => {
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

  const handleViewModule = (module: BaseModuleTemplate) => {
    setSelectedModule(module);
  };

  const handleCloseModal = () => {
    setSelectedModule(null);
  };

  if (isLoading) {
    return (
      <div className="animate-pulse">
        <div className="h-8 bg-gray-700 rounded w-64 mb-4"></div>
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {[...Array(6)].map((_, i) => (
            <div key={i} className="h-48 bg-gray-700 rounded-lg"></div>
          ))}
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="bg-red-900/20 border border-red-500 rounded-lg p-4">
        <p className="text-red-400">Failed to load basic modules: {error}</p>
      </div>
    );
  }

  return (
    <div>
      {/* Section Header */}
      <div className="flex items-center justify-between mb-6">
        <div>
          <h2 className="text-2xl font-semibold text-white mb-2">Basic Modules</h2>
          <p className="text-gray-400">
            System-provided modules for data transformation ({basicModules.length} total)
          </p>
        </div>
      </div>

      {/* Search Bar */}
      <div className="mb-6">
        <div className="relative max-w-md">
          <input
            type="text"
            placeholder="Search basic modules..."
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            className="w-full bg-gray-800 border border-gray-600 rounded-lg px-4 py-2 pl-10 text-white placeholder-gray-400 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
          />
          <svg 
            className="absolute left-3 top-1/2 transform -translate-y-1/2 w-4 h-4 text-gray-400"
            fill="none" 
            stroke="currentColor" 
            viewBox="0 0 24 24"
          >
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
          </svg>
        </div>
      </div>

      {/* Modules by Category */}
      <div className="space-y-8">
        {Object.entries(filteredModulesByCategory).map(([category, categoryModules]) => (
          <div key={category}>
            {/* Category Header */}
            <div className="flex items-center mb-4">
              <h3 className="text-xl font-medium text-white">{category}</h3>
              <span className="ml-3 text-sm text-gray-400 bg-gray-800 px-2 py-1 rounded">
                {categoryModules.length} module{categoryModules.length !== 1 ? 's' : ''}
              </span>
            </div>

            {/* Module Grid */}
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-4">
              {categoryModules.map((module) => (
                <ModuleCard
                  key={module.id}
                  module={module}
                  onView={() => handleViewModule(module)}
                  isReadOnly={true}
                />
              ))}
            </div>
          </div>
        ))}

        {/* No results message */}
        {Object.keys(filteredModulesByCategory).length === 0 && (
          <div className="text-center py-12">
            <svg className="w-12 h-12 text-gray-600 mx-auto mb-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
            </svg>
            <p className="text-gray-400 text-lg">No modules found matching "{searchTerm}"</p>
          </div>
        )}
      </div>

      {/* Module Details Modal */}
      {selectedModule && (
        <ModuleDetailsModal
          module={selectedModule}
          onClose={handleCloseModal}
        />
      )}
    </div>
  );
};