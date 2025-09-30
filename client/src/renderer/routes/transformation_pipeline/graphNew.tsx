import { createFileRoute } from "@tanstack/react-router";
import { useState, useEffect } from "react";
import { ModuleSelectionPaneNew } from "../../components/transformation-pipeline/ui/ModuleSelectionPaneNew";
import { TransformationGraphNew } from "../../components/transformation-pipeline/TransformationGraphNew";
import { ModuleTemplate, PipelineState, VisualState } from "../../types/pipelineTypes";

export const Route = createFileRoute("/transformation_pipeline/graphNew")({
  component: TransformationPipelineGraph,
});

function TransformationPipelineGraph() {
  // Module templates from API
  const [moduleTemplates, setModuleTemplates] = useState<ModuleTemplate[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Sidebar state
  const [isSidebarCollapsed, setIsSidebarCollapsed] = useState(false);
  const [selectedModule, setSelectedModule] = useState<ModuleTemplate | null>(null);

  // Load module templates from API
  useEffect(() => {
    const loadModules = async () => {
      setIsLoading(true);
      setError(null);

      try {
        const response = await fetch('http://localhost:8090/api/modules');

        if (!response.ok) {
          throw new Error(`HTTP error! status: ${response.status}`);
        }

        const data = await response.json();

        if (!data.modules) {
          throw new Error('No modules found in response');
        }

        setModuleTemplates(data.modules);
        console.log(`Loaded ${data.modules.length} module templates from API`);

      } catch (err) {
        console.error('Error loading modules:', err);
        setError(`Failed to load modules: ${err instanceof Error ? err.message : 'Unknown error'}`);
        setModuleTemplates([]);
      } finally {
        setIsLoading(false);
      }
    };

    loadModules();
  }, []);

  const toggleSidebar = () => {
    setIsSidebarCollapsed(prev => !prev);
  };

  const handleModuleSelect = (module: ModuleTemplate | null) => {
    setSelectedModule(module);
  };

  // For now, we're creating a new pipeline, so no initial state
  // When loading an existing pipeline, these would come from the API
  const initialPipeline: PipelineState | undefined = undefined;
  const initialVisual: VisualState | undefined = undefined;

  // Callbacks for when the pipeline changes (for saving, etc.)
  const handlePipelineChange = (pipeline: PipelineState) => {
    // This could trigger auto-save or enable a save button
    console.log('Pipeline changed:', pipeline);
  };

  const handleVisualChange = (visual: VisualState) => {
    // This could trigger auto-save or enable a save button
    console.log('Visual state changed:', visual);
  };

  // Show loading state while modules are loading
  if (isLoading) {
    return (
      <div className="w-full h-full flex items-center justify-center bg-gray-900 text-white">
        <div className="text-center">
          <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-white mx-auto mb-4"></div>
          <p>Loading modules from transformation pipeline server...</p>
        </div>
      </div>
    );
  }

  // Show error state if loading failed
  if (error) {
    return (
      <div className="w-full h-full flex items-center justify-center bg-gray-900 text-white">
        <div className="text-center">
          <div className="text-red-400 mb-4">
            <svg className="w-12 h-12 mx-auto" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
            </svg>
          </div>
          <p className="text-red-400">{error}</p>
          <p className="text-sm text-gray-400 mt-2">Make sure the transformation pipeline server is running on port 8090</p>
        </div>
      </div>
    );
  }

  return (
    <div className="relative w-full h-full overflow-hidden bg-gray-900 flex">
      {/* Module Selection Sidebar */}
      <div className="relative z-50">
        <ModuleSelectionPaneNew
          modules={moduleTemplates}
          isCollapsed={isSidebarCollapsed}
          onToggleCollapse={toggleSidebar}
          onModuleSelect={handleModuleSelect}
          selectedModule={selectedModule}
        />
      </div>

      {/* Main Graph Area */}
      <TransformationGraphNew
        moduleTemplates={moduleTemplates}
        selectedModule={selectedModule}
        onModuleSelect={handleModuleSelect}
        initialPipeline={initialPipeline}
        initialVisual={initialVisual}
        onPipelineChange={handlePipelineChange}
        onVisualChange={handleVisualChange}
      />
    </div>
  );
}