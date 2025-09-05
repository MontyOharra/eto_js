import { createFileRoute } from "@tanstack/react-router";
import { useState } from "react";
import { ModuleSelectionPane } from "../../components/transformation-pipeline/ui/ModuleSelectionPane";
import { TransformationGraph } from "../../components/transformation-pipeline/TransformationGraph";
import { BaseModuleTemplate } from "../../types/modules";
import { useTransformationModules } from "../../hooks/useTransformationModules";

export const Route = createFileRoute("/transformation_pipeline/graph")({
  component: TransformationPipelineGraph,
});

function TransformationPipelineGraph() {
  // Load modules from backend
  const { modules: allModules, isLoading: modulesLoading, error: modulesError } = useTransformationModules();
  
  // Route-level state (sidebar and module selection)
  const [isSidebarCollapsed, setIsSidebarCollapsed] = useState(false);
  const [selectedModuleTemplate, setSelectedModuleTemplate] = useState<BaseModuleTemplate | null>(null);
  
  // Event handlers for route-level concerns
  const toggleSidebar = () => {
    setIsSidebarCollapsed(prev => !prev);
  };

  const handleModuleTemplateSelect = (module: BaseModuleTemplate | null) => {
    setSelectedModuleTemplate(module);
  };

  const handleRunPipeline = async () => {
    console.log('Running transformation pipeline...');
    // This will be implemented later when the graph component is fully extracted
  };

  // Show loading state while modules are loading
  if (modulesLoading) {
    return (
      <div className="w-full h-full flex items-center justify-center bg-gray-900 text-white">
        <div className="text-center">
          <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-white mx-auto mb-4"></div>
          <p>Loading modules from backend...</p>
          {modulesError && <p className="text-red-400 mt-2">Error: {modulesError}</p>}
        </div>
      </div>
    );
  }

  return (
    <div className="relative w-full h-full overflow-hidden bg-gray-900 flex">
      {/* Module Selection Sidebar */}
      <div className="relative z-50">
        <ModuleSelectionPane
          modules={allModules}
          isCollapsed={isSidebarCollapsed}
          onToggleCollapse={toggleSidebar}
          onModuleSelect={handleModuleTemplateSelect}
          selectedModule={selectedModuleTemplate}
        />
      </div>
      
      {/* Main Graph Area - Now a reusable component */}
      <TransformationGraph
        modules={allModules}
        selectedModuleTemplate={selectedModuleTemplate}
        onModuleSelect={handleModuleTemplateSelect}
      />
    </div>
  );
}