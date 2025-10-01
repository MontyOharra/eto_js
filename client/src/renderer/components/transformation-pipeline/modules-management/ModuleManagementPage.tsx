import React from 'react';
import { BasicModulesSection } from './BasicModulesSection';
import { CustomModulesSection } from './CustomModulesSection';

export const ModuleManagementPage: React.FC = () => {
  const handleNewModule = () => {
    // TODO: Implement new module creation when needed
    console.log('New module creation not yet implemented');
  };

  const handleEditModule = (moduleId: string) => {
    // TODO: Implement module editing when needed
    console.log('Module editing not yet implemented:', moduleId);
  };

  return (
    <div className="h-full bg-gray-900 text-white">
      <div className="max-w-7xl mx-auto px-6 py-8">
        {/* Page Header */}
        <div className="mb-8">
          <h1 className="text-3xl font-bold text-white mb-2">Module Management</h1>
          <p className="text-gray-400">
            View and manage transformation modules for your pipelines
          </p>
        </div>

        {/* Basic Modules Section */}
        <div className="mb-12">
          <BasicModulesSection />
        </div>

        {/* Custom Modules Section */}
        <div>
          <CustomModulesSection
            onNewModule={handleNewModule}
            onEditModule={handleEditModule}
          />
        </div>
      </div>
    </div>
  );
};