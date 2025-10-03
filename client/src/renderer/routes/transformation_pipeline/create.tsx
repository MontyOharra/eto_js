import { createFileRoute } from "@tanstack/react-router";
import { useState, useEffect } from "react";
import { ModuleSelectorPane } from "../../components/transformation-pipeline/ModuleSelectorPane";
import { PipelineGraph } from "../../components/transformation-pipeline/PipelineGraph";
import { ModuleTemplate } from "../../types/moduleTypes";

export const Route = createFileRoute("/transformation_pipeline/create")({
  component: PipelineCreatePage,
});

function PipelineCreatePage() {
  // Page state
  const [moduleTemplates, setModuleTemplates] = useState<ModuleTemplate[]>([]);
  const [selectedModuleId, setSelectedModuleId] = useState<string | null>(null);
  const [pipelineName, setPipelineName] = useState("Untitled Pipeline");
  const [pipelineDescription, setPipelineDescription] = useState("");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Fetch module templates on mount
  useEffect(() => {
    async function loadModules() {
      setLoading(true);
      setError(null);
      try {
        const response = await fetch("http://localhost:8090/api/modules");
        if (!response.ok) {
          throw new Error(`HTTP error! status: ${response.status}`);
        }
        const data = await response.json();
        setModuleTemplates(data.modules || []);
      } catch (err) {
        console.error("Failed to load module templates:", err);
        setError(err instanceof Error ? err.message : "Failed to load modules");
      } finally {
        setLoading(false);
      }
    }
    loadModules();
  }, []);

  const handleModuleSelect = (moduleId: string | null) => {
    setSelectedModuleId(moduleId);
  };

  const handleModulePlaced = () => {
    setSelectedModuleId(null);
  };

  const handleSave = async () => {
    // TODO: Extract state from PipelineGraph and save
    console.log("Save pipeline:", { pipelineName, pipelineDescription });
  };

  const handleCancel = () => {
    window.history.back();
  };

  // Loading state
  if (loading) {
    return (
      <div className="flex h-screen bg-gray-900">
        <div className="flex-1 flex items-center justify-center">
          <div className="text-center">
            <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-500 mx-auto mb-4"></div>
            <p className="text-gray-400">Loading modules...</p>
          </div>
        </div>
      </div>
    );
  }

  // Error state
  if (error) {
    return (
      <div className="flex h-screen bg-gray-900">
        <div className="flex-1 flex items-center justify-center">
          <div className="text-center">
            <div className="text-red-400 mb-4">
              <svg
                className="w-16 h-16 mx-auto"
                fill="none"
                stroke="currentColor"
                viewBox="0 0 24 24"
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth={2}
                  d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"
                />
              </svg>
            </div>
            <h3 className="text-lg font-medium text-gray-300 mb-2">
              Failed to load modules
            </h3>
            <p className="text-gray-500">{error}</p>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="flex h-screen flex-col bg-gray-900">
      {/* Header */}
      <div className="bg-gray-800 border-b border-gray-600 px-4 py-3">
        <div className="flex items-center justify-between">
          <div className="flex items-center space-x-4 flex-1">
            <input
              type="text"
              value={pipelineName}
              onChange={(e) => setPipelineName(e.target.value)}
              className="text-xl font-semibold bg-transparent text-white border-none focus:outline-none focus:ring-2 focus:ring-blue-500 px-2 py-1 rounded"
              placeholder="Pipeline Name"
            />
            <input
              type="text"
              value={pipelineDescription}
              onChange={(e) => setPipelineDescription(e.target.value)}
              className="text-sm bg-transparent text-gray-400 border-none focus:outline-none focus:ring-2 focus:ring-blue-500 px-2 py-1 rounded flex-1"
              placeholder="Description (optional)"
            />
          </div>
          <div className="flex items-center space-x-2">
            <button
              onClick={handleCancel}
              className="px-4 py-2 text-sm font-medium text-gray-300 bg-gray-700 hover:bg-gray-600 rounded-md transition-colors"
            >
              Cancel
            </button>
            <button
              onClick={handleSave}
              className="px-4 py-2 text-sm font-medium text-white bg-blue-600 hover:bg-blue-700 rounded-md transition-colors"
            >
              Save Pipeline
            </button>
          </div>
        </div>
      </div>

      {/* Main Content Area */}
      <div className="flex flex-1 overflow-hidden">
        {/* Module Selector Pane */}
        <ModuleSelectorPane
          modules={moduleTemplates}
          selectedModuleId={selectedModuleId}
          onModuleSelect={handleModuleSelect}
        />

        {/* Pipeline Graph */}
        <div className="flex-1">
          <PipelineGraph
            moduleTemplates={moduleTemplates}
            selectedModuleId={selectedModuleId}
            onModulePlaced={handleModulePlaced}
            viewOnly={false}
          />
        </div>
      </div>
    </div>
  );
}
