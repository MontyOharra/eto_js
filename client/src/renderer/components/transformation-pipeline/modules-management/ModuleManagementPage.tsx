import React, { useState } from 'react';
import { BasicModulesSection } from './BasicModulesSection';
import { CustomModulesSection } from './CustomModulesSection';
import { CustomModuleBuilder } from '../module-builder/CustomModuleBuilder';

export const ModuleManagementPage: React.FC = () => {
  const [isBuilderOpen, setIsBuilderOpen] = useState(false);
  const [editingModuleId, setEditingModuleId] = useState<string | null>(null);

  const handleNewModule = () => {
    setEditingModuleId(null);
    setIsBuilderOpen(true);
  };

  const handleEditModule = (moduleId: string) => {
    setEditingModuleId(moduleId);
    setIsBuilderOpen(true);
  };

  const handleCloseBuilder = () => {
    setIsBuilderOpen(false);
    setEditingModuleId(null);
  };

  if (isBuilderOpen) {
    return (
      <CustomModuleBuilder
        moduleId={editingModuleId}
        onClose={handleCloseBuilder}
        onSave={handleCloseBuilder}
      />
    );
  }

  return (
    <div className="h-full bg-gray-900 text-white">
      <div className="max-w-7xl mx-auto px-6 py-8">
        {/* Page Header */}
        <div className="mb-8">
          <h1 className="text-3xl font-bold text-white mb-2">Module Management</h1>
          <p className="text-gray-400">
            Manage and create transformation modules for your pipelines
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