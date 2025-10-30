import { createFileRoute, useNavigate } from "@tanstack/react-router";
import { useState, useEffect, useRef } from "react";
import { ModuleSelectorPane } from "../../../features/pipelines/components/ModuleSelectorPane";
import {
  PipelineGraph,
  PipelineGraphRef,
} from "../../../features/pipelines/components/PipelineGraph";
import { EntryPointModal } from "../../../features/pipelines/components/EntryPointModal";
import { useModulesApi } from "../../../features/modules/hooks";
import {
  usePipelinesApi,
  usePipelineValidation,
} from "../../../features/pipelines/hooks";
import { serializePipelineData } from "../../../features/pipelines/utils/pipelineSerializer";
import { generateEntryPointId } from "../../../features/pipelines/utils/idGenerator";
import type { ModuleTemplate } from "../../../shared/types/moduleTypes";
import type { EntryPoint, PipelineState } from "../../../types/pipelineTypes";

export const Route = createFileRoute("/dashboard/pipelines/create")({
  component: PipelineCreatePage,
});

function PipelineCreatePage() {
  const navigate = useNavigate();
  const { getModules, isLoading, error: apiError } = useModulesApi();
  const {
    createPipeline,
    validatePipeline,
    isLoading: isSaving,
  } = usePipelinesApi();

  // Page state
  const [moduleTemplates, setModuleTemplates] = useState<ModuleTemplate[]>([]);
  const [selectedModuleId, setSelectedModuleId] = useState<string | null>(null);

  // Entry points state
  const [showEntryPointModal, setShowEntryPointModal] = useState(true);
  const [entryPoints, setEntryPoints] = useState<EntryPoint[]>([]);

  // Reference to PipelineGraph to extract state
  const pipelineGraphRef = useRef<PipelineGraphRef>(null);

  // Pipeline state for validation (updated via onChange callback)
  const [currentPipelineState, setCurrentPipelineState] =
    useState<PipelineState | null>(null);

  // Auto-validate pipeline state whenever it changes (debounced)
  const {
    isValid,
    error: validationError,
    isValidating,
  } = usePipelineValidation(currentPipelineState);

  // Fetch module templates on mount from API
  useEffect(() => {
    async function loadModules() {
      try {
        const response = await getModules();
        setModuleTemplates(response.modules);
      } catch (err) {
        console.error("Failed to load module templates:", err);
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
    const newEntryPoints: EntryPoint[] = points.map((p) => ({
      node_id: generateEntryPointId(),
      name: p.name,
      type: "str",
    }));
    setEntryPoints(newEntryPoints);
    setShowEntryPointModal(false);
  };

  const handleEntryPointsCancel = () => {
    // Go back to pipeline list
    navigate({ to: "/dashboard/pipelines" });
  };

  const handleValidate = async () => {
    if (!pipelineGraphRef.current) {
      console.error("PipelineGraph ref not available");
      return;
    }

    // Extract current pipeline state
    const pipelineState = pipelineGraphRef.current.getPipelineState();
    console.log(
      "[handleValidate] Manual validation - Pipeline state:",
      pipelineState
    );

    try {
      // Call validation endpoint using API hook
      const validationResult = await validatePipeline({
        pipeline_json: pipelineState,
      });

      console.log("[handleValidate] Validation result:", validationResult);

      if (validationResult.valid) {
        alert("✅ Pipeline is valid!");
      } else {
        const error = validationResult.error;
        if (error) {
          console.error(
            `❌ Pipeline validation failed: [${error.code}] ${error.message}`,
            error.where
          );
          alert(
            `❌ Pipeline validation failed:\n\n[${error.code}] ${error.message}\n\nCheck the browser console for details.`
          );
        } else {
          alert("❌ Pipeline validation failed with unknown error.");
        }
      }
    } catch (error) {
      console.error("Validation request failed:", error);
      alert("Failed to validate pipeline. Check console for details.");
    }
  };

  const handleSave = async () => {
    if (!pipelineGraphRef.current) {
      console.error("PipelineGraph ref not available");
      return;
    }

    // Extract current state from graph
    const pipelineState = pipelineGraphRef.current.getPipelineState();
    const visualState = pipelineGraphRef.current.getVisualState();

    // Serialize to backend format
    const backendData = serializePipelineData(pipelineState, visualState);

    // Log to console for verification
    console.log("=== PIPELINE STATE ===");
    console.log("Frontend PipelineState:", pipelineState);
    console.log("\n=== VISUAL STATE ===");
    console.log("Frontend VisualState:", visualState);
    console.log("\n=== BACKEND SERIALIZED DATA ===");
    console.log("Backend format:", JSON.stringify(backendData, null, 2));

    try {
      // Create pipeline using the API hook
      const result = await createPipeline(backendData);

      console.log("✅ Pipeline created successfully:", result);
      alert(
        `✅ Pipeline created successfully!\n\nID: ${result.id}\nCompiled Plan ID: ${result.compiled_plan_id || "Not yet compiled"}`
      );

      // Navigate back to pipelines list
      navigate({ to: "/dashboard/pipelines" });
    } catch (err) {
      console.error("Failed to create pipeline:", err);
      alert(
        `Failed to create pipeline: ${err instanceof Error ? err.message : "Unknown error"}`
      );
    }
  };

  const handleCancel = () => {
    navigate({ to: "/dashboard/pipelines" });
  };

  // Loading state
  if (isLoading) {
    return (
      <div className="flex h-full bg-gray-900">
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
  if (apiError) {
    return (
      <div className="flex h-full bg-gray-900">
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
            <p className="text-gray-500 mb-4">{apiError}</p>
            <button
              onClick={() => navigate({ to: "/dashboard/pipelines" })}
              className="px-4 py-2 text-sm font-medium text-white bg-gray-700 hover:bg-gray-600 rounded-md transition-colors"
            >
              Back to Pipelines
            </button>
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
      <div className="flex h-full flex-col bg-gray-900">
        {/* Header */}
        <div className="bg-gray-800 border-b border-gray-600 px-4 py-3">
          <div className="flex items-center justify-between">
            <div className="flex items-center space-x-4 flex-1">
              <h1 className="text-xl font-semibold text-white">
                Create Pipeline
              </h1>
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
                disabled={isSaving || !isValid || isValidating}
                className="px-4 py-2 text-sm font-medium text-white bg-blue-600 hover:bg-blue-700 rounded-md transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
              >
                {isSaving
                  ? "Saving..."
                  : isValidating
                    ? "Validating..."
                    : "Save Pipeline"}
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
              onChange={setCurrentPipelineState}
              viewOnly={false}
              entryPoints={entryPoints}
            />
          </div>
        </div>
      </div>
    </>
  );
}
