import React from 'react';
import { BasicModulesSection } from './BasicModulesSection';

export const ModuleManagementPage: React.FC = () => {

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

      </div>
    </div>
  );
};