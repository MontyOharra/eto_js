import React, { useState } from 'react';
import { ModuleCard } from './ModuleCard';
import { ModuleDetailsModal } from './ModuleDetailsModal';

// TODO: Replace with actual custom module type and API calls
interface CustomModule {
  id: string;
  name: string;
  description: string;
  category: string;
  color: string;
  inputs: any[];
  outputs: any[];
  config: any[];
  createdAt: string;
  updatedAt: string;
}

interface CustomModulesSectionProps {
  onNewModule: () => void;
  onEditModule: (moduleId: string) => void;
}

export const CustomModulesSection: React.FC<CustomModulesSectionProps> = ({
  onNewModule,
  onEditModule
}) => {
  const [selectedModule, setSelectedModule] = useState<CustomModule | null>(null);
  const [searchTerm, setSearchTerm] = useState('');

  // TODO: Replace with actual API call to get custom modules
  const customModules: CustomModule[] = [
    // Mock data for now
    {
      id: 'custom_1',
      name: 'Email Validator',
      description: 'Validates email addresses and extracts domain information',
      category: 'Custom',
      color: '#8B5CF6',
      inputs: [
        { name: 'Email', type: 'string', description: 'Email address to validate', required: true }
      ],
      outputs: [
        { name: 'Is Valid', type: 'boolean', description: 'Whether the email is valid', required: true },
        { name: 'Domain', type: 'string', description: 'Extracted domain', required: false }
      ],
      config: [],
      createdAt: '2024-01-15T10:30:00Z',
      updatedAt: '2024-01-15T10:30:00Z'
    }
  ];

  // Filter modules based on search term
  const filteredModules = customModules.filter(module =>
    module.name.toLowerCase().includes(searchTerm.toLowerCase()) ||
    module.description.toLowerCase().includes(searchTerm.toLowerCase())
  );

  const handleViewModule = (module: CustomModule) => {
    setSelectedModule(module);
  };

  const handleEditModule = (module: CustomModule) => {
    onEditModule(module.id);
  };

  const handleDeleteModule = (module: CustomModule) => {
    if (confirm(`Are you sure you want to delete "${module.name}"?`)) {
      // TODO: Implement delete API call
      console.log('Delete module:', module.id);
    }
  };

  const handleCloseModal = () => {
    setSelectedModule(null);
  };

  return (
    <div>
      {/* Section Header */}
      <div className="flex items-center justify-between mb-6">
        <div>
          <h2 className="text-2xl font-semibold text-white mb-2">Custom Modules</h2>
          <p className="text-gray-400">
            User-created modules for specialized transformations ({customModules.length} total)
          </p>
        </div>
        
        <button
          onClick={onNewModule}
          className="bg-blue-600 hover:bg-blue-700 text-white font-medium px-4 py-2 rounded-lg transition-colors flex items-center gap-2"
        >
          <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 4v16m8-8H4" />
          </svg>
          New Custom Module
        </button>
      </div>

      {/* Search Bar */}
      {customModules.length > 0 && (
        <div className="mb-6">
          <div className="relative max-w-md">
            <input
              type="text"
              placeholder="Search custom modules..."
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
      )}

      {/* Modules Grid */}
      {filteredModules.length > 0 ? (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-4">
          {filteredModules.map((module) => (
            <ModuleCard
              key={module.id}
              module={module as any} // TODO: Fix type compatibility
              onView={() => handleViewModule(module)}
              onEdit={() => handleEditModule(module)}
              onDelete={() => handleDeleteModule(module)}
              isReadOnly={false}
            />
          ))}
        </div>
      ) : customModules.length > 0 ? (
        /* No search results */
        <div className="text-center py-12">
          <svg className="w-12 h-12 text-gray-600 mx-auto mb-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
          </svg>
          <p className="text-gray-400 text-lg">No custom modules found matching "{searchTerm}"</p>
        </div>
      ) : (
        /* Empty state */
        <div className="text-center py-16 border-2 border-dashed border-gray-700 rounded-lg">
          <svg className="w-16 h-16 text-gray-600 mx-auto mb-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 11H5m14 0a2 2 0 012 2v6a2 2 0 01-2 2H5a2 2 0 01-2-2v-6a2 2 0 012-2m14 0V9a2 2 0 00-2-2M5 11V9a2 2 0 012-2m0 0V5a2 2 0 012-2h6a2 2 0 012 2v2M7 7h10" />
          </svg>
          <h3 className="text-xl font-medium text-white mb-2">No Custom Modules Yet</h3>
          <p className="text-gray-400 mb-6 max-w-md mx-auto">
            Create your first custom module by combining basic modules into reusable transformations.
          </p>
          <button
            onClick={onNewModule}
            className="bg-blue-600 hover:bg-blue-700 text-white font-medium px-6 py-3 rounded-lg transition-colors inline-flex items-center gap-2"
          >
            <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 4v16m8-8H4" />
            </svg>
            Create Custom Module
          </button>
        </div>
      )}

      {/* Module Details Modal */}
      {selectedModule && (
        <ModuleDetailsModal
          module={selectedModule as any} // TODO: Fix type compatibility
          onClose={handleCloseModal}
        />
      )}
    </div>
  );
};