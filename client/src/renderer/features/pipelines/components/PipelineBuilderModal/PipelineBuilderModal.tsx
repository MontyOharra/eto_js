/**
 * Pipeline Builder Modal
 * 2-step wizard for creating pipelines:
 * 1. Entry Points: Define pipeline entry points
 * 2. Pipeline Builder: Build the transformation pipeline
 */

import { useState, useCallback, useMemo } from "react";
import { generateEntryPointId } from "../../utils/idGenerator";
import { createEntryPoint } from "../../utils/moduleFactory";
import { PipelineEditor } from "../PipelineEditor";
import { usePipelineValidation } from "../../hooks";
import type {
  EntryPoint,
  PipelineState,
  VisualState,
} from "../../types";

interface PipelineBuilderModalProps {
  isOpen: boolean;
  onClose: () => void;
  onSave: (pipelineData: PipelineData) => Promise<void>;
  initialData?: PipelineData; // Optional initial data for editing
}

export interface PipelineData {
  pipeline_state: PipelineState;
  visual_state: VisualState;
}

type BuilderStep = "entry-points" | "pipeline";

export function PipelineBuilderModal({
  isOpen,
  onClose,
  onSave,
  initialData,
}: PipelineBuilderModalProps) {
  const [currentStep, setCurrentStep] = useState<BuilderStep>("entry-points");
  const [isSaving, setIsSaving] = useState(false);

  // Entry points - managed separately and passed as external prop
  const [entryPoints, setEntryPoints] = useState<EntryPoint[]>(
    () => initialData?.pipeline_state.entry_points || []
  );

  // Pipeline state (modules and connections only - entry points managed externally)
  const [pipelineState, setPipelineState] = useState<PipelineState>({
    entry_points: [], // Will be populated on save
    modules: initialData?.pipeline_state.modules || [],
    connections: initialData?.pipeline_state.connections || [],
    output_channels: initialData?.pipeline_state.output_channels || [],
  });

  // Visual state - node positions
  const [visualState, setVisualState] = useState<VisualState>(
    () => initialData?.visual_state || {}
  );

  // Create complete pipeline state for validation (includes entry points)
  const completePipelineState = useMemo<PipelineState>(() => ({
    ...pipelineState,
    entry_points: entryPoints,
  }), [pipelineState, entryPoints]);

  // Validate pipeline automatically when it changes
  const {
    isValid: isPipelineValid,
    error: pipelineValidationError,
    isValidating: isPipelineValidating,
  } = usePipelineValidation(currentStep === "pipeline" ? completePipelineState : null);

  // Handle entry points from step 1
  const handleEntryPointsConfirm = useCallback((points: Array<{ id: string; name: string }>) => {
    const newEntryPoints: EntryPoint[] = points.map((p) => {
      // Try to find existing entry point with the same name to preserve it
      const existingEntryPoint = entryPoints.find(ep => ep.name === p.name);

      if (existingEntryPoint) {
        // Preserve existing entry point (keeps ID, connections, visual position)
        return existingEntryPoint;
      } else {
        // Create new entry point for new names
        const entryPointId = generateEntryPointId();
        return createEntryPoint(entryPointId, p.name);
      }
    });

    // Store entry points in separate state (not in pipelineState until save)
    setEntryPoints(newEntryPoints);

    // Clean up orphaned connections from removed entry points
    const entryPointOutputIds = new Set(
      newEntryPoints.flatMap(ep => ep.outputs.map(output => output.node_id))
    );
    const cleanedConnections = pipelineState.connections.filter(
      conn => !conn.from_node_id.startsWith('ep_') || entryPointOutputIds.has(conn.from_node_id)
    );

    // Clean up orphaned visual state entries
    const entryPointIds = new Set(newEntryPoints.map(ep => ep.entry_point_id));
    const cleanedVisualState = Object.fromEntries(
      Object.entries(visualState).filter(
        ([nodeId]) => !nodeId.startsWith('ep_') || entryPointIds.has(nodeId)
      )
    );

    // Update pipeline state and visual state if needed
    if (cleanedConnections.length !== pipelineState.connections.length) {
      setPipelineState({ ...pipelineState, connections: cleanedConnections });
    }
    if (Object.keys(cleanedVisualState).length !== Object.keys(visualState).length) {
      setVisualState(cleanedVisualState);
    }

    // Move to pipeline builder step
    setCurrentStep("pipeline");
  }, [entryPoints, pipelineState, visualState]);

  const handleBack = () => {
    if (currentStep === "pipeline") {
      setCurrentStep("entry-points");
    }
  };

  const handleSave = async () => {
    setIsSaving(true);

    try {
      // Merge entry points into pipeline state for saving
      const completePipelineState: PipelineState = {
        ...pipelineState,
        entry_points: entryPoints,
      };

      const data: PipelineData = {
        pipeline_state: completePipelineState,
        visual_state: visualState,
      };

      // Call parent's save handler (which calls the API)
      await onSave(data);

      // Reset modal state on successful save (parent will close modal)
      setCurrentStep("entry-points");
      setEntryPoints([]);
      setPipelineState({
        entry_points: [],
        modules: [],
        connections: [],
        output_channels: [],
      });
      setVisualState({});
    } catch (error) {
      // Error is already handled by parent component (shows alert)
      console.error("[PipelineBuilderModal] Save failed:", error);
    } finally {
      setIsSaving(false);
    }
  };

  const handleCancel = () => {
    // Reset state
    setEntryPoints([]);
    setPipelineState({
      entry_points: [],
      modules: [],
      connections: [],
      output_channels: [],
    });
    setVisualState({});
    setCurrentStep("entry-points");
    onClose();
  };

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black bg-opacity-50">
      <div className="bg-gray-800 rounded-lg shadow-xl w-[95vw] h-[90vh] flex flex-col">
        {/* Header */}
        <div className="bg-gray-900 px-6 py-4 border-b border-gray-700 rounded-t-lg">
          <div className="flex items-center justify-between">
            <div>
              <h2 className="text-2xl font-bold text-white">Create Pipeline</h2>
              <p className="text-sm text-gray-400 mt-1">
                {currentStep === "entry-points"
                  ? "Step 1: Define entry points"
                  : "Step 2: Build transformation pipeline"}
              </p>
            </div>
            <button
              onClick={handleCancel}
              className="text-gray-400 hover:text-white transition-colors"
            >
              <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
              </svg>
            </button>
          </div>

          {/* Step indicator */}
          <div className="flex items-center gap-2 mt-4">
            <div className={`px-3 py-1 rounded text-sm font-medium ${
              currentStep === "entry-points"
                ? "bg-blue-600 text-white"
                : "bg-gray-700 text-gray-300"
            }`}>
              1. Entry Points
            </div>
            <div className="w-8 h-0.5 bg-gray-700" />
            <div className={`px-3 py-1 rounded text-sm font-medium ${
              currentStep === "pipeline"
                ? "bg-blue-600 text-white"
                : "bg-gray-700 text-gray-300"
            }`}>
              2. Pipeline Builder
            </div>
          </div>
        </div>

        {/* Content */}
        <div className="flex-1 overflow-hidden">
          {currentStep === "entry-points" && (
            <EntryPointsStep
              initialEntryPoints={entryPoints}
              onConfirm={handleEntryPointsConfirm}
            />
          )}

          {currentStep === "pipeline" && (
            <PipelineEditor
              pipelineState={pipelineState}
              visualState={visualState}
              entryPoints={entryPoints}
              onPipelineStateChange={setPipelineState}
              onVisualStateChange={setVisualState}
            />
          )}
        </div>

        {/* Footer */}
        <div className="bg-gray-900 px-6 py-4 border-t border-gray-700 rounded-b-lg flex items-center justify-between">
          {/* Cancel on the left */}
          <button
            onClick={handleCancel}
            disabled={isSaving}
            className="px-4 py-2 text-sm font-medium text-gray-300 bg-gray-700 hover:bg-gray-600 disabled:bg-gray-800 disabled:cursor-not-allowed rounded-md transition-colors"
          >
            Cancel
          </button>

          {/* Back and Next/Save on the right */}
          <div className="flex gap-2">
            {currentStep === "pipeline" && (
              <button
                onClick={handleBack}
                disabled={isSaving}
                className="px-4 py-2 text-sm font-medium text-gray-300 bg-gray-700 hover:bg-gray-600 disabled:bg-gray-800 disabled:cursor-not-allowed rounded-md transition-colors"
              >
                Back
              </button>
            )}

            {currentStep === "entry-points" ? (
              <button
                onClick={() => document.getElementById('entry-points-next')?.click()}
                className="px-4 py-2 text-sm font-medium text-white bg-blue-600 hover:bg-blue-700 rounded-md transition-colors"
              >
                Next
              </button>
            ) : (
              <div className="relative group">
                <button
                  onClick={handleSave}
                  disabled={!isPipelineValid || isPipelineValidating || isSaving}
                  className="px-4 py-2 text-sm font-medium text-white bg-blue-600 hover:bg-blue-700 disabled:bg-gray-600 disabled:cursor-not-allowed rounded-md transition-colors"
                >
                  {isSaving
                    ? "Saving..."
                    : isPipelineValidating
                      ? "Validating..."
                      : "Save Pipeline"}
                </button>
                {/* Tooltip on hover when disabled */}
                {(!isPipelineValid || isPipelineValidating) && !isSaving && (
                  <div className="absolute bottom-full right-0 mb-2 hidden group-hover:block z-10">
                    <div className="bg-gray-800 text-amber-400 text-xs px-3 py-2 rounded shadow-lg whitespace-nowrap border border-amber-400/30">
                      {isPipelineValidating
                        ? "Validating pipeline..."
                        : pipelineValidationError
                          ? `[${pipelineValidationError.code}] ${pipelineValidationError.message}`
                          : "Pipeline validation failed"}
                      <div className="absolute top-full right-4 w-0 h-0 border-l-4 border-r-4 border-t-4 border-l-transparent border-r-transparent border-t-gray-800"></div>
                    </div>
                  </div>
                )}
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}

// Step components
function EntryPointsStep({
  initialEntryPoints = [],
  onConfirm
}: {
  initialEntryPoints?: EntryPoint[];
  onConfirm: (points: Array<{ id: string; name: string }>) => void;
}) {
  // Convert EntryPoint[] to local format, or start with one empty entry point
  const [entryPoints, setEntryPoints] = useState<Array<{ id: string; name: string }>>(() => {
    if (initialEntryPoints.length > 0) {
      return initialEntryPoints.map(ep => ({
        id: ep.entry_point_id,
        name: ep.name,
      }));
    }
    return [{ id: crypto.randomUUID(), name: '' }];
  });

  const handleAddEntryPoint = () => {
    setEntryPoints([...entryPoints, { id: crypto.randomUUID(), name: '' }]);
  };

  const handleRemoveEntryPoint = (id: string) => {
    if (entryPoints.length === 1) return; // Keep at least one
    setEntryPoints(entryPoints.filter(ep => ep.id !== id));
  };

  const handleNameChange = (id: string, name: string) => {
    setEntryPoints(entryPoints.map(ep =>
      ep.id === id ? { ...ep, name } : ep
    ));
  };

  const handleNext = () => {
    // Filter out empty names and confirm (keep full objects with IDs)
    const validEntryPoints = entryPoints.filter(ep => ep.name.trim() !== '');
    if (validEntryPoints.length === 0) {
      alert('Please provide at least one entry point name');
      return;
    }
    onConfirm(validEntryPoints);
  };

  return (
    <div className="h-full flex items-center justify-center p-8">
      <div className="w-full max-w-2xl">
        <h3 className="text-2xl font-bold text-white mb-2">Define Entry Points</h3>
        <p className="text-sm text-gray-400 mb-6">
          Entry points are the starting inputs for your pipeline. Each entry point will output a string value.
        </p>

        <div className="space-y-3 mb-6">
          {entryPoints.map((ep, index) => (
            <div key={ep.id} className="flex items-center gap-2">
              <input
                type="text"
                value={ep.name}
                onChange={(e) => handleNameChange(ep.id, e.target.value)}
                placeholder="Entry point name"
                className="flex-1 px-3 py-2 bg-gray-700 border border-gray-600 rounded text-gray-200 text-sm focus:outline-none focus:border-blue-500"
                autoFocus={index === 0}
              />
              <button
                onClick={() => handleRemoveEntryPoint(ep.id)}
                disabled={entryPoints.length === 1}
                className="px-3 py-2 bg-gray-700 hover:bg-gray-600 disabled:bg-gray-800 disabled:text-gray-600 text-gray-300 rounded transition-colors"
                title="Remove entry point"
              >
                <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                </svg>
              </button>
            </div>
          ))}
        </div>

        <button
          onClick={handleAddEntryPoint}
          className="w-full mb-4 px-4 py-2 bg-gray-700 hover:bg-gray-600 text-gray-300 rounded transition-colors flex items-center justify-center gap-2"
        >
          <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 4v16m8-8H4" />
          </svg>
          Add Entry Point
        </button>

        {/* Hidden next button - actual navigation is in footer */}
        <button
          onClick={handleNext}
          id="entry-points-next"
          className="hidden"
        />
      </div>
    </div>
  );
}

