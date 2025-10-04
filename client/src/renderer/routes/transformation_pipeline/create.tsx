import { createFileRoute } from "@tanstack/react-router";
import { useState, useEffect, useRef } from "react";
import { ModuleSelectorPane } from "../../components/transformation-pipeline/ModuleSelectorPane";
import { PipelineGraph, PipelineGraphRef } from "../../components/transformation-pipeline/PipelineGraph";
import { EntryPointModal } from "../../components/transformation-pipeline/EntryPointModal";
import { ModuleTemplate } from "../../types/moduleTypes";
import { EntryPoint } from "../../types/pipelineTypes";
import { serializePipelineData } from "../../utils/pipelineSerializer";

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

  // Entry points state
  const [showEntryPointModal, setShowEntryPointModal] = useState(true);
  const [entryPoints, setEntryPoints] = useState<EntryPoint[]>([]);

  // Reference to PipelineGraph to extract state
  const pipelineGraphRef = useRef<PipelineGraphRef>(null);

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

  const handleEntryPointsConfirm = (points: Array<{ name: string }>) => {
    // Create entry points with IDs and str type
    const newEntryPoints: EntryPoint[] = points.map(p => ({
      node_id: crypto.randomUUID(),
      name: p.name,
      type: 'str'
    }));
    setEntryPoints(newEntryPoints);
    setShowEntryPointModal(false);
  };

  const handleEntryPointsCancel = () => {
    // Go back to pipeline list
    window.history.back();
  };

  const handleValidate = async () => {
    if (!pipelineGraphRef.current) {
      console.error("PipelineGraph ref not available");
      return;
    }

    // Extract current pipeline state
    const pipelineState = pipelineGraphRef.current.getPipelineState();

    try {
      const response = await fetch("http://localhost:8090/api/pipelines/validate", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          pipeline_json: pipelineState
        }),
      });

      const validationResult = await response.json();
      console.log("Validation result:", validationResult);

      if (validationResult.valid) {
        console.log("✅ Pipeline is valid!");
      } else {
        console.log("❌ Pipeline validation failed:");
        validationResult.errors.forEach((error: any) => {
          console.log(`  - [${error.code}] ${error.message}`, error.where);
        });
      }
    } catch (error) {
      console.error("Validation request failed:", error);
    }
  };

  const handleSave = async () => {
    if (!pipelineGraphRef.current) {
      console.error("PipelineGraph ref not available");
      return;
    }

    // Validate pipeline name
    if (!pipelineName || pipelineName.trim() === "") {
      alert("Please provide a pipeline name");
      return;
    }

    // Extract current state from graph
    const pipelineState = pipelineGraphRef.current.getPipelineState();
    const visualState = pipelineGraphRef.current.getVisualState();

    // Serialize to backend format
    const backendData = serializePipelineData(
      pipelineState,
      visualState,
      pipelineName,
      pipelineDescription
    );

    // Log to console for verification
    console.log("=== PIPELINE STATE ===");
    console.log("Frontend PipelineState:", pipelineState);
    console.log("\n=== VISUAL STATE ===");
    console.log("Frontend VisualState:", visualState);
    console.log("\n=== BACKEND SERIALIZED DATA ===");
    console.log("Backend format:", JSON.stringify(backendData, null, 2));

    try {
      // Send to backend API
      const response = await fetch("http://localhost:8090/api/pipelines", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(backendData)
      });

      if (!response.ok) {
        const errorData = await response.json().catch(() => ({ detail: "Unknown error" }));
        throw new Error(errorData.detail || `HTTP ${response.status}: ${response.statusText}`);
      }

      const savedPipeline = await response.json();
      console.log("Pipeline saved successfully:", savedPipeline);

      // Show success message and redirect
      alert(`Pipeline "${pipelineName}" saved successfully!`);
      window.history.back();
    } catch (err) {
      console.error("Failed to save pipeline:", err);
      alert(`Failed to save pipeline: ${err instanceof Error ? err.message : "Unknown error"}`);
    }
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
    <>
      {/* Entry Point Modal */}
      {showEntryPointModal && (
        <EntryPointModal
          onConfirm={handleEntryPointsConfirm}
          onCancel={handleEntryPointsCancel}
        />
      )}

      {/* Main Pipeline Builder */}
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
              onClick={handleValidate}
              className="px-4 py-2 text-sm font-medium text-white bg-purple-600 hover:bg-purple-700 rounded-md transition-colors"
            >
              Validate Pipeline
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
            ref={pipelineGraphRef}
            moduleTemplates={moduleTemplates}
            selectedModuleId={selectedModuleId}
            onModulePlaced={handleModulePlaced}
            viewOnly={false}
            entryPoints={entryPoints}
          />
        </div>
      </div>
    </div>
    </>
  );
}
